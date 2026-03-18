"""
ワールドステート管理 — World State Manager

Manages the nested game world state across physical/depth/dream layers.
Supports dot-path access, rule callbacks with deferred updates, and
JSON serialization for save/load.
"""

import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Supported rule event types
RULE_EVENT_TYPES = frozenset([
    "on_state_change",
    "on_layer_enter",
    "on_quest_complete",
])

# Maximum recursion depth for deferred rule updates
MAX_RULE_RECURSION = 8

# Default data path relative to project root
_DEFAULT_STATE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "world_state.json"


class WorldStateManager:
    """Central manager for all world state, flags, and rule callbacks."""

    def __init__(self, state_path: Optional[str] = None):
        self._state: Dict[str, Any] = {}
        self._rules: Dict[str, List[Callable]] = {t: [] for t in RULE_EVENT_TYPES}
        self._current_layer: str = "physical"

        # Deferred update queue (used during rule callback execution)
        self._update_queue: List[tuple] = []
        self._processing_rules: bool = False
        self._rule_recursion_depth: int = 0

        # Load initial state
        path = Path(state_path) if state_path else _DEFAULT_STATE_PATH
        self._load_state(path)

    # ------------------------------------------------------------------
    # State loading
    # ------------------------------------------------------------------

    def _load_state(self, path: Path) -> None:
        """Load initial state from a JSON file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._state = json.load(f)
            logger.info("World state loaded from %s", path)
        except FileNotFoundError:
            logger.warning("State file not found at %s — using defaults", path)
            self._state = self._default_state()
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in %s: %s — using defaults", path, exc)
            self._state = self._default_state()

    @staticmethod
    def _default_state() -> Dict[str, Any]:
        return {
            "global": {"chapter": 1, "story_phase": "awakening"},
            "layers": {
                "physical": {"distortion": 0, "healed_count": 0, "corruption_zones": []},
                "depth": {"distortion": 0, "crystallization": 0, "sealed_cores": []},
                "dream": {"stability": 100, "fragments_collected": 0, "unlocked_areas": []},
            },
            "flags": {},
            "quest_states": {},
        }

    # ------------------------------------------------------------------
    # Dot-path resolution
    # ------------------------------------------------------------------

    def _resolve_path(self, dot_path: str, *, create_intermediate: bool = False) -> tuple:
        """Resolve a dot-path string to (parent_dict, final_key).

        Paths are resolved as follows:
        - "global.chapter"          -> state["global"]["chapter"]
        - "flags.met_alma"          -> state["flags"]["met_alma"]
        - "quest_states.q001"       -> state["quest_states"]["q001"]
        - "depth.distortion"        -> state["layers"]["depth"]["distortion"]
        - "physical.healed_count"   -> state["layers"]["physical"]["healed_count"]
        - "dream.stability"         -> state["layers"]["dream"]["stability"]

        Parameters
        ----------
        create_intermediate : bool
            When True (used by set_state), creates missing intermediate dicts
            via setdefault. When False (used by get_state), raises KeyError if
            an intermediate segment does not exist, preventing read-side
            mutation of the state tree.
        """
        parts = dot_path.split(".")
        if not parts:
            raise KeyError(f"Empty dot-path: {dot_path!r}")

        root = parts[0]

        # Direct top-level keys
        if root in self._state and root != "layers":
            node = self._state[root]
            for segment in parts[1:-1]:
                if isinstance(node, dict):
                    if create_intermediate:
                        node = node.setdefault(segment, {})
                    else:
                        if segment not in node:
                            raise KeyError(f"Segment {segment!r} not found in {dot_path!r}")
                        node = node[segment]
                else:
                    raise KeyError(f"Cannot traverse non-dict at {segment!r} in {dot_path!r}")
            if len(parts) == 1:
                # Requesting entire top-level bucket (e.g. get_state("flags"))
                return self._state, root
            return node, parts[-1]

        # Layer shorthand: "depth.distortion" -> state["layers"]["depth"]["distortion"]
        layers = self._state.get("layers", {})
        if root in layers:
            node = layers[root]
            for segment in parts[1:-1]:
                if isinstance(node, dict):
                    if create_intermediate:
                        node = node.setdefault(segment, {})
                    else:
                        if segment not in node:
                            raise KeyError(f"Segment {segment!r} not found in {dot_path!r}")
                        node = node[segment]
                else:
                    raise KeyError(f"Cannot traverse non-dict at {segment!r} in {dot_path!r}")
            if len(parts) == 1:
                return layers, root
            return node, parts[-1]

        raise KeyError(f"Cannot resolve dot-path: {dot_path!r}")

    # ------------------------------------------------------------------
    # Public get / set
    # ------------------------------------------------------------------

    def get_state(self, dot_path: str) -> Any:
        """Read a value from state using a dot-path key."""
        try:
            parent, key = self._resolve_path(dot_path)
            return parent.get(key)
        except KeyError:
            logger.warning("get_state: unresolved path %r", dot_path)
            return None

    def set_state(self, dot_path: str, value: Any) -> None:
        """Write a value to state using a dot-path key.

        If called while rule callbacks are executing, the change is queued
        and applied after the current callback completes (deferred model).
        """
        if self._processing_rules:
            self._update_queue.append((dot_path, value))
            return

        self._apply_state_change(dot_path, value)

    def _apply_state_change(self, dot_path: str, value: Any) -> None:
        """Actually apply a state change and fire rule callbacks."""
        try:
            parent, key = self._resolve_path(dot_path, create_intermediate=True)
        except KeyError:
            logger.error("set_state: unresolved path %r", dot_path)
            return

        old_value = parent.get(key)
        parent[key] = value
        logger.debug("State %s: %r -> %r", dot_path, old_value, value)

        # Fire on_state_change rules
        self._fire_rules("on_state_change", dot_path, old_value, value)

    def _fire_rules(self, event_type: str, *args: Any) -> None:
        """Execute rule callbacks with deferred update support."""
        callbacks = self._rules.get(event_type, [])
        if not callbacks:
            return

        self._rule_recursion_depth += 1
        if self._rule_recursion_depth > MAX_RULE_RECURSION:
            logger.warning(
                "Rule recursion depth exceeded (%d). Skipping %s callbacks.",
                MAX_RULE_RECURSION,
                event_type,
            )
            self._rule_recursion_depth -= 1
            return

        self._processing_rules = True
        try:
            for cb in callbacks:
                try:
                    cb(*args)
                except Exception:
                    logger.exception("Error in %s rule callback", event_type)
        finally:
            self._processing_rules = False

        # Process deferred updates
        queued = list(self._update_queue)
        self._update_queue.clear()
        for path, val in queued:
            self._apply_state_change(path, val)

        self._rule_recursion_depth -= 1

    # ------------------------------------------------------------------
    # Layer management
    # ------------------------------------------------------------------

    @property
    def current_layer(self) -> str:
        """Return the name of the layer the player is currently in."""
        return self._current_layer

    @current_layer.setter
    def current_layer(self, value: str) -> None:
        self._current_layer = value

    def change_layer(self, new_layer: str) -> None:
        """Change the active layer and fire on_layer_enter rules."""
        old = self._current_layer
        self._current_layer = new_layer
        logger.info("Layer changed: %s -> %s", old, new_layer)
        self._fire_rules("on_layer_enter", new_layer, old)

    # ------------------------------------------------------------------
    # Flags convenience
    # ------------------------------------------------------------------

    def get_flags(self) -> Dict[str, Any]:
        return self._state.setdefault("flags", {})

    def get_flag(self, name: str) -> Any:
        return self.get_flags().get(name)

    def set_flag(self, name: str, value: Any) -> None:
        old = self.get_flags().get(name)
        self.get_flags()[name] = value
        logger.debug("Flag %s: %r -> %r", name, old, value)
        # Notify rules so they can react to flag changes
        self._fire_rules("on_state_change", f"flags.{name}", old, value)

    # ------------------------------------------------------------------
    # Quest states convenience
    # ------------------------------------------------------------------

    def get_quest_state(self, quest_id: str) -> Optional[str]:
        return self._state.setdefault("quest_states", {}).get(quest_id)

    def set_quest_state(self, quest_id: str, state: str) -> None:
        self._state.setdefault("quest_states", {})[quest_id] = state

    def notify_quest_complete(self, quest_id: str) -> None:
        """Fire on_quest_complete rules. Called by QuestManager."""
        self._fire_rules("on_quest_complete", quest_id)

    # ------------------------------------------------------------------
    # Rule registration
    # ------------------------------------------------------------------

    def register_rule(self, event_type: str, callback: Callable) -> None:
        """Register a rule callback for the given event type."""
        if event_type not in RULE_EVENT_TYPES:
            logger.warning(
                "Unknown rule event type %r. Supported: %s",
                event_type,
                ", ".join(sorted(RULE_EVENT_TYPES)),
            )
            return
        self._rules[event_type].append(callback)
        logger.debug("Registered rule for %s", event_type)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_json(self) -> str:
        """Serialize the entire state to a JSON string (no Lua refs)."""
        data = {
            "state": deepcopy(self._state),
            "current_layer": self._current_layer,
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def from_json(self, json_str: str) -> None:
        """Restore state from a JSON string."""
        try:
            data = json.loads(json_str)
            self._state = data.get("state", self._default_state())
            self._current_layer = data.get("current_layer", "physical")
            logger.info("World state restored from JSON")
        except (json.JSONDecodeError, KeyError) as exc:
            logger.error("Failed to restore world state: %s", exc)

    def get_raw_state(self) -> Dict[str, Any]:
        """Return a deep copy of the raw state dict (for debugging/testing)."""
        return deepcopy(self._state)

"""
クエスト管理 — Quest Manager

Manages quest definitions, state machine transitions, prerequisite
evaluation, Lua script callbacks, and reward distribution.
"""

import json
import logging
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Valid quest state transitions
VALID_STATES = ("inactive", "available", "active", "completed", "failed")

# Default quest data path
_DEFAULT_QUEST_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "quests.json"


class QuestManager:
    """Central manager for all quest lifecycle, scripting hooks, and rewards.

    Parameters
    ----------
    world_state_manager : WorldStateManager
        Used for flag/state checks and storing quest states.
    script_engine : ScriptEngine
        Used for loading and running Lua quest scripts.
    script_api : ScriptAPI
        Used for setting quest context before script calls.
    game : Game or None
        Used for reward distribution (party, gold, inventory).
    quest_path : str or Path, optional
        Path to the quest definitions JSON file.
    """

    def __init__(
        self,
        world_state_manager: Any,
        script_engine: Any,
        script_api: Any,
        game: Any = None,
        quest_path: Optional[str] = None,
    ):
        self._wsm = world_state_manager
        self._engine = script_engine
        self._api = script_api
        self._game = game

        # quest_id -> quest definition dict (from JSON)
        self._definitions: Dict[str, dict] = {}

        # quest_id -> runtime state dict:
        #   { "state": str, "stage": str, "objective": str }
        # Also mirrored into WorldStateManager.quest_states for serialization.
        self._runtime: Dict[str, dict] = {}

        # Current quest context for context-dependent API calls
        self._context_quest_id: Optional[str] = None

        # Load quest definitions
        path = Path(quest_path) if quest_path else _DEFAULT_QUEST_PATH
        self._load_definitions(path)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_definitions(self, path: Path) -> None:
        """Load quest definitions from a JSON file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.warning("Quest definitions not found at %s", path)
            return
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in %s: %s", path, exc)
            return

        for quest_id, definition in data.items():
            definition["id"] = quest_id
            self._definitions[quest_id] = definition

            # Initialise runtime state from WorldStateManager if it exists,
            # otherwise default to inactive.
            existing = self._wsm.get_quest_state(quest_id)
            if existing and isinstance(existing, dict):
                self._runtime[quest_id] = existing
            elif existing and isinstance(existing, str):
                # Legacy: just a state string
                self._runtime[quest_id] = {
                    "state": existing,
                    "stage": "",
                    "objective": "",
                }
            else:
                self._runtime[quest_id] = {
                    "state": "inactive",
                    "stage": "",
                    "objective": "",
                }
            # Mirror to WSM
            self._sync_to_wsm(quest_id)

        logger.info("Loaded %d quest definitions from %s", len(self._definitions), path)

    def _sync_to_wsm(self, quest_id: str) -> None:
        """Mirror runtime quest state to WorldStateManager for serialization."""
        rt = self._runtime.get(quest_id)
        if rt:
            self._wsm.set_quest_state(quest_id, deepcopy(rt))

    # ------------------------------------------------------------------
    # State machine helpers
    # ------------------------------------------------------------------

    def _get_runtime(self, quest_id: str) -> Optional[dict]:
        return self._runtime.get(quest_id)

    def _set_state(self, quest_id: str, new_state: str) -> None:
        rt = self._runtime.get(quest_id)
        if rt is None:
            logger.warning("_set_state: unknown quest %s", quest_id)
            return
        old_state = rt["state"]
        rt["state"] = new_state
        self._sync_to_wsm(quest_id)
        logger.info("Quest %s: %s -> %s", quest_id, old_state, new_state)

    # ------------------------------------------------------------------
    # Prerequisite evaluation (declarative, no Lua)
    # ------------------------------------------------------------------

    def _evaluate_prerequisites(self, quest_id: str) -> bool:
        """Evaluate declarative prerequisites from the quest JSON.

        Supported formats:
        - "flag:flag_name"                  -> wsm.get_flag(flag_name) is truthy
        - "world:dot.path>=value"           -> numeric comparison
        - "world:dot.path<=value"
        - "world:dot.path==value"
        - "quest:quest_id:state"            -> quest is in that state
        """
        defn = self._definitions.get(quest_id)
        if defn is None:
            return False

        prerequisites = defn.get("prerequisites", [])
        if not prerequisites:
            return True

        for prereq in prerequisites:
            if not self._evaluate_single_prereq(prereq):
                return False
        return True

    def _evaluate_single_prereq(self, prereq: str) -> bool:
        """Evaluate a single prerequisite string."""
        if prereq.startswith("flag:"):
            flag_name = prereq[5:]
            return bool(self._wsm.get_flag(flag_name))

        if prereq.startswith("world:"):
            expr = prereq[6:]
            return self._evaluate_world_prereq(expr)

        if prereq.startswith("quest:"):
            parts = prereq[6:].split(":")
            if len(parts) == 2:
                qid, expected_state = parts
                return self.get_quest_state(qid) == expected_state
            return False

        logger.warning("Unknown prerequisite format: %s", prereq)
        return False

    def _evaluate_world_prereq(self, expr: str) -> bool:
        """Evaluate a world state prerequisite like 'depth.distortion>=3'."""
        # Match patterns like "dot.path>=3", "dot.path<=5", "dot.path==10"
        match = re.match(r"^([\w.]+)\s*(>=|<=|==|!=|>|<)\s*(.+)$", expr)
        if not match:
            logger.warning("Cannot parse world prerequisite: %s", expr)
            return False

        path, op, raw_value = match.groups()
        current = self._wsm.get_state(path)

        # Try numeric comparison
        try:
            target = float(raw_value)
            current_num = float(current) if current is not None else 0.0
            if op == ">=":
                return current_num >= target
            elif op == "<=":
                return current_num <= target
            elif op == "==":
                return current_num == target
            elif op == "!=":
                return current_num != target
            elif op == ">":
                return current_num > target
            elif op == "<":
                return current_num < target
        except (ValueError, TypeError):
            # Fall back to string comparison for == and !=
            if op == "==":
                return str(current) == raw_value
            elif op == "!=":
                return str(current) != raw_value

        return False

    # ------------------------------------------------------------------
    # Availability checking
    # ------------------------------------------------------------------

    def check_all_availability(self) -> List[str]:
        """Evaluate all inactive quests and transition to available if
        prerequisites are met and Lua on_check_available() returns true.

        Returns a list of quest IDs that became available.
        """
        newly_available = []

        for quest_id, rt in self._runtime.items():
            if rt["state"] != "inactive":
                continue

            # Stage 1: declarative prerequisites
            if not self._evaluate_prerequisites(quest_id):
                continue

            # Stage 2: Lua on_check_available()
            if not self._lua_check_available(quest_id):
                continue

            self._set_state(quest_id, "available")
            newly_available.append(quest_id)

        return newly_available

    def _lua_check_available(self, quest_id: str) -> bool:
        """Call on_check_available() from the quest's Lua script."""
        defn = self._definitions.get(quest_id)
        if defn is None:
            return False

        script_path = defn.get("script")
        if not script_path:
            # No script means auto-available once prerequisites pass
            return True

        if not self._engine.is_available:
            logger.warning("Script engine not available for quest %s", quest_id)
            return True  # Default to available if no Lua

        # Set context for the duration of the call
        self.set_context(quest_id)
        try:
            self._engine.load_script(script_path)
            lua = self._engine.lua
            if lua is None:
                return True

            func = lua.eval("on_check_available")
            if func is None:
                return True

            result = func()
            return bool(result)
        except Exception as exc:
            logger.error("on_check_available error for %s: %s", quest_id, exc)
            return False
        finally:
            self.clear_context()

    # ------------------------------------------------------------------
    # Quest lifecycle
    # ------------------------------------------------------------------

    def start_quest(self, quest_id: str) -> None:
        """Transition a quest from available to active (called from Lua quest.start)."""
        self.accept_quest(quest_id)

    def accept_quest(self, quest_id: str) -> None:
        """Transition a quest from available to active, running on_accept() as coroutine."""
        rt = self._runtime.get(quest_id)
        if rt is None:
            logger.warning("accept_quest: unknown quest %s", quest_id)
            return
        if rt["state"] not in ("available", "inactive"):
            logger.warning(
                "accept_quest: quest %s is in state %s, expected available or inactive",
                quest_id, rt["state"],
            )
            return

        self._set_state(quest_id, "active")

        # Run on_accept() Lua callback
        defn = self._definitions.get(quest_id)
        if defn is None:
            return

        script_path = defn.get("script")
        if not script_path or not self._engine.is_available:
            return

        self.set_context(quest_id)
        try:
            self._engine.load_script(script_path)
            lua = self._engine.lua
            if lua is None:
                return

            func = lua.eval("on_accept")
            if func is None:
                return

            runner = self._engine.execute_coroutine(func)
            if runner is not None:
                # Drain the coroutine (on_accept may yield for dialogue)
                try:
                    for _yielded in runner:
                        pass
                except StopIteration:
                    pass
        except Exception as exc:
            logger.error("on_accept error for %s: %s", quest_id, exc)
        finally:
            self.clear_context()

    def complete_quest(self, quest_id: str) -> None:
        """Transition a quest from active to completed and distribute rewards."""
        rt = self._runtime.get(quest_id)
        if rt is None:
            logger.warning("complete_quest: unknown quest %s", quest_id)
            return
        if rt["state"] != "active":
            logger.warning(
                "complete_quest: quest %s is in state %s, expected active",
                quest_id, rt["state"],
            )
            return

        self._set_state(quest_id, "completed")
        self.distribute_rewards(quest_id)
        # Fire on_quest_complete rules in WorldStateManager
        self._wsm.notify_quest_complete(quest_id)
        logger.info("Quest completed: %s", quest_id)

    def fail_quest(self, quest_id: str) -> None:
        """Transition a quest from active to failed."""
        rt = self._runtime.get(quest_id)
        if rt is None:
            logger.warning("fail_quest: unknown quest %s", quest_id)
            return
        if rt["state"] != "active":
            logger.warning(
                "fail_quest: quest %s is in state %s, expected active",
                quest_id, rt["state"],
            )
            return

        self._set_state(quest_id, "failed")
        logger.info("Quest failed: %s", quest_id)

    # ------------------------------------------------------------------
    # Stage event dispatch
    # ------------------------------------------------------------------

    def dispatch_event(self, trigger_id: str) -> None:
        """For all active quests, call on_stage_event(trigger_id) on their scripts."""
        for quest_id, rt in self._runtime.items():
            if rt["state"] != "active":
                continue

            defn = self._definitions.get(quest_id)
            if defn is None:
                continue

            script_path = defn.get("script")
            if not script_path or not self._engine.is_available:
                continue

            self.set_context(quest_id)
            try:
                self._engine.load_script(script_path)
                lua = self._engine.lua
                if lua is None:
                    continue

                func = lua.eval("on_stage_event")
                if func is None:
                    continue

                runner = self._engine.execute_coroutine(func, trigger_id)
                if runner is not None:
                    try:
                        for _yielded in runner:
                            pass
                    except StopIteration:
                        pass
            except Exception as exc:
                logger.error(
                    "on_stage_event error for quest %s, trigger %s: %s",
                    quest_id, trigger_id, exc,
                )
            finally:
                self.clear_context()

    # ------------------------------------------------------------------
    # Context management (for context-dependent quest APIs)
    # ------------------------------------------------------------------

    def set_context(self, quest_id: str) -> None:
        """Set the current quest context for context-dependent APIs."""
        self._context_quest_id = quest_id
        if self._api is not None:
            self._api.current_quest_id = quest_id

    def clear_context(self) -> None:
        """Clear the current quest context."""
        self._context_quest_id = None
        if self._api is not None:
            self._api.current_quest_id = None

    # ------------------------------------------------------------------
    # Context-dependent stage/objective accessors
    # ------------------------------------------------------------------

    def get_current_stage(self) -> Optional[str]:
        """Return the stage of the context quest."""
        if self._context_quest_id is None:
            return None
        return self.get_quest_stage(self._context_quest_id)

    def set_current_stage(self, stage: str) -> None:
        """Set the stage of the context quest."""
        if self._context_quest_id is None:
            logger.warning("set_current_stage: no context quest")
            return
        self.set_quest_stage(self._context_quest_id, stage)

    def set_current_objective(self, text: str) -> None:
        """Set the objective text of the context quest."""
        if self._context_quest_id is None:
            logger.warning("set_current_objective: no context quest")
            return
        self.set_quest_objective(self._context_quest_id, text)

    # ------------------------------------------------------------------
    # Per-quest stage and objective
    # ------------------------------------------------------------------

    def get_quest_stage(self, quest_id: str) -> Optional[str]:
        """Return the current stage of the given quest."""
        rt = self._runtime.get(quest_id)
        if rt is None:
            return None
        return rt.get("stage", "")

    def set_quest_stage(self, quest_id: str, stage: str) -> None:
        """Set the stage of the given quest."""
        rt = self._runtime.get(quest_id)
        if rt is None:
            logger.warning("set_quest_stage: unknown quest %s", quest_id)
            return
        rt["stage"] = stage
        self._sync_to_wsm(quest_id)
        logger.debug("Quest %s stage -> %s", quest_id, stage)

    def set_quest_objective(self, quest_id: str, text: str) -> None:
        """Set the objective text of the given quest."""
        rt = self._runtime.get(quest_id)
        if rt is None:
            logger.warning("set_quest_objective: unknown quest %s", quest_id)
            return
        rt["objective"] = text
        self._sync_to_wsm(quest_id)
        logger.debug("Quest %s objective -> %s", quest_id, text)

    def update_quest(self, quest_id: str, stage: str) -> None:
        """Update a quest's stage (called from Lua quest.update)."""
        self.set_quest_stage(quest_id, stage)

    # ------------------------------------------------------------------
    # Reward distribution
    # ------------------------------------------------------------------

    def distribute_rewards(self, quest_id: str) -> None:
        """Distribute rewards for a completed quest.

        - EXP: equal split to alive party members
        - Gold: added to game.gold
        - Items: added to game.inventory (cap 99)
        """
        defn = self._definitions.get(quest_id)
        if defn is None:
            return

        rewards = defn.get("rewards")
        if not rewards:
            return

        game = self._game
        if game is None:
            logger.warning("distribute_rewards: no game reference")
            return

        # EXP — equal split to alive party members
        exp = rewards.get("exp", 0)
        if exp > 0:
            party = getattr(game, "party", [])
            alive = [m for m in party if m.get("hp", 0) > 0]
            if alive:
                per_member = exp // len(alive)
                for member in alive:
                    current_exp = member.get("current_exp", 0)
                    member["current_exp"] = current_exp + per_member
                logger.info("Distributed %d EXP (%d each) to %d members",
                            exp, per_member, len(alive))

        # Gold
        gold = rewards.get("gold", 0)
        if gold > 0:
            game.gold = getattr(game, "gold", 0) + gold
            logger.info("Awarded %d gold (total: %d)", gold, game.gold)

        # Items
        items = rewards.get("items", [])
        for item_entry in items:
            item_id = item_entry.get("id")
            count = item_entry.get("count", 1)
            if item_id:
                inv = getattr(game, "inventory", {})
                current = inv.get(item_id, 0)
                inv[item_id] = min(99, current + count)
                logger.info("Awarded item %s x%d", item_id, count)

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_quest_state(self, quest_id: str) -> Optional[str]:
        """Return the state string of the given quest."""
        rt = self._runtime.get(quest_id)
        if rt is None:
            return None
        return rt.get("state", "inactive")

    def get_active_quests(self) -> List[dict]:
        """Return a list of quest info dicts for all active quests."""
        return [
            self.get_quest_info(qid)
            for qid, rt in self._runtime.items()
            if rt["state"] == "active"
        ]

    def get_completed_quests(self) -> List[dict]:
        """Return a list of quest info dicts for all completed quests."""
        return [
            self.get_quest_info(qid)
            for qid, rt in self._runtime.items()
            if rt["state"] == "completed"
        ]

    def get_available_quests(self) -> List[dict]:
        """Return a list of quest info dicts for all available quests."""
        return [
            self.get_quest_info(qid)
            for qid, rt in self._runtime.items()
            if rt["state"] == "available"
        ]

    def get_quest_info(self, quest_id: str) -> Optional[dict]:
        """Return full quest data dict combining definition and runtime state."""
        defn = self._definitions.get(quest_id)
        if defn is None:
            return None

        rt = self._runtime.get(quest_id, {})

        return {
            "id": quest_id,
            "type": defn.get("type", "sub"),
            "title": defn.get("title", quest_id),
            "description": defn.get("description", ""),
            "chapter": defn.get("chapter"),
            "prerequisites": defn.get("prerequisites", []),
            "layers_involved": defn.get("layers_involved", []),
            "rewards": defn.get("rewards", {}),
            "state": rt.get("state", "inactive"),
            "stage": rt.get("stage", ""),
            "objective": rt.get("objective", ""),
        }

    def get_all_quests(self) -> List[dict]:
        """Return info for all known quests."""
        return [self.get_quest_info(qid) for qid in self._definitions]

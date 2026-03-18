"""
NPC管理システム — NPC Manager

Loads NPC definitions from data/npcs.json, handles NPC positioning per
map/layer, movement patterns, visibility checks, and dialogue coroutines.
"""

import json
import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Direction offsets: direction -> (dx, dy)
_DIRECTION_OFFSETS = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}

# Opposite directions (for patrol bounce)
_OPPOSITE_DIR = {
    "up": "down",
    "down": "up",
    "left": "right",
    "right": "left",
}


class NPC:
    """Runtime representation of a single NPC instance."""

    def __init__(
        self,
        npc_id: str,
        name: str,
        sprite: str,
        script_path: str,
        movement: str,
        facing: str = "down",
    ):
        self.id = npc_id
        self.name = name
        self.sprite = sprite
        self.script_path = script_path
        self.movement = movement  # "fixed", "patrol", "random"
        self.facing = facing

        # Position (set per-layer)
        self.grid_x: int = 0
        self.grid_y: int = 0

        # Patrol state
        self._patrol_dir: str = "right"
        self._patrol_steps: int = 0
        self._patrol_max_steps: int = 3

        # Random movement timer
        self._random_timer: float = 0.0
        self._random_interval: float = 2.0  # seconds between random steps

        # Layer-specific script override
        self.layer_script_path: Optional[str] = None

    def face_towards(self, target_x: int, target_y: int) -> None:
        """Turn to face a target grid position."""
        dx = target_x - self.grid_x
        dy = target_y - self.grid_y
        if abs(dx) > abs(dy):
            self.facing = "right" if dx > 0 else "left"
        elif dy != 0:
            self.facing = "down" if dy > 0 else "up"


class NPCManager:
    """Manages all NPC definitions and their runtime state.

    Parameters
    ----------
    script_engine : ScriptEngine
        The script engine used to load and run NPC Lua scripts.
    data_path : str or None
        Path to npcs.json. Defaults to ``<project_root>/data/npcs.json``.
    """

    def __init__(self, script_engine: Any, data_path: Optional[str] = None):
        self._engine = script_engine
        self._project_root = Path(__file__).resolve().parent.parent.parent
        self._data_path = Path(data_path) if data_path else self._project_root / "data" / "npcs.json"

        # npc_id -> raw definition from JSON
        self._definitions: Dict[str, dict] = {}

        # npc_id -> NPC runtime instance (built per map/layer query)
        self._active_npcs: Dict[str, NPC] = {}

        # Loaded Lua on_talk functions keyed by script path
        self._script_functions: Dict[str, Any] = {}

        self._load_definitions()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_definitions(self) -> None:
        """Load NPC definitions from JSON."""
        try:
            with open(self._data_path, "r", encoding="utf-8") as f:
                self._definitions = json.load(f)
            logger.info("Loaded %d NPC definitions from %s", len(self._definitions), self._data_path)
        except FileNotFoundError:
            logger.warning("NPC data file not found: %s", self._data_path)
            self._definitions = {}
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in NPC data: %s", exc)
            self._definitions = {}

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_npcs_for_map(self, map_id: str, layer: str) -> List[NPC]:
        """Return NPC instances positioned on *map_id* in *layer*."""
        result: List[NPC] = []
        for npc_id, defn in self._definitions.items():
            layers = defn.get("layers", {})
            layer_data = layers.get(layer)
            if layer_data is None:
                continue
            if layer_data.get("map") != map_id:
                continue

            is_new = npc_id not in self._active_npcs
            npc = self._get_or_create_npc(npc_id, defn)
            # Only set position from JSON on first creation; movement
            # updates modify grid_x/grid_y at runtime and must not be
            # overwritten each frame.
            if is_new:
                npc.grid_x = layer_data.get("x", 0)
                npc.grid_y = layer_data.get("y", 0)
            npc.layer_script_path = layer_data.get("script")
            result.append(npc)

        return result

    def get_npc_at(self, map_id: str, layer: str, grid_x: int, grid_y: int) -> Optional[NPC]:
        """Return the NPC at a specific tile, or None."""
        npcs = self.get_npcs_for_map(map_id, layer)
        for npc in npcs:
            if npc.grid_x == grid_x and npc.grid_y == grid_y:
                return npc
        return None

    def get_npc_in_direction(
        self, map_id: str, layer: str, player_x: int, player_y: int, direction: str
    ) -> Optional[NPC]:
        """Return the NPC adjacent to the player in the given direction."""
        offset = _DIRECTION_OFFSETS.get(direction)
        if offset is None:
            return None
        target_x = player_x + offset[0]
        target_y = player_y + offset[1]
        return self.get_npc_at(map_id, layer, target_x, target_y)

    # ------------------------------------------------------------------
    # NPC instance management
    # ------------------------------------------------------------------

    def _get_or_create_npc(self, npc_id: str, defn: dict) -> NPC:
        """Retrieve a cached NPC or create a new one."""
        if npc_id in self._active_npcs:
            return self._active_npcs[npc_id]

        npc = NPC(
            npc_id=npc_id,
            name=defn.get("name", "???"),
            sprite=defn.get("sprite", ""),
            script_path=defn.get("script", ""),
            movement=defn.get("movement", "fixed"),
        )
        self._active_npcs[npc_id] = npc
        return npc

    # ------------------------------------------------------------------
    # Visibility
    # ------------------------------------------------------------------

    def check_visibility(self, npc_id: str) -> bool:
        """Run the NPC's on_visible() callback if it exists. Returns True if visible."""
        npc = self._active_npcs.get(npc_id)
        if npc is None:
            return True

        script_path = npc.layer_script_path or npc.script_path
        if not script_path:
            return True

        on_visible = self._get_script_function(script_path, "on_visible")
        if on_visible is None:
            return True

        try:
            result = on_visible()
            if result is False:
                return False
            return True
        except Exception as exc:
            logger.error("Error in on_visible for %s: %s", npc_id, exc)
            return True

    # ------------------------------------------------------------------
    # Dialogue
    # ------------------------------------------------------------------

    def start_dialogue(self, npc_id: str) -> Any:
        """Load and run the NPC's on_talk() as a coroutine.

        Returns a CoroutineRunner that yields ("say", speaker, text) or
        ("choice", options), or None if the script cannot be loaded.
        """
        npc = self._active_npcs.get(npc_id)
        if npc is None:
            logger.warning("start_dialogue: NPC %s not found", npc_id)
            return None

        script_path = npc.layer_script_path or npc.script_path
        if not script_path:
            logger.warning("start_dialogue: NPC %s has no script", npc_id)
            return None

        on_talk = self._get_script_function(script_path, "on_talk")
        if on_talk is None:
            logger.warning("start_dialogue: no on_talk in %s", script_path)
            return None

        runner = self._engine.execute_coroutine(on_talk)
        return runner

    def _get_script_function(self, script_path: str, func_name: str) -> Any:
        """Load a script and extract a named function from the Lua global scope."""
        if not self._engine.is_available:
            return None

        # Load the script (cached internally by ScriptEngine)
        self._engine.load_script(script_path)

        # The script defines global functions; retrieve the requested one
        lua = self._engine.lua
        if lua is None:
            return None

        try:
            func = lua.eval(func_name)
            return func
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Movement
    # ------------------------------------------------------------------

    def update_npcs(self, map_id: str, layer: str, dt: float) -> None:
        """Update NPC movement patterns for all NPCs on the current map/layer.

        Parameters
        ----------
        map_id : str
            Current map identifier.
        layer : str
            Current world layer.
        dt : float
            Delta time in seconds since last frame.
        """
        npcs = self.get_npcs_for_map(map_id, layer)
        for npc in npcs:
            if npc.movement == "fixed":
                continue
            elif npc.movement == "patrol":
                self._update_patrol(npc, dt)
            elif npc.movement == "random":
                self._update_random(npc, dt)

    def _update_patrol(self, npc: NPC, dt: float) -> None:
        """Move NPC back and forth along its patrol path."""
        npc._random_timer += dt
        if npc._random_timer < 0.5:
            return
        npc._random_timer = 0.0

        dx, dy = _DIRECTION_OFFSETS.get(npc._patrol_dir, (0, 0))
        npc.grid_x += dx
        npc.grid_y += dy
        npc.facing = npc._patrol_dir
        npc._patrol_steps += 1

        if npc._patrol_steps >= npc._patrol_max_steps:
            npc._patrol_steps = 0
            npc._patrol_dir = _OPPOSITE_DIR.get(npc._patrol_dir, "right")

    def _update_random(self, npc: NPC, dt: float) -> None:
        """Move NPC in a random direction at intervals."""
        npc._random_timer += dt
        if npc._random_timer < npc._random_interval:
            return
        npc._random_timer = 0.0

        direction = random.choice(["up", "down", "left", "right"])
        dx, dy = _DIRECTION_OFFSETS[direction]
        npc.grid_x += dx
        npc.grid_y += dy
        npc.facing = direction

    # ------------------------------------------------------------------
    # Face player
    # ------------------------------------------------------------------

    def face_player(self, npc_id: str, player_x: int, player_y: int) -> None:
        """Make an NPC face towards the player position."""
        npc = self._active_npcs.get(npc_id)
        if npc is not None:
            npc.face_towards(player_x, player_y)

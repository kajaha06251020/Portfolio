"""ダンジョンギミック管理 — Dungeon Gimmick Manager

Manages dungeon gimmicks extracted from TMX map objects:

* **Switch + Door** — step-on or action-button switches that toggle linked doors
* **Pitfall** — hidden (or visible) floor traps that teleport the player
* **One-Way Door** — passages that only allow movement in one direction
* **Locked Door** — doors that require a key item to open
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

# Direction vectors used for one-way / facing checks
_DIR_VECTORS: dict[str, tuple[int, int]] = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}

# Reverse direction lookup
_DIR_OPPOSITE: dict[str, str] = {
    "up": "down",
    "down": "up",
    "left": "right",
    "right": "left",
}


# ------------------------------------------------------------------
# Data classes
# ------------------------------------------------------------------

@dataclass
class _SwitchData:
    switch_id: str
    grid_x: int
    grid_y: int
    target: str  # linked door_id


@dataclass
class _SwitchDoorData:
    door_id: str
    grid_x: int
    grid_y: int
    default: str  # "closed" or "open"


@dataclass
class _PitfallData:
    pitfall_id: str
    grid_x: int
    grid_y: int
    dest_map: str
    dest_x: int
    dest_y: int
    visible: bool


@dataclass
class _OneWayData:
    grid_x: int
    grid_y: int
    direction: str  # the allowed direction of passage


@dataclass
class _LockedDoorData:
    door_id: str
    grid_x: int
    grid_y: int
    key_item: str


@dataclass
class GimmickEvent:
    """Returned by on_player_step / interact for MapScene to handle."""
    type: str       # "switch_toggle", "pitfall", "door_opened", "one_way_block"
    data: dict      # gimmick-specific payload
    message: str = ""


# ------------------------------------------------------------------
# Manager
# ------------------------------------------------------------------

class GimmickManager:
    """Manages dungeon gimmicks parsed from TMX object layers.

    TMX object types recognised:

    ``switch``
        Properties: *switch_id*, *target* (door_id to toggle).

    ``switch_door``
        Properties: *door_id*, *default* (``"closed"`` or ``"open"``).

    ``pitfall``
        Properties: *pitfall_id*, *dest_map*, *dest_x*, *dest_y*, *visible*.

    ``one_way``
        Properties: *direction* (the allowed passage direction).

    ``locked_door``
        Properties: *door_id*, *key_item*.
    """

    def __init__(self, world_state_manager, game):
        self._wsm = world_state_manager
        self._game = game

        # Per-map gimmick storage, cleared on load_gimmicks
        self._switches: list[_SwitchData] = []
        self._switch_doors: dict[str, _SwitchDoorData] = {}  # door_id -> data
        self._pitfalls: list[_PitfallData] = []
        self._one_ways: list[_OneWayData] = []
        self._locked_doors: dict[str, _LockedDoorData] = {}  # door_id -> data

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_gimmicks(self, map_id: str, tmx_data) -> None:
        """Extract all gimmick objects from *tmx_data* object groups."""
        self._switches.clear()
        self._switch_doors.clear()
        self._pitfalls.clear()
        self._one_ways.clear()
        self._locked_doors.clear()

        if tmx_data is None:
            return

        tile_w = tmx_data.tilewidth
        tile_h = tmx_data.tileheight

        for obj_group in tmx_data.objectgroups:
            for obj in obj_group:
                obj_type = getattr(obj, "type", "")
                if not obj_type:
                    continue

                props = obj.properties if hasattr(obj, "properties") and obj.properties else {}
                gx = int(obj.x // tile_w)
                gy = int(obj.y // tile_h)

                if obj_type == "switch":
                    self._parse_switch(props, gx, gy)
                elif obj_type == "switch_door":
                    self._parse_switch_door(props, gx, gy)
                elif obj_type == "pitfall":
                    self._parse_pitfall(props, gx, gy)
                elif obj_type == "one_way":
                    self._parse_one_way(props, gx, gy)
                elif obj_type == "locked_door":
                    self._parse_locked_door(props, gx, gy)

        total = (
            len(self._switches)
            + len(self._switch_doors)
            + len(self._pitfalls)
            + len(self._one_ways)
            + len(self._locked_doors)
        )
        logger.info("Loaded %d gimmicks for map %s", total, map_id)

    # -- parsers ------------------------------------------------------

    def _parse_switch(self, props: dict, gx: int, gy: int) -> None:
        switch_id = props.get("switch_id", "")
        target = props.get("target", "")
        if not switch_id or not target:
            logger.warning("Switch at (%d, %d) missing switch_id or target", gx, gy)
            return
        self._switches.append(_SwitchData(switch_id=switch_id, grid_x=gx, grid_y=gy, target=target))
        logger.debug("Loaded switch %s at (%d, %d) -> door %s", switch_id, gx, gy, target)

    def _parse_switch_door(self, props: dict, gx: int, gy: int) -> None:
        door_id = props.get("door_id", "")
        if not door_id:
            logger.warning("Switch door at (%d, %d) missing door_id", gx, gy)
            return
        default = str(props.get("default", "closed")).lower()
        if default not in ("closed", "open"):
            default = "closed"
        self._switch_doors[door_id] = _SwitchDoorData(
            door_id=door_id, grid_x=gx, grid_y=gy, default=default
        )
        logger.debug("Loaded switch_door %s at (%d, %d) default=%s", door_id, gx, gy, default)

    def _parse_pitfall(self, props: dict, gx: int, gy: int) -> None:
        pitfall_id = props.get("pitfall_id", "")
        dest_map = props.get("dest_map", "")
        if not pitfall_id or not dest_map:
            logger.warning("Pitfall at (%d, %d) missing pitfall_id or dest_map", gx, gy)
            return
        self._pitfalls.append(_PitfallData(
            pitfall_id=pitfall_id,
            grid_x=gx,
            grid_y=gy,
            dest_map=dest_map,
            dest_x=int(props.get("dest_x", 0)),
            dest_y=int(props.get("dest_y", 0)),
            visible=bool(props.get("visible", False)),
        ))
        logger.debug("Loaded pitfall %s at (%d, %d)", pitfall_id, gx, gy)

    def _parse_one_way(self, props: dict, gx: int, gy: int) -> None:
        direction = str(props.get("direction", "")).lower()
        if direction not in _DIR_VECTORS:
            logger.warning("One-way at (%d, %d) has invalid direction %r", gx, gy, direction)
            return
        self._one_ways.append(_OneWayData(grid_x=gx, grid_y=gy, direction=direction))
        logger.debug("Loaded one_way at (%d, %d) direction=%s", gx, gy, direction)

    def _parse_locked_door(self, props: dict, gx: int, gy: int) -> None:
        door_id = props.get("door_id", "")
        key_item = props.get("key_item", "")
        if not door_id or not key_item:
            logger.warning("Locked door at (%d, %d) missing door_id or key_item", gx, gy)
            return
        self._locked_doors[door_id] = _LockedDoorData(
            door_id=door_id, grid_x=gx, grid_y=gy, key_item=key_item
        )
        logger.debug("Loaded locked_door %s at (%d, %d) key=%s", door_id, gx, gy, key_item)

    # ------------------------------------------------------------------
    # Tile blocking
    # ------------------------------------------------------------------

    def is_tile_blocked(self, x: int, y: int, move_direction: str | None = None) -> bool:
        """Check whether tile (x, y) is impassable due to a gimmick.

        Parameters
        ----------
        x, y : int
            Target grid coordinates the player wants to move *into*.
        move_direction : str or None
            The direction the player is moving (``"up"``, ``"down"``,
            ``"left"``, ``"right"``).  Required for one-way checks.
        """
        # Closed switch doors block movement
        for door in self._switch_doors.values():
            if door.grid_x == x and door.grid_y == y:
                if not self._is_switch_door_open(door):
                    return True

        # Visible pitfalls block movement
        for pit in self._pitfalls:
            if pit.grid_x == x and pit.grid_y == y:
                if self._is_pitfall_visible(pit):
                    return True

        # One-way doors: block if player is moving AGAINST the allowed direction
        if move_direction:
            for ow in self._one_ways:
                if ow.grid_x == x and ow.grid_y == y:
                    if move_direction != ow.direction:
                        return True

        # Locked doors block movement while locked
        for door in self._locked_doors.values():
            if door.grid_x == x and door.grid_y == y:
                if not self._is_locked_door_open(door.door_id):
                    return True

        return False

    # ------------------------------------------------------------------
    # Step triggers
    # ------------------------------------------------------------------

    def on_player_step(self, x: int, y: int) -> GimmickEvent | None:
        """Called when the player arrives at grid (x, y).

        Returns a :class:`GimmickEvent` if the step triggers something,
        otherwise ``None``.
        """
        # Switch step activation
        for sw in self._switches:
            if sw.grid_x == x and sw.grid_y == y:
                return self._toggle_switch(sw)

        # Hidden pitfall
        for pit in self._pitfalls:
            if pit.grid_x == x and pit.grid_y == y:
                if not self._is_pitfall_visible(pit):
                    return self._trigger_pitfall(pit)

        return None

    # ------------------------------------------------------------------
    # Action-button interaction
    # ------------------------------------------------------------------

    def interact(self, x: int, y: int, direction: str) -> GimmickEvent | None:
        """Called when the player presses the action button at (x, y) facing *direction*.

        The target tile is one step ahead in *direction*.
        """
        dx, dy = _DIR_VECTORS.get(direction, (0, 0))
        target_x = x + dx
        target_y = y + dy

        # Switch activation via action button (facing the switch)
        for sw in self._switches:
            if sw.grid_x == target_x and sw.grid_y == target_y:
                return self._toggle_switch(sw)

        # Locked door unlock
        for door in self._locked_doors.values():
            if door.grid_x == target_x and door.grid_y == target_y:
                if not self._is_locked_door_open(door.door_id):
                    return self._try_unlock_door(door)

        return None

    # ------------------------------------------------------------------
    # Switch + Door helpers
    # ------------------------------------------------------------------

    def _toggle_switch(self, sw: _SwitchData) -> GimmickEvent:
        """Toggle a switch and its linked door."""
        flag_name = f"switch_{sw.switch_id}"
        current = self._wsm.get_flag(flag_name)
        new_state = not bool(current)
        self._wsm.set_flag(flag_name, new_state)

        door = self._switch_doors.get(sw.target)
        door_open = False
        if door is not None:
            door_open = self._is_switch_door_open(door)

        state_label = "開いた" if door_open else "閉じた"
        logger.info(
            "Switch %s toggled -> %s (door %s %s)",
            sw.switch_id, new_state, sw.target, "open" if door_open else "closed",
        )
        return GimmickEvent(
            type="switch_toggle",
            data={
                "switch_id": sw.switch_id,
                "door_id": sw.target,
                "switch_state": new_state,
                "door_open": door_open,
            },
            message=f"スイッチを押した！ 扉が{state_label}！",
        )

    def _is_switch_door_open(self, door: _SwitchDoorData) -> bool:
        """Determine whether a switch-controlled door is currently open.

        Logic: if *default* is ``"closed"``, the door is open when its
        linked switch flag is ``True``, and vice versa.
        """
        # Find which switch(es) target this door
        for sw in self._switches:
            if sw.target == door.door_id:
                flag = self._wsm.get_flag(f"switch_{sw.switch_id}")
                activated = bool(flag)
                if door.default == "closed":
                    return activated
                else:  # default "open"
                    return not activated
        # No switch found — use default
        return door.default == "open"

    # ------------------------------------------------------------------
    # Pitfall helpers
    # ------------------------------------------------------------------

    def _is_pitfall_visible(self, pit: _PitfallData) -> bool:
        """A pitfall is visible if it was defined visible OR has been revealed."""
        if pit.visible:
            return True
        revealed_flag = self._wsm.get_flag(f"pitfall_{pit.pitfall_id}_revealed")
        return revealed_flag is True

    def _trigger_pitfall(self, pit: _PitfallData) -> GimmickEvent:
        """Player fell into a hidden pitfall."""
        # Mark as revealed for future visits
        self._wsm.set_flag(f"pitfall_{pit.pitfall_id}_revealed", True)
        logger.info("Player fell into pitfall %s -> %s (%d, %d)", pit.pitfall_id, pit.dest_map, pit.dest_x, pit.dest_y)
        return GimmickEvent(
            type="pitfall",
            data={
                "pitfall_id": pit.pitfall_id,
                "dest_map": pit.dest_map,
                "dest_x": pit.dest_x,
                "dest_y": pit.dest_y,
            },
            message="足元が崩れた！",
        )

    # ------------------------------------------------------------------
    # Locked door helpers
    # ------------------------------------------------------------------

    def _is_locked_door_open(self, door_id: str) -> bool:
        flag = self._wsm.get_flag(f"door_{door_id}")
        return flag is True

    def _try_unlock_door(self, door: _LockedDoorData) -> GimmickEvent:
        """Attempt to unlock a locked door with the required key item."""
        inv = self._game.inventory
        if inv.get(door.key_item, 0) <= 0:
            return GimmickEvent(
                type="one_way_block",  # reuse as "blocked" feedback
                data={"door_id": door.door_id, "key_item": door.key_item},
                message="鍵がかかっている！",
            )

        # Consume key
        current = inv.get(door.key_item, 0)
        new_count = current - 1
        if new_count <= 0:
            inv.pop(door.key_item, None)
        else:
            inv[door.key_item] = new_count

        # Permanently unlock
        self._wsm.set_flag(f"door_{door.door_id}", True)
        logger.info("Unlocked door %s with key %s", door.door_id, door.key_item)
        return GimmickEvent(
            type="door_opened",
            data={"door_id": door.door_id, "key_item": door.key_item},
            message="扉の鍵を開けた！",
        )

"""宝箱システム — Treasure Chest System

Manages treasure chests extracted from TMX map objects.
Handles chest opening, locked chests, mimics, and item/gold rewards.
"""

from dataclasses import dataclass
from typing import Any, Optional
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ChestData:
    """Data for a single treasure chest parsed from TMX."""
    chest_id: str
    grid_x: int
    grid_y: int
    item: Optional[str] = None
    quantity: int = 1
    gold: int = 0
    locked: bool = False
    key_item: Optional[str] = None
    mimic: bool = False
    enemy_group: Optional[str] = None


@dataclass
class ChestResult:
    """Result of interacting with a chest, consumed by MapScene."""
    status: str  # "opened", "locked", "mimic", "already_opened"
    item: Optional[str] = None
    quantity: int = 0
    gold: int = 0
    enemy_group: Optional[str] = None
    message: str = ""


class TreasureManager:
    """Manages treasure chests extracted from TMX map objects.

    Chests are TMX objects with ``type="chest"`` and the following
    custom properties:

    * ``chest_id`` (str, required) — unique ID persisted in world-state flags
    * ``item`` (str) — item_id to grant
    * ``quantity`` (int, default 1)
    * ``gold`` (int, default 0)
    * ``locked`` (bool, default false)
    * ``key_item`` (str) — required inventory key to unlock
    * ``mimic`` (bool, default false)
    * ``enemy_group`` (str) — encounter group spawned by mimic
    """

    def __init__(self, world_state_manager, game):
        self._wsm = world_state_manager
        self._game = game
        self._chests: dict[str, ChestData] = {}  # chest_id -> ChestData
        self._item_name_cache: Optional[dict[str, str]] = None  # lazy-loaded

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_chests(self, map_id: str, tmx_data) -> None:
        """Extract chest objects from TMX data.

        Iterates over all object groups in *tmx_data* and picks up objects
        whose ``type`` equals ``"chest"``.
        """
        self._chests.clear()
        if tmx_data is None:
            return

        tile_width = tmx_data.tilewidth
        tile_height = tmx_data.tileheight

        for obj_group in tmx_data.objectgroups:
            for obj in obj_group:
                if getattr(obj, "type", "") != "chest":
                    continue

                props = obj.properties if hasattr(obj, "properties") and obj.properties else {}
                chest_id = props.get("chest_id", "")
                if not chest_id:
                    logger.warning(
                        "Chest object without chest_id at (%s, %s)", obj.x, obj.y
                    )
                    continue

                chest = ChestData(
                    chest_id=chest_id,
                    grid_x=int(obj.x // tile_width),
                    grid_y=int(obj.y // tile_height),
                    item=props.get("item"),
                    quantity=int(props.get("quantity", 1)),
                    gold=int(props.get("gold", 0)),
                    locked=bool(props.get("locked", False)),
                    key_item=props.get("key_item"),
                    mimic=bool(props.get("mimic", False)),
                    enemy_group=props.get("enemy_group"),
                )
                self._chests[chest_id] = chest
                logger.debug(
                    "Loaded chest %s at (%d, %d)", chest_id, chest.grid_x, chest.grid_y
                )

        logger.info("Loaded %d chests for map %s", len(self._chests), map_id)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_chests(self) -> list[ChestData]:
        """Return a list of all chests on the current map."""
        return list(self._chests.values())

    def is_opened(self, chest_id: str) -> bool:
        """Check whether the chest has already been opened (via world-state flag)."""
        flag = self._wsm.get_flag(f"chest_{chest_id}")
        return flag is True

    def is_chest_at(self, x: int, y: int) -> Optional[ChestData]:
        """Return the ChestData at grid position (x, y), or None."""
        for chest in self._chests.values():
            if chest.grid_x == x and chest.grid_y == y:
                return chest
        return None

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def interact(self, chest_id: str) -> ChestResult:
        """Handle the player interacting with a chest.

        Returns a :class:`ChestResult` that the caller (e.g. MapScene) can
        use to display messages, start mimic battles, etc.
        """
        chest = self._chests.get(chest_id)
        if chest is None:
            return ChestResult(status="already_opened", message="")

        # Already opened
        if self.is_opened(chest_id):
            return ChestResult(status="already_opened", message="からっぽだ。")

        # Locked check
        if chest.locked and chest.key_item:
            inv = self._game.inventory
            if inv.get(chest.key_item, 0) <= 0:
                return ChestResult(status="locked", message="鍵がかかっている！")
            # Consume key
            current = inv.get(chest.key_item, 0)
            new_count = current - 1
            if new_count <= 0:
                inv.pop(chest.key_item, None)
            else:
                inv[chest.key_item] = new_count
            logger.info("Used key %s to open chest %s", chest.key_item, chest_id)

        # Mimic check
        if chest.mimic:
            self._wsm.set_flag(f"chest_{chest_id}", True)
            return ChestResult(
                status="mimic",
                enemy_group=chest.enemy_group,
                message="ミミックが現れた！",
            )

        # Normal open — mark as opened first
        self._wsm.set_flag(f"chest_{chest_id}", True)

        if chest.gold > 0:
            self._game.gold += chest.gold
            return ChestResult(
                status="opened",
                gold=chest.gold,
                message=f"{chest.gold}ゴールド を手に入れた！",
            )

        if chest.item:
            inv = self._game.inventory
            current = inv.get(chest.item, 0)
            inv[chest.item] = min(99, current + chest.quantity)
            item_name = self._get_item_name(chest.item)
            if chest.quantity > 1:
                msg = f"{item_name}\u00d7{chest.quantity} を手に入れた！"
            else:
                msg = f"{item_name} を手に入れた！"
            return ChestResult(
                status="opened",
                item=chest.item,
                quantity=chest.quantity,
                message=msg,
            )

        return ChestResult(status="opened", message="宝箱は空だった。")

    # ------------------------------------------------------------------
    # Item name lookup (cached)
    # ------------------------------------------------------------------

    def _get_item_name(self, item_id: str) -> str:
        """Look up the display name for *item_id* from items.json.

        The file is loaded and cached on the first call so subsequent
        lookups are O(1).
        """
        if self._item_name_cache is None:
            self._item_name_cache = self._load_item_names()
        return self._item_name_cache.get(item_id, item_id)

    def _load_item_names(self) -> dict[str, str]:
        """Parse items.json once and build a flat item_id -> name mapping."""
        cache: dict[str, str] = {}
        try:
            items_path = (
                Path(__file__).resolve().parent.parent.parent / "data" / "items.json"
            )
            with open(items_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for section in ("weapons", "armor", "accessory", "consumable", "materials"):
                for item in data.get(section, []):
                    iid = item.get("item_id")
                    name = item.get("name")
                    if iid and name:
                        cache[iid] = name
        except Exception:
            logger.warning("Failed to load items.json for name lookup", exc_info=True)
        return cache

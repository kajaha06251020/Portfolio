"""ショップシーン -- FF風の買う/売るインターフェース"""

import json
import logging
import math
from pathlib import Path

import pygame

from src.scenes.base_scene import BaseScene
from src.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    WHITE,
    BLACK,
    RED,
    GREEN,
    YELLOW,
    FONT_SIZE_SMALL,
    FONT_SIZE_MEDIUM,
    FONT_SIZE_LARGE,
    scaled,
)
from src.font import get_font
from src.ui.panel import UIPanel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Item data cache (module-level singleton so it is loaded only once)
# ---------------------------------------------------------------------------
_item_cache: dict | None = None


def _load_item_cache() -> dict:
    """Load and return the item data cache keyed by item_id.

    Each value is the raw dict from items.json with an extra ``_category``
    field (``"weapons"``, ``"armor"``, ``"accessory"``, ``"consumable"``,
    ``"materials"``).
    """
    global _item_cache
    if _item_cache is not None:
        return _item_cache

    items_path = Path(__file__).resolve().parents[2] / "data" / "items.json"
    cache: dict = {}
    try:
        with open(items_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        for category in ("weapons", "armor", "accessory", "consumable", "materials"):
            for entry in data.get(category, []):
                item_id = entry.get("item_id")
                if item_id:
                    entry_copy = dict(entry)
                    entry_copy["_category"] = category
                    cache[item_id] = entry_copy
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load items.json: %s", exc)

    _item_cache = cache
    return _item_cache


# ---------------------------------------------------------------------------
# Helper: determine which equipment slot an item occupies
# ---------------------------------------------------------------------------

def _item_equip_slot(item_data: dict) -> str | None:
    """Return the equipment slot key for an item, or None if not equippable."""
    cat = item_data.get("_category")
    if cat == "weapons":
        return "weapon"
    if cat == "armor":
        return item_data.get("slot")  # "head" or "body"
    if cat == "accessory":
        return "accessory1"  # comparison uses first accessory slot
    return None


# ---------------------------------------------------------------------------
# ShopScene
# ---------------------------------------------------------------------------

class ShopScene(BaseScene):
    """FF-style shop scene supporting buy / sell / inn."""

    # States: main, buy, buy_confirm, sell, sell_confirm, inn_confirm
    def __init__(self, game):
        super().__init__(game)

        # Fonts (lazily initialised in on_enter)
        self.font: pygame.font.Font | None = None
        self.small_font: pygame.font.Font | None = None
        self.large_font: pygame.font.Font | None = None

        # Shop data
        self.shop_id: str = ""
        self.shop_data: dict = {}
        self.shop_items: list[dict] = []  # resolved item dicts
        self.sell_rate: float = 0.5

        # State machine
        self.state: str = "main"
        self.main_options: list[str] = []
        self.cursor: int = 0

        # buy_confirm / sell_confirm
        self.quantity: int = 1
        self.selected_item: dict | None = None

        # sell list
        self.sell_items: list[tuple[str, dict, int]] = []  # (item_id, data, count)

        # Cursor image
        self.cursor_surface: pygame.Surface | None = None

        # Scroll offset for long lists
        self._buy_scroll: int = 0
        self._sell_scroll: int = 0

        # Maximum visible rows in the item list panel
        self._max_visible_rows: int = 8

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open(self, shop_id: str) -> None:
        """Configure this scene for *shop_id*.  Call before push_scene."""
        shops_path = Path(__file__).resolve().parents[2] / "data" / "shops.json"
        try:
            with open(shops_path, "r", encoding="utf-8") as fh:
                all_shops = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.error("Cannot load shops.json: %s", exc)
            all_shops = {}

        self.shop_id = shop_id
        self.shop_data = all_shops.get(shop_id, {})
        self.sell_rate = float(self.shop_data.get("sell_rate", 0.5))

        # Resolve shop inventory
        item_cache = _load_item_cache()
        self.shop_items = []
        for item_id in self.shop_data.get("items", []):
            if item_id in item_cache:
                self.shop_items.append(item_cache[item_id])
            else:
                logger.warning("Shop '%s': item_id '%s' not found in items.json -- skipped", shop_id, item_id)

        # Build main menu options depending on shop type
        shop_type = self.shop_data.get("type", "item")
        if shop_type == "inn":
            inn_price = self.shop_data.get("price", 50)
            self.main_options = [f"泊まる ({inn_price}G)", "やめる"]
        else:
            self.main_options = ["買う", "売る", "やめる"]

    # ------------------------------------------------------------------
    # Scene lifecycle
    # ------------------------------------------------------------------

    def on_enter(self):
        self.font = get_font(FONT_SIZE_MEDIUM)
        self.small_font = get_font(FONT_SIZE_SMALL)
        self.large_font = get_font(FONT_SIZE_LARGE)
        self.state = "main"
        self.cursor = 0
        self.quantity = 1
        self._buy_scroll = 0
        self._sell_scroll = 0
        self._ensure_cursor_loaded()

    def on_exit(self):
        pass

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_events(self, events: list):
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            key = event.key
            if key in (pygame.K_UP, pygame.K_w):
                self._on_up()
            elif key in (pygame.K_DOWN, pygame.K_s):
                self._on_down()
            elif key in (pygame.K_RETURN, pygame.K_z):
                self._on_confirm()
            elif key in (pygame.K_ESCAPE, pygame.K_x):
                self._on_cancel()

    # --- navigation helpers ---

    def _on_up(self):
        if self.state in ("buy_confirm", "sell_confirm"):
            self._change_quantity(1)
            return
        self._move_cursor(-1)

    def _on_down(self):
        if self.state in ("buy_confirm", "sell_confirm"):
            self._change_quantity(-1)
            return
        self._move_cursor(1)

    def _move_cursor(self, delta: int):
        count = self._option_count()
        if count <= 0:
            return
        self.cursor = (self.cursor + delta) % count
        # adjust scroll
        if self.state == "buy":
            if self.cursor < self._buy_scroll:
                self._buy_scroll = self.cursor
            elif self.cursor >= self._buy_scroll + self._max_visible_rows:
                self._buy_scroll = self.cursor - self._max_visible_rows + 1
        elif self.state == "sell":
            if self.cursor < self._sell_scroll:
                self._sell_scroll = self.cursor
            elif self.cursor >= self._sell_scroll + self._max_visible_rows:
                self._sell_scroll = self.cursor - self._max_visible_rows + 1

    def _option_count(self) -> int:
        if self.state == "main":
            return len(self.main_options)
        if self.state == "buy":
            return len(self.shop_items)
        if self.state == "sell":
            return len(self.sell_items)
        if self.state == "inn_confirm":
            return 2  # はい / いいえ
        return 0

    def _change_quantity(self, delta: int):
        if self.selected_item is None:
            return
        price = self.selected_item.get("price", 0)
        if self.state == "buy_confirm":
            max_affordable = price and (self.game.gold // price) or 99
            max_qty = min(99, max_affordable)
            self.quantity = max(1, min(max_qty, self.quantity + delta))
        elif self.state == "sell_confirm":
            # find owned count
            item_id = self.selected_item.get("item_id", "")
            owned = self.game.inventory.get(item_id, 0)
            self.quantity = max(1, min(owned, self.quantity + delta))

    # --- confirm / cancel ---

    def _on_confirm(self):
        if self.state == "main":
            self._confirm_main()
        elif self.state == "buy":
            self._confirm_buy_select()
        elif self.state == "buy_confirm":
            self._confirm_buy_execute()
        elif self.state == "sell":
            self._confirm_sell_select()
        elif self.state == "sell_confirm":
            self._confirm_sell_execute()
        elif self.state == "inn_confirm":
            self._confirm_inn()

    def _on_cancel(self):
        if self.state == "main":
            self._exit_shop()
        elif self.state in ("buy", "sell"):
            self.state = "main"
            self.cursor = 0
        elif self.state == "buy_confirm":
            self.state = "buy"
            # cursor stays on last selected item
        elif self.state == "sell_confirm":
            self.state = "sell"
        elif self.state == "inn_confirm":
            self.state = "main"
            self.cursor = 0

    # --- main menu ---

    def _confirm_main(self):
        shop_type = self.shop_data.get("type", "item")
        if shop_type == "inn":
            if self.cursor == 0:
                self.state = "inn_confirm"
                self.cursor = 0
            else:
                self._exit_shop()
            return

        if self.cursor == 0:  # 買う
            self.state = "buy"
            self.cursor = 0
            self._buy_scroll = 0
        elif self.cursor == 1:  # 売る
            self._build_sell_list()
            self.state = "sell"
            self.cursor = 0
            self._sell_scroll = 0
        elif self.cursor == 2:  # やめる
            self._exit_shop()

    # --- buy ---

    def _confirm_buy_select(self):
        if not self.shop_items:
            return
        item = self.shop_items[self.cursor]
        price = item.get("price", 0)
        if price > self.game.gold:
            return  # can't afford -- do nothing
        self.selected_item = item
        self.quantity = 1
        self.state = "buy_confirm"

    def _confirm_buy_execute(self):
        if self.selected_item is None:
            return
        item_id = self.selected_item.get("item_id", "")
        price = self.selected_item.get("price", 0)
        total = price * self.quantity
        if total > self.game.gold:
            return
        self.game.gold -= total
        self.game.inventory[item_id] = self.game.inventory.get(item_id, 0) + self.quantity
        # Return to buy list
        self.state = "buy"

    # --- sell ---

    def _build_sell_list(self):
        """Rebuild the sellable-item list from the player inventory."""
        item_cache = _load_item_cache()
        equipped_ids = self._get_equipped_item_ids()
        self.sell_items = []
        for item_id, count in self.game.inventory.items():
            if count <= 0:
                continue
            data = item_cache.get(item_id)
            if data is None:
                continue
            self.sell_items.append((item_id, data, count))

    def _confirm_sell_select(self):
        if not self.sell_items:
            return
        item_id, data, count = self.sell_items[self.cursor]
        # Check if ALL copies are equipped (can't sell)
        if self._is_fully_equipped(item_id, count):
            return
        self.selected_item = data
        self.quantity = 1
        self.state = "sell_confirm"

    def _confirm_sell_execute(self):
        if self.selected_item is None:
            return
        item_id = self.selected_item.get("item_id", "")
        price = self.selected_item.get("price", 0)
        sell_price = int(math.floor(price * self.sell_rate))
        total = sell_price * self.quantity

        owned = self.game.inventory.get(item_id, 0)
        if self.quantity > owned:
            return

        self.game.gold += total
        self.game.inventory[item_id] = owned - self.quantity
        if self.game.inventory[item_id] <= 0:
            del self.game.inventory[item_id]

        # Rebuild sell list and clamp cursor
        self._build_sell_list()
        if self.cursor >= len(self.sell_items):
            self.cursor = max(0, len(self.sell_items) - 1)
        self.state = "sell"

    # --- inn ---

    def _confirm_inn(self):
        if self.cursor == 0:  # はい
            inn_price = self.shop_data.get("price", 50)
            if self.game.gold >= inn_price:
                self.game.gold -= inn_price
                # Heal entire party
                for actor in self.game.party:
                    actor["hp"] = actor.get("max_hp", actor.get("hp", 1))
                    actor["mp"] = actor.get("max_mp", actor.get("mp", 0))
            self.state = "main"
            self.cursor = 0
        else:  # いいえ
            self.state = "main"
            self.cursor = 0

    # --- exit ---

    def _exit_shop(self):
        if hasattr(self.game, "pop_scene"):
            self.game.pop_scene()
        else:
            self.game.change_scene("map")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_equipped_item_ids(self) -> set[str]:
        """Return a set of item_ids currently equipped by any party member."""
        ids: set[str] = set()
        for actor in self.game.party:
            eq = actor.get("equipment", {})
            for v in eq.values():
                if v:
                    ids.add(v)
        return ids

    def _is_fully_equipped(self, item_id: str, owned_count: int) -> bool:
        """True when every owned copy of *item_id* is equipped (cannot sell)."""
        equipped_count = 0
        for actor in self.game.party:
            eq = actor.get("equipment", {})
            for v in eq.values():
                if v == item_id:
                    equipped_count += 1
        return equipped_count >= owned_count

    def _equipped_count(self, item_id: str) -> int:
        count = 0
        for actor in self.game.party:
            eq = actor.get("equipment", {})
            for v in eq.values():
                if v == item_id:
                    count += 1
        return count

    def _ensure_cursor_loaded(self):
        if self.cursor_surface is not None:
            return
        cursor_path = Path(__file__).resolve().parents[2] / "assets" / "images" / "UI" / "FinalFantasyCursor.png"
        try:
            image = pygame.image.load(str(cursor_path)).convert_alpha()
            target_h = scaled(16)
            ratio = target_h / max(1, image.get_height())
            target_w = max(1, int(image.get_width() * ratio))
            self.cursor_surface = pygame.transform.smoothscale(image, (target_w, target_h))
        except (pygame.error, FileNotFoundError):
            self.cursor_surface = None

    def _draw_cursor_icon(self, screen: pygame.Surface, x: int, y: int):
        if self.cursor_surface is not None:
            screen.blit(self.cursor_surface, (x, y))
        else:
            fallback = self.small_font.render("\u25b6", True, YELLOW)
            screen.blit(fallback, (x, y))

    # ------------------------------------------------------------------
    # Stat comparison helpers
    # ------------------------------------------------------------------

    def _get_stat_comparison(self, item_data: dict) -> list[tuple[str, int]]:
        """Return list of (label, diff) for the hovered equipment item.

        Compares the item's stat_bonuses against what the first party member
        currently has equipped in the corresponding slot.
        """
        slot = _item_equip_slot(item_data)
        if slot is None:
            return []

        party = self.game.party
        if not party:
            return []
        actor = party[0]

        # Current equipment in the same slot
        eq = actor.get("equipment", {})
        # For accessories, check both slots
        if slot == "accessory1":
            current_id = eq.get("accessory1") or eq.get("accessory2")
        else:
            current_id = eq.get(slot)

        item_cache = _load_item_cache()
        current_bonuses: dict = {}
        if current_id and current_id in item_cache:
            current_bonuses = item_cache[current_id].get("stat_bonuses", {})

        new_bonuses = item_data.get("stat_bonuses", {})
        all_stats = set(list(current_bonuses.keys()) + list(new_bonuses.keys()))

        stat_labels = {
            "attack": "ATK",
            "defense": "DEF",
            "magic": "MAG",
            "magic_defense": "MDEF",
            "hp": "HP",
            "mp": "MP",
            "agility": "AGI",
            "evasion": "EVA",
            "hit_rate": "HIT",
        }

        diffs: list[tuple[str, int]] = []
        for stat in sorted(all_stats):
            new_val = int(new_bonuses.get(stat, 0))
            cur_val = int(current_bonuses.get(stat, 0))
            diff = new_val - cur_val
            if diff != 0:
                label = stat_labels.get(stat, stat.upper())
                diffs.append((label, diff))
        return diffs

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self):
        pass

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen: pygame.Surface):
        screen.fill((10, 16, 46))

        if self.state == "main":
            self._draw_main(screen)
        elif self.state in ("buy", "buy_confirm"):
            self._draw_buy(screen)
        elif self.state in ("sell", "sell_confirm"):
            self._draw_sell(screen)
        elif self.state == "inn_confirm":
            self._draw_inn(screen)

        # Gold panel (always visible)
        self._draw_gold_panel(screen)

    # --- panels ---

    def _panel_menu(self) -> UIPanel:
        """Left-side main menu panel."""
        return UIPanel(
            scaled(20), scaled(20),
            scaled(160), scaled(160),
            title=self.shop_data.get("name", "ショップ"),
            bg_color=(20, 28, 70),
            border_radius=scaled(6),
            padding=scaled(10),
        )

    def _panel_items(self) -> UIPanel:
        """Right-side item list panel."""
        return UIPanel(
            scaled(190), scaled(20),
            SCREEN_WIDTH - scaled(210), scaled(340),
            title="",
            bg_color=(20, 28, 70),
            border_radius=scaled(6),
            padding=scaled(10),
        )

    def _panel_detail(self) -> UIPanel:
        """Bottom detail / stat comparison panel."""
        return UIPanel(
            scaled(20), scaled(370),
            SCREEN_WIDTH - scaled(40), scaled(120),
            title="",
            bg_color=(20, 28, 70),
            border_radius=scaled(6),
            padding=scaled(10),
        )

    def _panel_gold(self) -> UIPanel:
        """Gold display panel at the very bottom."""
        return UIPanel(
            scaled(20), scaled(500),
            SCREEN_WIDTH - scaled(40), scaled(56),
            title="",
            bg_color=(20, 28, 70),
            border_radius=scaled(6),
            padding=scaled(10),
        )

    # --- draw: main ---

    def _draw_main(self, screen: pygame.Surface):
        menu_panel = self._panel_menu()
        content = menu_panel.draw(screen, title_font=self.small_font)

        line_h = scaled(32)
        for i, label in enumerate(self.main_options):
            y = content.y + i * line_h
            color = YELLOW if i == self.cursor else WHITE
            text = self.font.render(label, True, color)
            screen.blit(text, (content.x + scaled(20), y))
            if i == self.cursor:
                self._draw_cursor_icon(screen, content.x, y + scaled(4))

        # Draw shop description in the detail area
        detail_panel = self._panel_detail()
        dc = detail_panel.draw(screen, title_font=self.small_font)
        shop_type = self.shop_data.get("type", "item")
        if shop_type == "inn":
            inn_price = self.shop_data.get("price", 50)
            msg = f"一晩 {inn_price}G でHP/MPを全回復します。"
        else:
            msg = "買う・売るを選んでください。"
        info_surf = self.small_font.render(msg, True, WHITE)
        screen.blit(info_surf, (dc.x, dc.y))

    # --- draw: buy ---

    def _draw_buy(self, screen: pygame.Surface):
        # Left menu (highlight 買う)
        menu_panel = self._panel_menu()
        mc = menu_panel.draw(screen, title_font=self.small_font)
        line_h = scaled(32)
        for i, label in enumerate(self.main_options):
            y = mc.y + i * line_h
            color = YELLOW if i == 0 else WHITE
            text = self.font.render(label, True, color)
            screen.blit(text, (mc.x + scaled(20), y))
        # static cursor on 買う
        self._draw_cursor_icon(screen, mc.x, mc.y + scaled(4))

        # Item list panel
        items_panel = self._panel_items()
        ic = items_panel.draw(screen, title_font=self.small_font)
        row_h = scaled(32)

        visible_start = self._buy_scroll
        visible_end = min(len(self.shop_items), visible_start + self._max_visible_rows)

        for draw_i, idx in enumerate(range(visible_start, visible_end)):
            item = self.shop_items[idx]
            y = ic.y + draw_i * row_h
            price = item.get("price", 0)
            can_afford = self.game.gold >= price
            is_selected = (idx == self.cursor) and self.state == "buy"

            if is_selected:
                color = YELLOW
            elif not can_afford:
                color = (128, 128, 128)
            else:
                color = WHITE

            name_surf = self.font.render(item.get("name", "???"), True, color)
            price_str = f"{price}G"
            price_surf = self.font.render(price_str, True, color)
            screen.blit(name_surf, (ic.x + scaled(20), y))
            screen.blit(price_surf, (ic.x + ic.width - price_surf.get_width() - scaled(8), y))

            if is_selected:
                self._draw_cursor_icon(screen, ic.x, y + scaled(4))

        # Scroll indicators
        if self._buy_scroll > 0:
            arrow_up = self.small_font.render("\u25b2", True, WHITE)
            screen.blit(arrow_up, (ic.x + ic.width // 2, ic.y - scaled(14)))
        if visible_end < len(self.shop_items):
            arrow_dn = self.small_font.render("\u25bc", True, WHITE)
            screen.blit(arrow_dn, (ic.x + ic.width // 2, ic.y + self._max_visible_rows * row_h))

        # Detail / stat comparison
        detail_panel = self._panel_detail()
        dc = detail_panel.draw(screen, title_font=self.small_font)
        if self.shop_items and 0 <= self.cursor < len(self.shop_items):
            hovered = self.shop_items[self.cursor]
            # Description
            desc = hovered.get("description", "")
            desc_surf = self.small_font.render(desc, True, WHITE)
            screen.blit(desc_surf, (dc.x, dc.y))
            # Stat comparison
            diffs = self._get_stat_comparison(hovered)
            if diffs:
                x_off = dc.x
                y_off = dc.y + scaled(28)
                for label, diff in diffs:
                    sign = "+" if diff > 0 else ""
                    diff_color = GREEN if diff > 0 else RED
                    diff_str = f"{label}{sign}{diff}"
                    diff_surf = self.small_font.render(diff_str, True, diff_color)
                    screen.blit(diff_surf, (x_off, y_off))
                    x_off += diff_surf.get_width() + scaled(16)

        # Quantity overlay
        if self.state == "buy_confirm" and self.selected_item:
            self._draw_quantity_overlay(screen, is_buy=True)

    # --- draw: sell ---

    def _draw_sell(self, screen: pygame.Surface):
        # Left menu (highlight 売る)
        menu_panel = self._panel_menu()
        mc = menu_panel.draw(screen, title_font=self.small_font)
        line_h = scaled(32)
        for i, label in enumerate(self.main_options):
            y = mc.y + i * line_h
            color = YELLOW if i == 1 else WHITE
            text = self.font.render(label, True, color)
            screen.blit(text, (mc.x + scaled(20), y))
        self._draw_cursor_icon(screen, mc.x, mc.y + line_h + scaled(4))

        # Sell item list
        items_panel = self._panel_items()
        ic = items_panel.draw(screen, title_font=self.small_font)
        row_h = scaled(32)

        if not self.sell_items:
            empty_surf = self.font.render("売れるアイテムがありません", True, WHITE)
            screen.blit(empty_surf, (ic.x + scaled(10), ic.y + scaled(10)))
        else:
            visible_start = self._sell_scroll
            visible_end = min(len(self.sell_items), visible_start + self._max_visible_rows)

            equipped_ids = self._get_equipped_item_ids()

            for draw_i, idx in enumerate(range(visible_start, visible_end)):
                item_id, data, count = self.sell_items[idx]
                y = ic.y + draw_i * row_h
                price = data.get("price", 0)
                sell_price = int(math.floor(price * self.sell_rate))
                is_selected = (idx == self.cursor) and self.state == "sell"
                is_equipped_all = self._is_fully_equipped(item_id, count)

                if is_equipped_all:
                    color = (128, 128, 128)
                elif is_selected:
                    color = YELLOW
                else:
                    color = WHITE

                name_str = data.get("name", item_id)
                name_surf = self.font.render(f"{name_str} x{count}", True, color)
                screen.blit(name_surf, (ic.x + scaled(20), y))

                # Sell price or 装備中
                if is_equipped_all:
                    tag_surf = self.small_font.render("\u88c5\u5099\u4e2d", True, (128, 128, 128))
                    screen.blit(tag_surf, (ic.x + ic.width - tag_surf.get_width() - scaled(8), y + scaled(4)))
                else:
                    price_surf = self.font.render(f"{sell_price}G", True, color)
                    screen.blit(price_surf, (ic.x + ic.width - price_surf.get_width() - scaled(8), y))

                    # If some copies are equipped, show partial tag
                    eq_count = self._equipped_count(item_id)
                    if eq_count > 0:
                        partial_surf = self.small_font.render(f"({eq_count}\u88c5\u5099)", True, (180, 180, 100))
                        screen.blit(partial_surf, (ic.x + ic.width - scaled(100) - partial_surf.get_width(), y + scaled(4)))

                if is_selected:
                    self._draw_cursor_icon(screen, ic.x, y + scaled(4))

            # Scroll indicators
            if self._sell_scroll > 0:
                arrow_up = self.small_font.render("\u25b2", True, WHITE)
                screen.blit(arrow_up, (ic.x + ic.width // 2, ic.y - scaled(14)))
            if visible_end < len(self.sell_items):
                arrow_dn = self.small_font.render("\u25bc", True, WHITE)
                screen.blit(arrow_dn, (ic.x + ic.width // 2, ic.y + self._max_visible_rows * row_h))

        # Detail panel
        detail_panel = self._panel_detail()
        dc = detail_panel.draw(screen, title_font=self.small_font)
        if self.sell_items and 0 <= self.cursor < len(self.sell_items):
            _, hovered_data, _ = self.sell_items[self.cursor]
            desc = hovered_data.get("description", "")
            desc_surf = self.small_font.render(desc, True, WHITE)
            screen.blit(desc_surf, (dc.x, dc.y))

        # Quantity overlay
        if self.state == "sell_confirm" and self.selected_item:
            self._draw_quantity_overlay(screen, is_buy=False)

    # --- draw: inn ---

    def _draw_inn(self, screen: pygame.Surface):
        menu_panel = self._panel_menu()
        mc = menu_panel.draw(screen, title_font=self.small_font)

        inn_price = self.shop_data.get("price", 50)
        can_afford = self.game.gold >= inn_price

        detail_panel = self._panel_detail()
        dc = detail_panel.draw(screen, title_font=self.small_font)

        question = f"一泊 {inn_price}G です。泊まりますか？"
        q_surf = self.font.render(question, True, WHITE)
        screen.blit(q_surf, (dc.x, dc.y))

        options = ["\u306f\u3044", "\u3044\u3044\u3048"]
        line_h = scaled(32)
        for i, label in enumerate(options):
            y = dc.y + scaled(36) + i * line_h
            if i == 0 and not can_afford:
                color = (128, 128, 128)
            elif i == self.cursor:
                color = YELLOW
            else:
                color = WHITE
            text = self.font.render(label, True, color)
            screen.blit(text, (dc.x + scaled(20), y))
            if i == self.cursor:
                self._draw_cursor_icon(screen, dc.x, y + scaled(4))

    # --- quantity overlay ---

    def _draw_quantity_overlay(self, screen: pygame.Surface, is_buy: bool):
        if self.selected_item is None:
            return

        overlay_w = scaled(260)
        overlay_h = scaled(140)
        overlay_x = (SCREEN_WIDTH - overlay_w) // 2
        overlay_y = (SCREEN_HEIGHT - overlay_h) // 2

        panel = UIPanel(
            overlay_x, overlay_y,
            overlay_w, overlay_h,
            title="個数選択",
            bg_color=(10, 16, 50),
            border_radius=scaled(8),
            padding=scaled(12),
        )
        oc = panel.draw(screen, title_font=self.small_font)

        name = self.selected_item.get("name", "???")
        price = self.selected_item.get("price", 0)

        if is_buy:
            unit_price = price
            label = "購入"
        else:
            unit_price = int(math.floor(price * self.sell_rate))
            label = "売却"

        total = unit_price * self.quantity

        name_surf = self.font.render(name, True, WHITE)
        screen.blit(name_surf, (oc.x, oc.y))

        qty_str = f"数量: \u25c4 {self.quantity} \u25ba"
        qty_surf = self.font.render(qty_str, True, YELLOW)
        screen.blit(qty_surf, (oc.x, oc.y + scaled(30)))

        total_str = f"{label}合計: {total}G"
        total_surf = self.small_font.render(total_str, True, WHITE)
        screen.blit(total_surf, (oc.x, oc.y + scaled(60)))

        hint_surf = self.small_font.render("Z:決定  X:戻る  ↑↓:数量", True, (180, 180, 180))
        screen.blit(hint_surf, (oc.x, oc.y + scaled(82)))

    # --- gold panel ---

    def _draw_gold_panel(self, screen: pygame.Surface):
        panel = self._panel_gold()
        gc = panel.draw(screen, title_font=self.small_font)
        gold_str = f"所持金: {self.game.gold}G"
        gold_surf = self.font.render(gold_str, True, YELLOW)
        screen.blit(gold_surf, (gc.x, gc.y))

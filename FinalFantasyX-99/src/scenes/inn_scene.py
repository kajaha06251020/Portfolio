"""宿屋シーン — Inn Scene

料金確認ダイアログ → ゴールドチェック → HP/MP 全回復。
"""
from __future__ import annotations

import logging
import pygame
from src.scenes.base_scene import BaseScene
from src.font import get_font
from src.constants import FONT_SIZE_MEDIUM, FONT_SIZE_SMALL

logger = logging.getLogger(__name__)

# Colors (match existing scene conventions)
COLOR_BG = (20, 20, 40)
COLOR_PANEL = (40, 40, 70)
COLOR_BORDER = (100, 100, 160)
COLOR_TEXT = (220, 220, 220)
COLOR_GOLD = (255, 215, 0)
COLOR_SELECT = (80, 120, 200)
COLOR_HP = (80, 200, 80)
COLOR_HP_LOW = (200, 80, 80)


class InnScene(BaseScene):
    """宿屋シーン。MapScene から push_scene("inn") で起動される。"""

    def __init__(self, game):
        super().__init__(game)
        self.price: int = 0
        self.state: str = "confirm"   # confirm | no_gold
        self.selected_index: int = 0  # 0=はい, 1=いいえ
        self.message: str = ""
        self._font: pygame.font.Font | None = None
        self._small_font: pygame.font.Font | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_price(self, price: int) -> None:
        """MapScene が push_scene の直前に呼ぶ。"""
        self.price = max(0, int(price))

    # ------------------------------------------------------------------
    # BaseScene lifecycle
    # ------------------------------------------------------------------

    def on_enter(self) -> None:
        self.state = "confirm"
        self.selected_index = 0
        self.message = ""
        if self.price == 0:
            logger.warning("InnScene entered with price=0, popping immediately")
            self.game.pop_scene()
            return
        self._load_fonts()

    def _load_fonts(self) -> None:
        self._font = get_font(FONT_SIZE_MEDIUM)
        self._small_font = get_font(FONT_SIZE_SMALL)

    def handle_events(self, events) -> None:
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if self.state == "no_gold":
                self._dismiss_no_gold(event.key)
            else:
                self._handle_confirm_key(event.key)

    def _handle_confirm_key(self, key: int) -> None:
        if key in (pygame.K_UP, pygame.K_DOWN):
            self.selected_index = 1 - self.selected_index
        elif key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
            if self.selected_index == 0:
                self._confirm_yes()
            else:
                self.game.pop_scene()
        elif key == pygame.K_ESCAPE:
            self.game.pop_scene()

    def _dismiss_no_gold(self, key: int) -> None:
        if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z, pygame.K_ESCAPE):
            self.state = "confirm"
            self.message = ""

    def _confirm_yes(self) -> None:
        if self.game.gold >= self.price:
            self.game.gold -= self.price
            self._recover_party()
            self.game.pop_scene()
        else:
            self.state = "no_gold"
            self.message = "ゴールドが足りません。"

    def _recover_party(self) -> None:
        """全パーティメンバーの HP/MP をインプレースで全回復する。"""
        for member in self.game.party:
            member["hp"] = member["max_hp"]
            member["mp"] = member["max_mp"]

    def update(self) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        if self._font is None or self._small_font is None:
            return

        W, H = screen.get_size()

        # 背景
        screen.fill(COLOR_BG)

        if self.state == "no_gold":
            self._draw_no_gold(screen, W, H)
        else:
            self._draw_confirm(screen, W, H)

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _draw_confirm(self, screen: pygame.Surface, W: int, H: int) -> None:
        # タイトル
        title = self._font.render("宿 屋", True, COLOR_TEXT)
        screen.blit(title, (W // 2 - title.get_width() // 2, 20))

        # 左パネル: パーティ状態
        panel_x, panel_y = 40, 70
        panel_w, panel_h = W // 2 - 60, H - 160
        pygame.draw.rect(screen, COLOR_PANEL, (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(screen, COLOR_BORDER, (panel_x, panel_y, panel_w, panel_h), 2)

        party = self.game.party
        for i, member in enumerate(party):
            y = panel_y + 16 + i * 44
            name = member.get("name", "???")
            hp = member.get("hp", 0)
            max_hp = member.get("max_hp", 1)

            name_surf = self._small_font.render(name, True, COLOR_TEXT)
            screen.blit(name_surf, (panel_x + 12, y))

            ratio = hp / max_hp if max_hp > 0 else 0
            bar_x = panel_x + 12
            bar_y = y + 22
            bar_w = panel_w - 24
            bar_h = 10
            pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h))
            fill_color = COLOR_HP if ratio > 0.3 else COLOR_HP_LOW
            pygame.draw.rect(screen, fill_color, (bar_x, bar_y, int(bar_w * ratio), bar_h))

            hp_text = self._small_font.render(f"HP {hp}/{max_hp}", True, COLOR_TEXT)
            screen.blit(hp_text, (panel_x + 12, bar_y + 14))

        # 右パネル: 確認
        rpanel_x = W // 2 + 20
        rpanel_y = 70
        rpanel_w = W // 2 - 60
        rpanel_h = H - 160
        pygame.draw.rect(screen, COLOR_PANEL, (rpanel_x, rpanel_y, rpanel_w, rpanel_h))
        pygame.draw.rect(screen, COLOR_BORDER, (rpanel_x, rpanel_y, rpanel_w, rpanel_h), 2)

        msg1 = self._small_font.render(f"1泊 {self.price}G です。", True, COLOR_TEXT)
        msg2 = self._small_font.render("お泊まりになりますか？", True, COLOR_TEXT)
        screen.blit(msg1, (rpanel_x + 12, rpanel_y + 20))
        screen.blit(msg2, (rpanel_x + 12, rpanel_y + 50))

        # 選択肢
        options = ["はい", "いいえ"]
        for i, opt in enumerate(options):
            oy = rpanel_y + 110 + i * 40
            if i == self.selected_index:
                pygame.draw.rect(screen, COLOR_SELECT, (rpanel_x + 8, oy - 4, rpanel_w - 16, 32))
                prefix = "▶ "
            else:
                prefix = "  "
            opt_surf = self._small_font.render(prefix + opt, True, COLOR_TEXT)
            screen.blit(opt_surf, (rpanel_x + 16, oy))

        # 所持ゴールド
        gold_surf = self._small_font.render(f"所持ゴールド: {self.game.gold}G", True, COLOR_GOLD)
        screen.blit(gold_surf, (40, H - 50))

    def _draw_no_gold(self, screen: pygame.Surface, W: int, H: int) -> None:
        # タイトル
        title = self._font.render("宿 屋", True, COLOR_TEXT)
        screen.blit(title, (W // 2 - title.get_width() // 2, 20))

        panel_x, panel_y = 60, H // 2 - 60
        panel_w, panel_h = W - 120, 120
        pygame.draw.rect(screen, COLOR_PANEL, (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(screen, COLOR_BORDER, (panel_x, panel_y, panel_w, panel_h), 2)

        msg = self._font.render("ゴールドが足りません。", True, COLOR_HP_LOW)
        hint = self._small_font.render("何かキーを押してください", True, COLOR_TEXT)
        screen.blit(msg, (W // 2 - msg.get_width() // 2, panel_y + 20))
        screen.blit(hint, (W // 2 - hint.get_width() // 2, panel_y + 70))

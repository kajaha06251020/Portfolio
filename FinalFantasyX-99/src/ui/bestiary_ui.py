"""図鑑UI — 出会った敵とアイテムを一覧表示"""

import pygame
from src.constants import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, YELLOW, FONT_SIZE_SMALL, FONT_SIZE_MEDIUM, scaled
from src.font import get_font
from src.ui.panel import UIPanel


class BestiaryUI:
    """図鑑（モンスター・アイテム）表示UI"""

    TABS = ["モンスター", "アイテム"]

    def __init__(self, game):
        self.game = game
        self.active = False
        self.tab = 0          # 0: モンスター, 1: アイテム
        self.scroll = 0
        self.font = None
        self.small_font = None

    def open(self):
        self.active = True
        self.tab = 0
        self.scroll = 0
        self.font = get_font(FONT_SIZE_MEDIUM)
        self.small_font = get_font(FONT_SIZE_SMALL)

    def close(self):
        self.active = False

    def handle_events(self, events):
        for event in events:
            if event.type != pygame.KEYDOWN:
                continue
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.close()
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.tab = (self.tab - 1) % len(self.TABS)
                self.scroll = 0
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.tab = (self.tab + 1) % len(self.TABS)
                self.scroll = 0
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.scroll = max(0, self.scroll - 1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.scroll += 1

    def _get_entries(self):
        bestiary = getattr(self.game, "bestiary", {})
        if self.tab == 0:
            seen = bestiary.get("enemies_seen", [])
            defeated = bestiary.get("enemies_defeated", {})
            if not seen:
                return ["まだ敵に遭遇していません"]
            return [f"{name}  （討伐数: {defeated.get(name, 0)}）" for name in seen]
        else:
            # アイテムタブ: 現在の所持品を表示
            inv = getattr(self.game, "inventory", {})
            entries = [f"{item_id}  x{qty}" for item_id, qty in inv.items() if qty > 0]
            return entries if entries else ["所持アイテムなし"]

    def draw(self, screen: pygame.Surface):
        if not self.active:
            return
        if not self.small_font:
            return

        # 背景パネル
        panel = UIPanel(
            scaled(30), scaled(20),
            SCREEN_WIDTH - scaled(60), SCREEN_HEIGHT - scaled(40),
            title="図鑑",
            bg_color=(10, 18, 50),
            border_radius=scaled(8),
            padding=scaled(14),
        )
        content = panel.draw(screen, title_font=self.font)

        # タブ表示
        if self.font:
            for i, tab_name in enumerate(self.TABS):
                color = YELLOW if i == self.tab else WHITE
                tab_surf = self.font.render(f"[{tab_name}]", True, color)
                screen.blit(tab_surf, (content.x + i * scaled(150), content.y))

        # エントリー一覧
        entries = self._get_entries()
        max_visible = 12
        y_start = content.y + scaled(40)
        for i, entry in enumerate(entries[self.scroll:self.scroll + max_visible]):
            text = self.small_font.render(entry, True, WHITE)
            screen.blit(text, (content.x + scaled(10), y_start + i * scaled(30)))

        # 件数表示
        count_text = self.small_font.render(
            f"{len(entries)}件  ←→タブ切替  ↑↓スクロール  ESCで閉じる", True, WHITE
        )
        screen.blit(count_text, (content.x, content.bottom - scaled(28)))

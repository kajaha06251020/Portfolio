"""
クエストログUI — Quest Log UI

Full-screen overlay for viewing quest status, organized by tabs:
メイン (main quests), サブ (sub quests), 完了済み (completed quests).
"""

import pygame
from typing import Any, List, Optional

from src.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    WHITE,
    YELLOW,
    FONT_SIZE_SMALL,
    FONT_SIZE_MEDIUM,
    scaled,
)
from src.font import get_font
from src.ui.panel import UIPanel


# Tab definitions
_TABS = ["メイン", "サブ", "完了済み"]

# Layer display info: layer_name -> (label, color)
_LAYER_COLORS = {
    "physical": ("物", (0, 200, 80)),
    "depth": ("深", (160, 80, 220)),
    "dream": ("夢", (80, 160, 255)),
}


class QuestLogUI:
    """Full-screen quest log overlay.

    Parameters
    ----------
    quest_manager : QuestManager
        Source of quest data.
    """

    def __init__(self, quest_manager: Any):
        self._qm = quest_manager
        self._active = False

        # UI state
        self._tab_index = 0
        self._selected_index = 0
        self._scroll_offset = 0

        # Fonts (initialised lazily)
        self._font: Optional[pygame.font.Font] = None
        self._small_font: Optional[pygame.font.Font] = None

        # Cached quest lists per tab
        self._cached_lists: List[List[dict]] = [[], [], []]

    # ------------------------------------------------------------------
    # Open / close
    # ------------------------------------------------------------------

    @property
    def active(self) -> bool:
        return self._active

    def open(self) -> None:
        """Open the quest log overlay."""
        self._active = True
        self._tab_index = 0
        self._selected_index = 0
        self._scroll_offset = 0
        self._ensure_fonts()
        self._refresh_lists()

    def close(self) -> None:
        """Close the quest log overlay."""
        self._active = False

    # ------------------------------------------------------------------
    # Font setup
    # ------------------------------------------------------------------

    def _ensure_fonts(self) -> None:
        if self._font is None:
            self._font = get_font(FONT_SIZE_MEDIUM)
        if self._small_font is None:
            self._small_font = get_font(FONT_SIZE_SMALL)

    # ------------------------------------------------------------------
    # Data refresh
    # ------------------------------------------------------------------

    def _refresh_lists(self) -> None:
        """Rebuild cached quest lists for all tabs."""
        if self._qm is None:
            self._cached_lists = [[], [], []]
            return

        all_quests = self._qm.get_all_quests()

        main_active = [q for q in all_quests if q["type"] == "main" and q["state"] in ("active", "available")]
        sub_active = [q for q in all_quests if q["type"] == "sub" and q["state"] in ("active", "available")]
        completed = [q for q in all_quests if q["state"] in ("completed", "failed")]

        # Sort: active first, then available; main quests by chapter
        main_active.sort(key=lambda q: (0 if q["state"] == "active" else 1, q.get("chapter") or 999))
        sub_active.sort(key=lambda q: (0 if q["state"] == "active" else 1, q["title"]))
        completed.sort(key=lambda q: q["title"])

        self._cached_lists = [main_active, sub_active, completed]

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def handle_events(self, events: list) -> None:
        if not self._active:
            return

        for event in events:
            if event.type != pygame.KEYDOWN:
                continue

            if event.key == pygame.K_ESCAPE:
                self.close()
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self._switch_tab(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._switch_tab(1)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self._move_cursor(-1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._move_cursor(1)

    def _switch_tab(self, direction: int) -> None:
        self._tab_index = (self._tab_index + direction) % len(_TABS)
        self._selected_index = 0
        self._scroll_offset = 0

    def _move_cursor(self, direction: int) -> None:
        quest_list = self._cached_lists[self._tab_index]
        if not quest_list:
            self._selected_index = 0
            return
        self._selected_index = (self._selected_index + direction) % len(quest_list)

        # Adjust scroll so selected item is visible
        max_visible = self._max_visible_items()
        if self._selected_index < self._scroll_offset:
            self._scroll_offset = self._selected_index
        elif self._selected_index >= self._scroll_offset + max_visible:
            self._scroll_offset = self._selected_index - max_visible + 1

    def _max_visible_items(self) -> int:
        """Number of quest items that fit in the list panel."""
        list_panel_height = SCREEN_HEIGHT - scaled(170)
        item_height = scaled(52)
        return max(1, (list_panel_height - scaled(40)) // item_height)

    # ------------------------------------------------------------------
    # Update (no-op, included for scene compatibility)
    # ------------------------------------------------------------------

    def update(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self, screen: pygame.Surface) -> None:
        if not self._active:
            return

        self._ensure_fonts()

        # Dark overlay background
        screen.fill((10, 16, 46))

        self._draw_tabs(screen)
        self._draw_quest_list(screen)
        self._draw_detail_panel(screen)

    def _draw_tabs(self, screen: pygame.Surface) -> None:
        """Draw the tab bar at the top."""
        tab_panel = UIPanel(
            scaled(20),
            scaled(16),
            SCREEN_WIDTH - scaled(40),
            scaled(48),
            title="",
            bg_color=(16, 24, 64),
            border_radius=scaled(6),
            padding=scaled(10),
            texture_scale=1.25,
            texture_repeat=False,
        )
        content = tab_panel.draw(screen, title_font=self._small_font)

        tab_width = scaled(120)
        start_x = content.x + scaled(10)

        for i, tab_name in enumerate(_TABS):
            x = start_x + i * (tab_width + scaled(20))
            color = YELLOW if i == self._tab_index else WHITE

            # Draw underline for selected tab
            if i == self._tab_index:
                line_y = content.y + scaled(22)
                pygame.draw.line(screen, YELLOW, (x, line_y), (x + tab_width, line_y), 2)

            text = self._font.render(tab_name, True, color)
            screen.blit(text, (x, content.y))

    def _draw_quest_list(self, screen: pygame.Surface) -> None:
        """Draw the quest list on the left side."""
        list_panel = UIPanel(
            scaled(20),
            scaled(74),
            int(SCREEN_WIDTH * 0.42),
            SCREEN_HEIGHT - scaled(100),
            title="クエスト一覧",
            bg_color=(20, 28, 74),
            border_radius=scaled(8),
            padding=scaled(12),
            texture_scale=1.55,
            texture_repeat=False,
        )
        content = list_panel.draw(screen, title_font=self._small_font)

        quest_list = self._cached_lists[self._tab_index]
        if not quest_list:
            empty_text = self._small_font.render("クエストなし", True, WHITE)
            screen.blit(empty_text, (content.x + scaled(10), content.y + scaled(10)))
            return

        item_height = scaled(52)
        max_visible = self._max_visible_items()

        for draw_i in range(max_visible):
            list_i = self._scroll_offset + draw_i
            if list_i >= len(quest_list):
                break

            quest = quest_list[list_i]
            y = content.y + draw_i * item_height
            if y + item_height > content.bottom:
                break

            is_selected = (list_i == self._selected_index)
            color = YELLOW if is_selected else WHITE

            # Selection indicator
            if is_selected:
                highlight = pygame.Surface((content.width - scaled(4), item_height - scaled(4)), pygame.SRCALPHA)
                highlight.fill((255, 255, 255, 20))
                screen.blit(highlight, (content.x + scaled(2), y))

            # Quest title
            title_text = self._small_font.render(quest["title"], True, color)
            screen.blit(title_text, (content.x + scaled(10), y + scaled(2)))

            # Layer dots
            dot_x = content.x + scaled(10)
            dot_y = y + scaled(24)
            for layer in quest.get("layers_involved", []):
                layer_info = _LAYER_COLORS.get(layer)
                if layer_info:
                    _label, dot_color = layer_info
                    pygame.draw.circle(screen, dot_color, (dot_x + scaled(5), dot_y + scaled(5)), scaled(4))
                    dot_x += scaled(14)

            # Objective text (for active quests)
            if quest.get("objective") and quest["state"] == "active":
                obj_color = (180, 200, 255) if is_selected else (140, 160, 200)
                obj_text = self._small_font.render(quest["objective"], True, obj_color)
                screen.blit(obj_text, (dot_x + scaled(6), dot_y))

            # State badge
            state_label = self._state_label(quest["state"])
            if state_label:
                badge_color = self._state_color(quest["state"])
                badge_text = self._small_font.render(state_label, True, badge_color)
                badge_x = content.right - badge_text.get_width() - scaled(10)
                screen.blit(badge_text, (badge_x, y + scaled(2)))

    def _draw_detail_panel(self, screen: pygame.Surface) -> None:
        """Draw the detail panel on the right side."""
        detail_panel = UIPanel(
            int(SCREEN_WIDTH * 0.44),
            scaled(74),
            SCREEN_WIDTH - int(SCREEN_WIDTH * 0.44) - scaled(20),
            SCREEN_HEIGHT - scaled(100),
            title="詳細",
            bg_color=(20, 28, 74),
            border_radius=scaled(8),
            padding=scaled(12),
            texture_scale=1.55,
            texture_repeat=False,
        )
        content = detail_panel.draw(screen, title_font=self._small_font)

        quest_list = self._cached_lists[self._tab_index]
        if not quest_list or self._selected_index >= len(quest_list):
            no_sel = self._small_font.render("クエストを選択してください", True, WHITE)
            screen.blit(no_sel, (content.x + scaled(10), content.y + scaled(10)))
            return

        quest = quest_list[self._selected_index]
        line_y = content.y + scaled(4)
        line_gap = scaled(30)

        # Title
        title_surf = self._font.render(quest["title"], True, YELLOW)
        screen.blit(title_surf, (content.x + scaled(4), line_y))
        line_y += line_gap + scaled(6)

        # State
        state_label = self._state_label(quest["state"])
        state_color = self._state_color(quest["state"])
        state_surf = self._small_font.render(f"状態: {state_label}", True, state_color)
        screen.blit(state_surf, (content.x + scaled(4), line_y))
        line_y += line_gap

        # Chapter (main quests only)
        if quest.get("chapter") is not None:
            chapter_surf = self._small_font.render(f"第{quest['chapter']}章", True, WHITE)
            screen.blit(chapter_surf, (content.x + scaled(4), line_y))
            line_y += line_gap

        # Description
        desc = quest.get("description", "")
        if desc:
            desc_surf = self._small_font.render(desc, True, WHITE)
            screen.blit(desc_surf, (content.x + scaled(4), line_y))
            line_y += line_gap

        # Layers
        layers = quest.get("layers_involved", [])
        if layers:
            layer_x = content.x + scaled(4)
            layer_label = self._small_font.render("関連世界層: ", True, (160, 180, 220))
            screen.blit(layer_label, (layer_x, line_y))
            layer_x += layer_label.get_width()
            for layer in layers:
                layer_info = _LAYER_COLORS.get(layer)
                if layer_info:
                    lbl, dot_color = layer_info
                    pygame.draw.circle(screen, dot_color, (layer_x + scaled(5), line_y + scaled(10)), scaled(5))
                    layer_x += scaled(14)
                    lname = self._small_font.render(lbl, True, dot_color)
                    screen.blit(lname, (layer_x, line_y))
                    layer_x += lname.get_width() + scaled(10)
            line_y += line_gap

        # Current stage/objective
        if quest.get("stage") and quest["state"] == "active":
            stage_surf = self._small_font.render(f"段階: {quest['stage']}", True, (180, 220, 255))
            screen.blit(stage_surf, (content.x + scaled(4), line_y))
            line_y += line_gap

        if quest.get("objective") and quest["state"] == "active":
            obj_surf = self._small_font.render(f"目標: {quest['objective']}", True, (200, 240, 255))
            screen.blit(obj_surf, (content.x + scaled(4), line_y))
            line_y += line_gap

        # Reward preview
        rewards = quest.get("rewards", {})
        if rewards and quest["state"] != "completed":
            line_y += scaled(6)
            reward_header = self._small_font.render("報酬:", True, (220, 200, 120))
            screen.blit(reward_header, (content.x + scaled(4), line_y))
            line_y += line_gap

            reward_parts = []
            if rewards.get("exp"):
                reward_parts.append(f"EXP {rewards['exp']}")
            if rewards.get("gold"):
                reward_parts.append(f"ギル {rewards['gold']}")
            items = rewards.get("items", [])
            for item in items:
                reward_parts.append(f"{item.get('id', '?')} x{item.get('count', 1)}")

            if reward_parts:
                reward_text = "  ".join(reward_parts)
                reward_surf = self._small_font.render(reward_text, True, (220, 200, 120))
                screen.blit(reward_surf, (content.x + scaled(14), line_y))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _state_label(state: str) -> str:
        labels = {
            "inactive": "",
            "available": "受注可",
            "active": "進行中",
            "completed": "完了",
            "failed": "失敗",
        }
        return labels.get(state, state)

    @staticmethod
    def _state_color(state: str) -> tuple:
        colors = {
            "inactive": (120, 120, 120),
            "available": (100, 220, 100),
            "active": (100, 180, 255),
            "completed": (200, 200, 100),
            "failed": (220, 80, 80),
        }
        return colors.get(state, WHITE)

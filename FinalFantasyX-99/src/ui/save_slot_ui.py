"""
セーブスロット選択UI — Save Slot UI

セーブ時のみ使用するスロット選択オーバーレイ。
3スロットを上下キーで選択し、Enter で確認、ESC でキャンセル。
"""

from typing import Callable, Optional

import pygame

from src.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    WHITE,
    BLACK,
    FONT_SIZE_SMALL,
    FONT_SIZE_MEDIUM,
    scaled,
)
from src.font import get_font

# ---------------------------------------------------------------------------
# Colour palette (dark-blue semi-transparent, matching dialogue_renderer.py)
# ---------------------------------------------------------------------------
_BG_COLOR = (10, 10, 80, 210)
_BORDER_COLOR = (200, 200, 255)
_TEXT_COLOR = WHITE
_DIM_COLOR = (160, 160, 180)
_CURSOR_COLOR = (255, 255, 100)
_HIGHLIGHT_COLOR = (60, 60, 140, 180)
_CONFIRM_BG_COLOR = (10, 10, 80, 230)
_OVERLAY_COLOR = (0, 0, 0, 160)

# ---------------------------------------------------------------------------
# Layout constants (pre-scale; scaled() applied at use-site)
# ---------------------------------------------------------------------------
_PANEL_WIDTH = 560
_PANEL_PADDING_X = 20
_PANEL_PADDING_Y = 16
_TITLE_HEIGHT = 36
_DIVIDER = 1
_SLOT_HEIGHT = 68          # height of one slot row
_BORDER_W = 3
_CURSOR_SIZE = 12
_CONFIRM_PANEL_WIDTH = 360
_CONFIRM_PANEL_HEIGHT = 110

NUM_SLOTS = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_playtime(seconds: float) -> str:
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    return f"{h}:{m:02d}:{s:02d}"


def _format_timestamp(ts: str) -> str:
    """Convert ISO-8601 timestamp to display string.

    ``"2026-03-18T20:00:00"`` → ``"2026-03-18 20:00"``
    Falls back to the original string on parse failure.
    """
    if not ts:
        return ""
    try:
        date_part, time_part = ts.split("T", 1)
        hhmm = time_part[:5]
        return f"{date_part} {hhmm}"
    except (ValueError, AttributeError):
        return ts


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class SaveSlotUI:
    """セーブスロット選択UI（セーブ時のみ使用）

    使い方:
        ui = SaveSlotUI(save_manager)
        ui.show(save_type="tile", callback=on_save_done)
        # update()/draw() をメインループから呼ぶ
        # セーブ完了 or キャンセルで callback(slot_or_None) が呼ばれる
    """

    def __init__(self, save_manager) -> None:
        self.save_manager = save_manager
        self.state: str = "HIDDEN"          # "HIDDEN" | "SLOT_SELECT" | "CONFIRM"
        self.selected_slot: int = 1         # 1-based
        self._save_type: str = "tile"
        self._callback: Optional[Callable[[Optional[int]], None]] = None

        # Fonts (lazy-initialised in _ensure_fonts)
        self._font_title: Optional[pygame.font.Font] = None
        self._font_main: Optional[pygame.font.Font] = None
        self._font_sub: Optional[pygame.font.Font] = None

        # Cached slot metadata list (refreshed each show())
        self._slots: list = []             # list of dict or None per slot

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        return self.state != "HIDDEN"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(self, save_type: str, callback: Callable[[Optional[int]], None]) -> None:
        """UIを表示する。

        Parameters
        ----------
        save_type:
            セーブのトリガー種別 (例: ``"tile"``)。現時点では表示上の参考情報。
        callback:
            セーブ完了時はスロット番号（1-based）、キャンセル時は ``None`` を受け取る。
        """
        self._save_type = save_type
        self._callback = callback
        self.selected_slot = 1
        self.state = "SLOT_SELECT"
        self._ensure_fonts()
        self._refresh_slots()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """キーボードイベントを処理する。

        Returns
        -------
        bool
            ``True`` のとき、このイベントは消費済み（上位に伝播させない）。
        """
        if self.state == "HIDDEN":
            return False

        if event.type != pygame.KEYDOWN:
            # UIが表示中はキー以外のイベントも吸収する
            return self.is_active

        if self.state == "SLOT_SELECT":
            return self._handle_slot_select(event)

        if self.state == "CONFIRM":
            return self._handle_confirm(event)

        return False

    def draw(self, screen: pygame.Surface) -> None:
        """UIを描画する（is_active のときのみ）。"""
        if not self.is_active:
            return

        self._ensure_fonts()
        self._draw_overlay(screen)
        self._draw_slot_panel(screen)

        if self.state == "CONFIRM":
            self._draw_confirm_panel(screen)

    # ------------------------------------------------------------------
    # Font setup
    # ------------------------------------------------------------------

    def _ensure_fonts(self) -> None:
        if self._font_title is None:
            self._font_title = get_font(scaled(FONT_SIZE_MEDIUM))
        if self._font_main is None:
            self._font_main = get_font(scaled(FONT_SIZE_SMALL))
        if self._font_sub is None:
            # Slightly smaller than FONT_SIZE_SMALL
            self._font_sub = get_font(scaled(int(FONT_SIZE_SMALL * 0.85)))

    # ------------------------------------------------------------------
    # Data refresh
    # ------------------------------------------------------------------

    def _refresh_slots(self) -> None:
        """save_manager からスロット情報を取得してキャッシュする。"""
        self._slots = []
        for slot_index in range(1, NUM_SLOTS + 1):
            try:
                data = self.save_manager.load_slot(slot_index)
                self._slots.append(data)
            except Exception:
                self._slots.append(None)

    # ------------------------------------------------------------------
    # Input handlers
    # ------------------------------------------------------------------

    def _handle_slot_select(self, event: pygame.event.Event) -> bool:
        if event.key == pygame.K_UP:
            self.selected_slot = (self.selected_slot - 2) % NUM_SLOTS + 1
            return True
        if event.key == pygame.K_DOWN:
            self.selected_slot = self.selected_slot % NUM_SLOTS + 1
            return True
        if event.key in (pygame.K_RETURN, pygame.K_z):
            self.state = "CONFIRM"
            return True
        if event.key == pygame.K_ESCAPE:
            self._cancel()
            return True
        return True  # consume all keys while UI is active

    def _handle_confirm(self, event: pygame.event.Event) -> bool:
        if event.key in (pygame.K_RETURN, pygame.K_y, pygame.K_z):
            self._execute_save()
            return True
        if event.key in (pygame.K_ESCAPE, pygame.K_n):
            # 確認をキャンセルしてスロット選択に戻る
            self.state = "SLOT_SELECT"
            return True
        return True

    # ------------------------------------------------------------------
    # Save execution
    # ------------------------------------------------------------------

    def _execute_save(self) -> None:
        try:
            self.save_manager.save_slot(self.selected_slot)
        except Exception:
            pass  # 呼び出し元に任せる
        slot = self.selected_slot
        self.state = "HIDDEN"
        if self._callback is not None:
            self._callback(slot)

    def _cancel(self) -> None:
        self.state = "HIDDEN"
        if self._callback is not None:
            self._callback(None)

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _draw_overlay(self, screen: pygame.Surface) -> None:
        """画面全体に半透明の黒オーバーレイを描画する。"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(_OVERLAY_COLOR)
        screen.blit(overlay, (0, 0))

    def _panel_rect(self) -> pygame.Rect:
        """メインパネルの Rect を計算して返す。"""
        panel_w = scaled(_PANEL_WIDTH)
        title_h = scaled(_TITLE_HEIGHT)
        slot_h = scaled(_SLOT_HEIGHT)
        pad_y = scaled(_PANEL_PADDING_Y)
        panel_h = title_h + scaled(_DIVIDER) + slot_h * NUM_SLOTS + pad_y * 2
        panel_x = (SCREEN_WIDTH - panel_w) // 2
        panel_y = (SCREEN_HEIGHT - panel_h) // 2
        return pygame.Rect(panel_x, panel_y, panel_w, panel_h)

    def _draw_box(self, screen: pygame.Surface, rect: pygame.Rect, color=_BG_COLOR) -> None:
        """半透明ボックスに白い枠を描いて blit する。"""
        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        surf.fill(color)
        screen.blit(surf, rect.topleft)
        pygame.draw.rect(screen, _BORDER_COLOR, rect, scaled(_BORDER_W))

    def _draw_slot_panel(self, screen: pygame.Surface) -> None:
        panel = self._panel_rect()
        self._draw_box(screen, panel)

        pad_x = scaled(_PANEL_PADDING_X)
        pad_y = scaled(_PANEL_PADDING_Y)
        title_h = scaled(_TITLE_HEIGHT)
        slot_h = scaled(_SLOT_HEIGHT)

        # ----- タイトル行 -----
        title_surf = self._font_title.render("セーブデータを選択", True, _TEXT_COLOR)
        title_x = panel.x + (panel.width - title_surf.get_width()) // 2
        title_y = panel.y + pad_y
        screen.blit(title_surf, (title_x, title_y))

        # タイトル下の仕切り線
        divider_y = panel.y + pad_y + title_h
        pygame.draw.line(
            screen, _BORDER_COLOR,
            (panel.x + scaled(4), divider_y),
            (panel.right - scaled(4), divider_y),
            1,
        )

        # ----- スロット行 -----
        for i in range(NUM_SLOTS):
            slot_num = i + 1
            row_y = divider_y + i * slot_h
            row_rect = pygame.Rect(panel.x, row_y, panel.width, slot_h)

            is_selected = (slot_num == self.selected_slot)

            # 選択ハイライト
            if is_selected:
                hl_surf = pygame.Surface((row_rect.width - scaled(6), row_rect.height - scaled(4)), pygame.SRCALPHA)
                hl_surf.fill(_HIGHLIGHT_COLOR)
                screen.blit(hl_surf, (row_rect.x + scaled(3), row_rect.y + scaled(2)))

            # スロット行の下仕切り（最終行以外）
            if i < NUM_SLOTS - 1:
                sep_y = row_rect.bottom - 1
                pygame.draw.line(
                    screen, (80, 80, 140),
                    (panel.x + scaled(4), sep_y),
                    (panel.right - scaled(4), sep_y),
                    1,
                )

            # カーソル ▶
            cursor_x = panel.x + pad_x
            cursor_mid_y = row_rect.y + row_rect.height // 2
            if is_selected:
                cs = scaled(_CURSOR_SIZE)
                tri_points = [
                    (cursor_x, cursor_mid_y - cs // 2),
                    (cursor_x, cursor_mid_y + cs // 2),
                    (cursor_x + cs, cursor_mid_y),
                ]
                pygame.draw.polygon(screen, _CURSOR_COLOR, tri_points)

            # テキスト描画開始 X
            text_x = panel.x + pad_x + scaled(_CURSOR_SIZE) + scaled(8)
            slot_data = self._slots[i] if i < len(self._slots) else None

            self._draw_slot_row(screen, slot_num, slot_data, text_x, row_rect, is_selected)

    def _draw_slot_row(
        self,
        screen: pygame.Surface,
        slot_num: int,
        slot_data: Optional[dict],
        text_x: int,
        row_rect: pygame.Rect,
        is_selected: bool,
    ) -> None:
        """1 スロット分のテキストを描画する。"""
        pad_y_inner = scaled(8)
        line1_y = row_rect.y + pad_y_inner
        line2_y = line1_y + self._font_main.get_linesize()

        main_color = _CURSOR_COLOR if is_selected else _TEXT_COLOR
        sub_color = (200, 200, 140) if is_selected else _DIM_COLOR

        slot_label = f"スロット {slot_num}"

        if slot_data is None:
            # データなし
            label_surf = self._font_main.render(slot_label, True, main_color)
            screen.blit(label_surf, (text_x, line1_y + (row_rect.height - label_surf.get_height()) // 2 - scaled(4)))

            empty_surf = self._font_sub.render("（データなし）", True, _DIM_COLOR)
            screen.blit(empty_surf, (text_x + label_surf.get_width() + scaled(16), line1_y + (row_rect.height - empty_surf.get_height()) // 2 - scaled(4)))
        else:
            # 1行目: スロットラベル  マップ名  Lv.XX
            label_surf = self._font_main.render(slot_label, True, main_color)
            screen.blit(label_surf, (text_x, line1_y))

            map_name = str(slot_data.get("map_name", ""))
            level = slot_data.get("level", "")
            if map_name:
                map_surf = self._font_main.render(map_name, True, main_color)
                screen.blit(map_surf, (text_x + label_surf.get_width() + scaled(16), line1_y))

            if level != "":
                lv_text = f"Lv.{level}"
                lv_surf = self._font_main.render(lv_text, True, main_color)
                lv_x = row_rect.right - scaled(20) - lv_surf.get_width()
                screen.blit(lv_surf, (lv_x, line1_y))

            # 2行目: タイムスタンプ  プレイ: H:MM:SS
            ts_raw = str(slot_data.get("timestamp", ""))
            ts_text = _format_timestamp(ts_raw)
            playtime = slot_data.get("playtime", 0.0)
            pt_text = f"プレイ: {_format_playtime(float(playtime))}"

            if ts_text:
                ts_surf = self._font_sub.render(ts_text, True, sub_color)
                screen.blit(ts_surf, (text_x, line2_y))

            pt_surf = self._font_sub.render(pt_text, True, sub_color)
            pt_x = row_rect.right - scaled(20) - pt_surf.get_width()
            screen.blit(pt_surf, (pt_x, line2_y))

    def _draw_confirm_panel(self, screen: pygame.Surface) -> None:
        """「上書き / セーブしますか？」確認ウィンドウを描画する。"""
        cw = scaled(_CONFIRM_PANEL_WIDTH)
        ch = scaled(_CONFIRM_PANEL_HEIGHT)
        cx = (SCREEN_WIDTH - cw) // 2
        cy = (SCREEN_HEIGHT - ch) // 2
        confirm_rect = pygame.Rect(cx, cy, cw, ch)

        self._draw_box(screen, confirm_rect, _CONFIRM_BG_COLOR)

        pad_x = scaled(_PANEL_PADDING_X)
        pad_y = scaled(_PANEL_PADDING_Y)

        # メッセージ
        slot_data = self._slots[self.selected_slot - 1] if (self.selected_slot - 1) < len(self._slots) else None
        if slot_data is not None:
            msg = f"スロット{self.selected_slot}に上書きしますか？"
        else:
            msg = f"スロット{self.selected_slot}にセーブしますか？"

        msg_surf = self._font_main.render(msg, True, _TEXT_COLOR)
        msg_x = confirm_rect.x + (confirm_rect.width - msg_surf.get_width()) // 2
        msg_y = confirm_rect.y + pad_y
        screen.blit(msg_surf, (msg_x, msg_y))

        # 操作ヒント
        hint = "Enter / Y : はい     N / ESC : いいえ"
        hint_surf = self._font_sub.render(hint, True, _DIM_COLOR)
        hint_x = confirm_rect.x + (confirm_rect.width - hint_surf.get_width()) // 2
        hint_y = confirm_rect.bottom - pad_y - hint_surf.get_height()
        screen.blit(hint_surf, (hint_x, hint_y))

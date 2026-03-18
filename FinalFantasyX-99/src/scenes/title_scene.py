"""
タイトルシーン
"""

from pathlib import Path
import pygame
from src.scenes.base_scene import BaseScene
from src.audio_manager import get_audio_manager
from src.constants import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, YELLOW, FONT_SIZE_LARGE, FONT_SIZE_MEDIUM, scaled
from src.font import get_font


class TitleScene(BaseScene):
    """タイトル画面のシーン"""
    
    def __init__(self, game):
        super().__init__(game)
        self.menu_items = ["はじめから", "つづきから", "おわる"]
        self.selected_index = 0
        self.font_large = None
        self.font_medium = None
        self.audio_manager = get_audio_manager()
        self.cursor_surface = None
        self.save_slot_ui = None
        self._status_message: str = ""

    def on_enter(self):
        """シーンに入った時の初期化"""
        self.font_large = get_font(FONT_SIZE_LARGE * 2)
        self.font_medium = get_font(FONT_SIZE_MEDIUM)
        self.selected_index = 0
        self._status_message = ""
        self._ensure_cursor_loaded()

        # タイトルBGMを再生
        self.audio_manager.play_bgm("title", fade_in=500)
    
    def handle_events(self, events: list):
        """イベント処理"""
        # SaveSlotUI がアクティブなときはそちらにすべてのイベントを渡す
        if self.save_slot_ui is not None and self.save_slot_ui.is_active:
            for event in events:
                self.save_slot_ui.handle_event(event)
            return

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_DOWN):
                    self._status_message = ""
                    self.selected_index = (
                        self.selected_index + (-1 if event.key == pygame.K_UP else 1)
                    ) % len(self.menu_items)
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    self._select_menu_item()
    
    def _select_menu_item(self):
        """メニュー項目を選択"""
        if self.selected_index == 0:  # はじめから
            self.game.change_scene("map")
        elif self.selected_index == 1:  # つづきから
            save_manager = getattr(self.game, "save_manager", None)
            if save_manager is None or not save_manager.has_any_save():
                self._status_message = "セーブデータがありません"
            else:
                self._status_message = ""
                if self.save_slot_ui is None:
                    from src.ui.save_slot_ui import SaveSlotUI
                    self.save_slot_ui = SaveSlotUI(self.game)
                self.save_slot_ui.show_load(self._on_load_slot_selected)
        elif self.selected_index == 2:  # おわる
            self.game.running = False

    def _on_load_slot_selected(self, slot):
        """ロードスロット選択コールバック"""
        if slot is None:
            return  # キャンセル
        save_manager = getattr(self.game, "save_manager", None)
        if save_manager and save_manager.load(slot):
            self.game.change_scene("map")
        else:
            self._status_message = "ロードに失敗しました"
    
    def update(self):
        """更新処理"""
        pass

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

    def _draw_cursor(self, screen: pygame.Surface, x: int, y: int):
        if self.cursor_surface is not None:
            screen.blit(self.cursor_surface, (x, y))
            return
        fallback = self.font_medium.render(">", True, YELLOW)
        screen.blit(fallback, (x, y))
    
    def draw(self, screen: pygame.Surface):
        """描画処理"""
        # 背景
        screen.fill((0, 0, 0))
        
        # タイトル
        title_text = self.font_large.render("Final Fantasy X-99", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
        screen.blit(title_text, title_rect)
        
        # メニュー項目
        for i, item in enumerate(self.menu_items):
            color = WHITE
            text = self.font_medium.render(item, True, color)
            text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + i * scaled(40)))
            screen.blit(text, text_rect)
            
            # 選択カーソル
            if i == self.selected_index:
                if self.cursor_surface is not None:
                    cursor_w = self.cursor_surface.get_width()
                    cursor_h = self.cursor_surface.get_height()
                else:
                    cursor_w, cursor_h = self.font_medium.size(">")

                cursor_x = text_rect.left - cursor_w - scaled(8)
                cursor_y = text_rect.centery - cursor_h // 2 + scaled(2)
                self._draw_cursor(screen, cursor_x, cursor_y)

        # ステータスメッセージ（セーブなし等）
        if self._status_message:
            msg_surf = self.font_medium.render(self._status_message, True, (255, 100, 100))
            msg_rect = msg_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + len(self.menu_items) * scaled(40) + scaled(16)))
            screen.blit(msg_surf, msg_rect)

        # セーブスロットUIオーバーレイ
        if self.save_slot_ui is not None:
            self.save_slot_ui.draw(screen)

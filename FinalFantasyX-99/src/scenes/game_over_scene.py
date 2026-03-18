"""
ゲームオーバーシーン — Game Over Scene

全滅後に表示される画面。「全滅した...」テキスト + SE を流し、
任意キーで最後のセーブ地点へ自動復帰する。
"""

import pygame
from src.scenes.base_scene import BaseScene
from src.audio_manager import get_audio_manager
from src.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from src.font import get_font

import logging

logger = logging.getLogger(__name__)

_FADE_SPEED = 4   # alpha per frame during fade-in
_TEXT = "全滅した..."


class GameOverScene(BaseScene):
    """ゲームオーバー画面シーン。

    フロー:
    1. on_enter: BGM停止 → SE再生 → フェードイン開始
    2. フェードイン完了後: テキスト表示・キー待ち
    3. 任意キー: セーブデータがあれば最後のセーブをロード → ペナルティ適用 → map へ
               セーブデータがなければ title へ
    """

    def __init__(self, game):
        super().__init__(game)
        self._alpha = 0
        self._fading = False
        self._ready = False   # フェードイン完了フラグ
        self._font_large = get_font(48)
        self._font_small = get_font(22)
        self._audio = get_audio_manager()

    # ------------------------------------------------------------------
    # Scene lifecycle
    # ------------------------------------------------------------------

    def on_enter(self):
        self._alpha = 0
        self._fading = True
        self._ready = False

        # BGM停止
        self._audio.stop_bgm()

        # ゲームオーバーSE
        if not self._audio.play_se("se_gameover"):
            # se_gameover が登録されていなければ別名も試みる
            self._audio.play_se("gameover")

        logger.info("GameOverScene entered")

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_events(self, events: list):
        if not self._ready:
            return
        for event in events:
            if event.type == pygame.KEYDOWN:
                self._proceed()
                return

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self):
        if self._fading:
            self._alpha = min(255, self._alpha + _FADE_SPEED)
            if self._alpha >= 255:
                self._fading = False
                self._ready = True

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, screen: pygame.Surface):
        # 暗い背景
        bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        bg.fill((0, 0, 0))
        bg.set_alpha(self._alpha)
        screen.blit(bg, (0, 0))

        if not self._ready:
            return

        # メインテキスト「全滅した...」
        text_surf = self._font_large.render(_TEXT, True, (220, 50, 50))
        x = SCREEN_WIDTH // 2 - text_surf.get_width() // 2
        y = SCREEN_HEIGHT // 2 - text_surf.get_height() // 2 - 20
        screen.blit(text_surf, (x, y))

        # サブテキスト（キー案内）
        hint_surf = self._font_small.render("何かキーを押してください", True, (180, 180, 180))
        hx = SCREEN_WIDTH // 2 - hint_surf.get_width() // 2
        hy = y + text_surf.get_height() + 20
        screen.blit(hint_surf, (hx, hy))

    # ------------------------------------------------------------------
    # Proceed after key press
    # ------------------------------------------------------------------

    def _proceed(self):
        save_manager = getattr(self.game, "save_manager", None)
        if save_manager is None:
            logger.warning("GameOverScene: save_manager not found, going to title")
            self.game.change_scene("title")
            return

        if not save_manager.has_any_save():
            logger.info("GameOverScene: no save data, going to title")
            self.game.change_scene("title")
            return

        # 最後のセーブをロード
        save_manager.load_latest()
        save_manager.apply_game_over_penalty()

        # 神父セーブポイントからの復帰なら特殊セリフフラグをセット
        if save_manager.get_save_type() == "npc_priest":
            map_scene = self.game.scenes.get("map")
            if map_scene is not None:
                map_scene._pending_priest_dialogue = True

        self.game.change_scene("map")

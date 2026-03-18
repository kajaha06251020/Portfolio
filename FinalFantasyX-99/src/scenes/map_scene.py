import logging
import pygame
import json
from pathlib import Path
import pytmx
from pytmx.util_pygame import load_pygame
from src.scenes.base_scene import BaseScene
from src.entities.player import Player
from src.battle.encounter import EncounterManager
from src.entities.enemy_system import EnemyGroup
from src.audio_manager import get_audio_manager
from src.constants import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, WHITE, FONT_SIZE_SMALL, scaled
from src.font import get_font
from src.npc.npc_manager import NPCManager
from src.npc.dialogue_renderer import DialogueRenderer

logger = logging.getLogger(__name__)


class MapScene(BaseScene):
    """マップ画面のシーン"""
    
    def __init__(self, game):
        super().__init__(game)
        self.player = Player(0, 0)
        self.encounter_steps = 0
        self.encounter_rate = 30  # 何歩ごとにエンカウント判定
        self.project_root = Path(__file__).resolve().parents[2]
        
        # 新しいマップシステム
        self.maps_data = self._load_maps()
        self.current_map = "DQ_OverWorld"
        self.current_map_data = self.maps_data.get(self.current_map)
        self.encounter_manager = EncounterManager()
        self.player_grid_pos = [8, 6]  # 初期グリッド座標
        self.transition_cooldown = 0
        
        # 背景画像・BGM
        self.background_image = None
        self.audio_manager = get_audio_manager()
        self.map_backgrounds = {}  # キャッシュ

        # TMXマップ
        self.tmx_data = None
        self.tmx_surface = None
        self.tmx_tile_scale = 1
        self.map_pixel_width = 0
        self.map_pixel_height = 0
        self.map_width_tiles = 0
        self.map_height_tiles = 0
        self.camera_x = 0
        self.camera_y = 0
        self.map_tile_layers = []
        self.warp_areas = []

        self.fade_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.fade_alpha = 0
        self.fade_state = None  # None | "out" | "in"
        self.fade_speed = 18
        self.pending_transition = None
        self.map_tmx_files = self._build_map_tmx_files()
        self.return_points = {}
        self.warp_block_tile = None

        self.blocked_tile_types = {"wall", "sea", "mountain"}

        # NPC・ダイアログシステム
        self.npc_manager = None      # ScriptEngine接続後に初期化
        self.dialogue_renderer = DialogueRenderer()
        self.current_npcs = []       # 現在のマップに表示中のNPC一覧
        self.dialogue_coroutine = None  # 実行中の対話コルーチン
        self.dialogue_npc_id = None    # 対話中のNPC ID
        self._current_layer = "physical"  # ワールドレイヤー
        self._npc_label_font = get_font(scaled(12))

        # 宝箱・ギミック管理（game.py側で初期化後に設定される）
        self.treasure_manager = None
        self.gimmick_manager = None
        self.door_manager = None

        # スクリプトフェード/ウェイト（対話コルーチン用）
        self._script_fade_state = None   # "out" / "in" / None
        self._script_fade_alpha = 0
        self._script_wait_timer = 0.0
        self._script_fade_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self._script_fade_surface.fill((0, 0, 0))

        # ロケーション名表示
        self._location_name_text = ""
        self._location_name_alpha = 0
        self._location_name_timer = 0.0
        self._location_name_phase = None  # "in" / "hold" / "out" / None
        self._location_name_last_map = None

        # ボスバトル結果（push_scene経由のバトルから戻った時用）
        self._pending_coroutine_result = None
        
    def _load_maps(self):
        """マップデータを読み込み"""
        try:
            maps_file = self.project_root / "data" / "maps.json"
            with open(maps_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {m["map_id"]: m for m in data.get("maps", [])}
        except Exception as e:
            print(f"マップデータの読み込みに失敗: {e}")
            return {}

    def _build_map_tmx_files(self):
        """maps.json を元に map_id -> tmx ファイル名を構築"""
        files = {}
        for map_id, map_data in self.maps_data.items():
            tmx_name = map_data.get("tmx")
            if not tmx_name:
                tmx_name = f"{map_id}.tmx"
            files[map_id] = tmx_name
        return files
    
    def init_npc_system(self, script_engine):
        """ScriptEngine接続後にNPCManagerを初期化"""
        self.npc_manager = NPCManager(script_engine)

    def _load_chests_and_gimmicks(self):
        """現在のマップの宝箱・ギミックをTMXから読み込み"""
        if self.treasure_manager is not None and self.tmx_data is not None:
            self.treasure_manager.load_chests(self.current_map, self.tmx_data)
        if self.gimmick_manager is not None and self.tmx_data is not None:
            self.gimmick_manager.load_gimmicks(self.current_map, self.tmx_data)
        if self.door_manager is not None and self.tmx_data is not None:
            self.door_manager.load_from_tmx(self.current_map, self.tmx_data)
            self.door_manager.on_door_opened = self._on_door_animation_complete
            self.door_manager._on_tile_removed_callback = self._redraw_tmx_surface

    def _load_npcs_for_current_map(self):
        """現在のマップ/レイヤーのNPCを取得"""
        if self.npc_manager is None:
            self.current_npcs = []
            return
        self.current_npcs = self.npc_manager.get_npcs_for_map(
            self.current_map, self._current_layer
        )

    def on_enter(self):
        """シーンに入った時の初期化"""
        self.current_map_data = self.maps_data.get(self.current_map)
        self.encounter_manager.set_current_location(self.current_map)
        self.fade_state = None
        self.fade_alpha = 0
        self.pending_transition = None

        # マップサイズ設定（TMX優先）
        self._load_tmx_map()
        if self.tmx_data:
            self.map_width_tiles = self.tmx_data.width
            self.map_height_tiles = self.tmx_data.height
        else:
            self.map_width_tiles = self.current_map_data.get("width", 16) if self.current_map_data else 16
            self.map_height_tiles = self.current_map_data.get("height", 12) if self.current_map_data else 12

        start_x = min(self.player_grid_pos[0], max(0, self.map_width_tiles - 1))
        start_y = min(self.player_grid_pos[1], max(0, self.map_height_tiles - 1))
        self.player.set_grid_position(start_x, start_y)
        self._update_camera()

        # NPCを読み込み
        self._load_npcs_for_current_map()

        # 宝箱・ギミックを読み込み
        self._load_chests_and_gimmicks()

        # ロケーション名表示
        if self.current_map != self._location_name_last_map:
            self._location_name_last_map = self.current_map
            display_name = ""
            if self.current_map_data:
                display_name = self.current_map_data.get("display_name", "")
            if display_name:
                self._location_name_text = display_name
                self._location_name_alpha = 0
                self._location_name_timer = 0.0
                self._location_name_phase = "in"

        # BGMを再生
        self._play_map_bgm()
    
    def handle_events(self, events: list):
        """イベント処理"""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.fade_state is not None:
                    continue

                # ダイアログ中はDialogueRendererにイベントを渡す
                if self.dialogue_renderer.is_active:
                    consumed = self.dialogue_renderer.handle_event(event)
                    if consumed:
                        # ダイアログが完了したらコルーチンを再開
                        if not self.dialogue_renderer.is_active:
                            self._advance_dialogue()
                    continue

                # アクションキー (Enter / Space / Z): NPC会話 → 宝箱 → ギミック
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                    if self._try_start_npc_dialogue():
                        continue
                    if self._try_interact_chest():
                        continue
                    if self._try_interact_gimmick():
                        continue

                if event.key == pygame.K_ESCAPE:
                    self._begin_transition({"kind": "scene", "scene": "menu"})
                elif event.key == pygame.K_b:
                    # BGMのON/OFF切り替え
                    if self.audio_manager.bgm_playing:
                        self.audio_manager.pause_bgm()
                        print("BGM paused")
                    else:
                        self.audio_manager.unpause_bgm()
                        print("BGM resumed")
    
    def on_resume(self):
        """push_sceneから戻った時の処理（ショップ終了後・ボスバトル終了後等）"""
        # ボスバトルからの帰還チェック
        battle_result = getattr(self.game, '_last_battle_result', None)
        if battle_result is not None:
            self.game._last_battle_result = None
            self._pending_coroutine_result = battle_result

        if self.dialogue_coroutine is not None:
            self._advance_dialogue()

    def update(self):
        """更新処理"""
        if self.fade_state is not None:
            self._update_fade_transition()
            return

        # ドアアニメーション中は入力をロック
        if self.door_manager is not None and self.door_manager.is_animating():
            self.door_manager.update(1.0 / 60.0)
            return

        # スクリプトフェード/ウェイト処理
        if self._script_fade_state is not None or self._script_wait_timer > 0:
            self._update_script_effects()
            return

        # ダイアログ中はプレイヤー移動とエンカウントをブロック
        if self.dialogue_renderer.is_active or self.dialogue_coroutine is not None:
            self.dialogue_renderer.update()
            return

        # ロケーション名フェード更新
        self._update_location_name()

        # NPC移動の更新
        if self.npc_manager is not None:
            self.npc_manager.update_npcs(self.current_map, self._current_layer, 1.0 / 60.0)

        # ドアアニメーション更新（アニメ中以外も毎フレーム状態管理のため呼ぶ）
        if self.door_manager is not None:
            self.door_manager.update(1.0 / 60.0)

        step_completed = self.player.update()

        # 長押しで1マスずつ継続移動
        if not self.player.is_grid_moving:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self._try_player_step(-1, 0)
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self._try_player_step(1, 0)
            elif keys[pygame.K_UP] or keys[pygame.K_w]:
                self._try_player_step(0, -1)
            elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                self._try_player_step(0, 1)

        self._update_camera()

        # 現在のゾーンを更新
        self._update_current_zone()

        # エンカウント判定（新システム）
        if step_completed:
            if self.transition_cooldown > 0:
                self.transition_cooldown -= 1

            # ギミック判定（落とし穴等）
            self._check_gimmick_step()

            if self._check_tmx_warp():
                return

            if self._check_map_transition():
                return

            self.encounter_steps += 1

            # エンカウント判定
            if self.encounter_steps >= self.encounter_rate:
                self._try_encounter()
                self.encounter_steps = 0

    def _point_in_zone(self, x: int, y: int, zone: dict) -> bool:
        zone_x = zone.get("x", 0)
        zone_y = zone.get("y", 0)
        zone_width = zone.get("width", 0)
        zone_height = zone.get("height", 0)
        return zone_x <= x < zone_x + zone_width and zone_y <= y < zone_y + zone_height

    def _find_entry_position(self, map_data: dict, entry_zone_id: str | None):
        if not map_data or not entry_zone_id:
            return None

        search_groups = [
            map_data.get("transitions", []),
            map_data.get("safe_zones", []),
            map_data.get("encounter_zones", []),
        ]

        for zones in search_groups:
            for zone in zones:
                if zone.get("zone_id") != entry_zone_id:
                    continue
                center_x = zone.get("x", 0) + max(0, zone.get("width", 1) - 1) // 2
                center_y = zone.get("y", 0) + max(0, zone.get("height", 1) - 1) // 2
                return [center_x, center_y]

        return None

    def _check_map_transition(self):
        """遷移ゾーンに入ったらマップ遷移を行う"""
        if self.transition_cooldown > 0 or not self.current_map_data:
            return False

        player_x = self.player.grid_x
        player_y = self.player.grid_y
        transitions = self.current_map_data.get("transitions", [])

        for transition in transitions:
            if not self._point_in_zone(player_x, player_y, transition):
                continue

            next_map_id = transition.get("to_map")
            if not next_map_id:
                return False

            next_map_data = self.maps_data.get(next_map_id)
            if not next_map_data:
                return False

            self._begin_transition(
                {
                    "kind": "map",
                    "map_id": next_map_id,
                    "entry": transition.get("to_entry"),
                    "x": None,
                    "y": None,
                }
            )
            return True

        return False

    def _check_tmx_warp(self):
        """TMXのワープ判定を実行"""
        if self.transition_cooldown > 0 or not self.warp_areas:
            return False

        if self.warp_block_tile is not None:
            blocked_map_id, blocked_x, blocked_y = self.warp_block_tile
            if blocked_map_id == self.current_map:
                if self.player.grid_x != blocked_x or self.player.grid_y != blocked_y:
                    self.warp_block_tile = None

        tile_w = self.tmx_data.tilewidth * self.tmx_tile_scale if self.tmx_data else TILE_SIZE
        tile_h = self.tmx_data.tileheight * self.tmx_tile_scale if self.tmx_data else TILE_SIZE
        player_rect = pygame.Rect(self.player.grid_x * tile_w, self.player.grid_y * tile_h, tile_w, tile_h)
        if self.warp_block_tile is not None:
            blocked_map_id, blocked_x, blocked_y = self.warp_block_tile
            if blocked_map_id == self.current_map and self.player.grid_x == blocked_x and self.player.grid_y == blocked_y:
                return False

        for warp in self.warp_areas:
            if not player_rect.colliderect(warp["rect"]):
                continue

            if warp.get("scene"):
                if warp.get("scene") in {"menu", "title"}:
                    continue
                self._begin_transition({"kind": "scene", "scene": warp.get("scene")})
                return True

            map_id = warp.get("map_id")
            if not map_id:
                return False

            self._begin_transition(
                {
                    "kind": "map",
                    "map_id": map_id,
                    "entry": warp.get("dest_entry"),
                    "x": warp.get("dest_x"),
                    "y": warp.get("dest_y"),
                }
            )
            return True

        return False

    def _begin_transition(self, transition: dict):
        """フェード付き遷移を開始"""
        if self.fade_state is not None:
            return

        if transition.get("kind") == "map":
            target_map_id = transition.get("map_id")
            if self._is_field_map(self.current_map) and self._is_settlement_or_dungeon_map(target_map_id):
                self.return_points[target_map_id] = {
                    "map_id": self.current_map,
                    "x": self.player.grid_x,
                    "y": self.player.grid_y,
                }

        self.pending_transition = transition
        self.fade_alpha = 0
        self.fade_state = "out"
        self.audio_manager.play_se("Warp")

    def _is_field_map(self, map_id: str | None) -> bool:
        map_key = str(map_id or "").lower()
        return map_key in {"dq_overworld", "field", "overworld"} or "field" in map_key or "overworld" in map_key

    def _is_settlement_or_dungeon_map(self, map_id: str | None) -> bool:
        if not map_id:
            return False
        map_key = str(map_id).lower()
        if self._is_field_map(map_key):
            return False
        map_data = self.maps_data.get(map_id) or {}
        map_name = str(map_data.get("name", "")).lower()
        tokens = ["town", "castle", "dungeon", "cave", "城", "町", "洞窟"]
        return any(token in map_key or token in map_name for token in tokens)

    def _update_script_effects(self):
        """スクリプトフェード/ウェイト処理（宿屋のevent.fade_out等）"""
        fade_speed = 15

        if self._script_fade_state == "out":
            self._script_fade_alpha = min(255, self._script_fade_alpha + fade_speed)
            if self._script_fade_alpha >= 255:
                self._script_fade_state = None
                # フェードアウト完了 → コルーチンresume
                self._advance_dialogue()
            return

        if self._script_fade_state == "in":
            self._script_fade_alpha = max(0, self._script_fade_alpha - fade_speed)
            if self._script_fade_alpha <= 0:
                self._script_fade_alpha = 0
                self._script_fade_state = None
                # フェードイン完了 → コルーチンresume
                self._advance_dialogue()
            return

        if self._script_wait_timer > 0:
            self._script_wait_timer -= 1.0 / 60.0
            if self._script_wait_timer <= 0:
                self._script_wait_timer = 0.0
                # ウェイト完了 → コルーチンresume
                self._advance_dialogue()
            return

    def _update_location_name(self):
        """ロケーション名のフェードイン/ホールド/フェードアウトを更新"""
        if self._location_name_phase is None:
            return

        if self._location_name_phase == "in":
            self._location_name_alpha = min(255, self._location_name_alpha + 8)
            if self._location_name_alpha >= 255:
                self._location_name_phase = "hold"
                self._location_name_timer = 2.0  # 2秒間表示

        elif self._location_name_phase == "hold":
            self._location_name_timer -= 1.0 / 60.0
            if self._location_name_timer <= 0:
                self._location_name_phase = "out"

        elif self._location_name_phase == "out":
            self._location_name_alpha = max(0, self._location_name_alpha - 6)
            if self._location_name_alpha <= 0:
                self._location_name_phase = None

    def _draw_location_name(self, screen: pygame.Surface):
        """ロケーション名を画面上部に描画"""
        if self._location_name_phase is None or self._location_name_alpha <= 0:
            return

        font = get_font(scaled(20))
        text_surf = font.render(self._location_name_text, True, WHITE)

        # 背景バー
        bar_w = text_surf.get_width() + scaled(60)
        bar_h = text_surf.get_height() + scaled(16)
        bar_x = (SCREEN_WIDTH - bar_w) // 2
        bar_y = scaled(40)

        bg_surf = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
        bg_surf.fill((0, 0, 0, min(180, self._location_name_alpha)))
        # 枠線
        pygame.draw.rect(bg_surf, (200, 180, 120, min(200, self._location_name_alpha)), (0, 0, bar_w, bar_h), 2)
        screen.blit(bg_surf, (bar_x, bar_y))

        # テキスト
        text_surf.set_alpha(self._location_name_alpha)
        text_x = bar_x + (bar_w - text_surf.get_width()) // 2
        text_y = bar_y + (bar_h - text_surf.get_height()) // 2
        screen.blit(text_surf, (text_x, text_y))

    def _draw_location_markers(self, screen: pygame.Surface):
        """ワールドマップ上にロケーションマーカーを描画"""
        if not self._is_field_map(self.current_map):
            return
        if not self.warp_areas:
            return

        # パルスアニメーション
        import math
        pulse = 0.7 + 0.3 * math.sin(pygame.time.get_ticks() * 0.003)

        for warp in self.warp_areas:
            map_id = warp.get("map_id")
            if not map_id:
                continue

            # マーカーの色を決定
            map_data = self.maps_data.get(map_id, {})
            map_name = str(map_data.get("name", "")).lower()
            map_key = str(map_id).lower()

            if any(t in map_key or t in map_name for t in ["town", "村", "町"]):
                color = (80, 140, 255)  # 青 (町)
            elif any(t in map_key or t in map_name for t in ["cave", "dungeon", "洞窟"]):
                color = (255, 80, 80)  # 赤 (ダンジョン)
            elif any(t in map_key or t in map_name for t in ["castle", "城"]):
                color = (255, 220, 60)  # 黄 (城)
            else:
                continue  # マーカーを描画しない

            rect = warp["rect"]
            cx = rect.centerx - self.camera_x
            cy = rect.centery - self.camera_y
            radius = int(scaled(6) * pulse)

            # 外側のグロー
            glow_surf = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*color, 60), (radius * 2, radius * 2), radius * 2)
            screen.blit(glow_surf, (cx - radius * 2, cy - radius * 2))

            # メインの点
            pygame.draw.circle(screen, color, (cx, cy), radius)
            pygame.draw.circle(screen, WHITE, (cx, cy), max(1, radius - scaled(2)))

            # ラベル
            label_font = get_font(scaled(10))
            display_name = map_data.get("display_name", map_data.get("name", map_id))
            label = label_font.render(display_name, True, WHITE)
            label_x = cx - label.get_width() // 2
            label_y = cy - radius - label.get_height() - scaled(2)
            # ラベル背景
            bg = pygame.Surface((label.get_width() + scaled(4), label.get_height() + scaled(2)), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 140))
            screen.blit(bg, (label_x - scaled(2), label_y - scaled(1)))
            screen.blit(label, (label_x, label_y))

    def _update_fade_transition(self):
        """フェードの進行を更新"""
        if self.fade_state == "out":
            self.fade_alpha = min(255, self.fade_alpha + self.fade_speed)
            if self.fade_alpha >= 255:
                self._apply_pending_transition()
                self.fade_state = "in"
            return

        if self.fade_state == "in":
            self.fade_alpha = max(0, self.fade_alpha - self.fade_speed)
            if self.fade_alpha <= 0:
                self.fade_alpha = 0
                self.fade_state = None
                self.pending_transition = None

    def _apply_pending_transition(self):
        """フェード中点で遷移を確定"""
        transition = self.pending_transition or {}
        kind = transition.get("kind")

        if kind == "scene":
            scene_name = transition.get("scene")
            if scene_name in self.game.scenes:
                self.game.change_scene(scene_name)
            self.transition_cooldown = 8
            return

        source_map_id = self.current_map
        map_id = transition.get("map_id")
        if not map_id:
            self.transition_cooldown = 4
            return

        next_map_data = self.maps_data.get(map_id, {"map_id": map_id, "width": 16, "height": 12})
        self.current_map = map_id
        self.current_map_data = next_map_data

        next_x = transition.get("x")
        next_y = transition.get("y")

        return_point = self.return_points.get(source_map_id)
        if return_point and return_point.get("map_id") == map_id and self._is_field_map(map_id):
            next_x = return_point.get("x")
            next_y = return_point.get("y")

        if next_x is None or next_y is None:
            next_pos = self._find_entry_position(next_map_data, transition.get("entry"))
            if next_pos is None:
                next_pos = [0, 0]
            next_x, next_y = next_pos

        self.player_grid_pos[0] = int(next_x)
        self.player_grid_pos[1] = int(next_y)

        self._load_tmx_map()
        if self.tmx_data:
            self.map_width_tiles = self.tmx_data.width
            self.map_height_tiles = self.tmx_data.height
        else:
            self.map_width_tiles = next_map_data.get("width", 16)
            self.map_height_tiles = next_map_data.get("height", 12)

        self.player_grid_pos[0] = min(max(0, self.player_grid_pos[0]), max(0, self.map_width_tiles - 1))
        self.player_grid_pos[1] = min(max(0, self.player_grid_pos[1]), max(0, self.map_height_tiles - 1))

        self.player.set_grid_position(self.player_grid_pos[0], self.player_grid_pos[1])
        self.warp_block_tile = (self.current_map, self.player_grid_pos[0], self.player_grid_pos[1])
        self.encounter_manager.set_current_location(self.current_map, None)
        self._update_current_zone()
        self._update_camera()
        self._play_map_bgm()
        self._load_npcs_for_current_map()
        self._load_chests_and_gimmicks()
        self.encounter_steps = 0
        self.transition_cooldown = 8

    # ------------------------------------------------------------------
    # NPC対話
    # ------------------------------------------------------------------

    def _try_start_npc_dialogue(self) -> bool:
        """プレイヤーの向いている方向のNPCと会話を開始"""
        if self.npc_manager is None:
            return False
        if self.dialogue_coroutine is not None:
            return False

        npc = self.npc_manager.get_npc_in_direction(
            self.current_map,
            self._current_layer,
            self.player.grid_x,
            self.player.grid_y,
            self.player.direction,
        )
        if npc is None:
            return False

        # NPCをプレイヤーの方に向かせる
        self.npc_manager.face_player(npc.id, self.player.grid_x, self.player.grid_y)

        # コルーチンを開始
        runner = self.npc_manager.start_dialogue(npc.id)
        if runner is None:
            return False

        self.dialogue_coroutine = runner
        self.dialogue_npc_id = npc.id
        self._advance_dialogue()
        return True

    def _advance_dialogue(self) -> None:
        """コルーチンを進めて次のダイアログ命令を処理"""
        runner = self.dialogue_coroutine
        if runner is None:
            return

        # キャンセルされた場合はコルーチンを終了
        if self.dialogue_renderer.is_cancelled:
            self.dialogue_coroutine = None
            self.dialogue_npc_id = None
            self.dialogue_renderer.reset()
            return

        # ボスバトル結果 or 選択肢の結果を送る
        pending_result = self._pending_coroutine_result
        if pending_result is not None:
            self._pending_coroutine_result = None
        choice_result = self.dialogue_renderer.get_choice_result()

        try:
            if pending_result is not None:
                yielded = runner.send(pending_result)
            elif choice_result is not None:
                yielded = runner.send(choice_result)
            else:
                yielded = next(runner)
        except StopIteration:
            # コルーチン終了
            self.dialogue_coroutine = None
            self.dialogue_npc_id = None
            self.dialogue_renderer.reset()
            return

        # 命令を処理
        if yielded is None:
            # コルーチンがNoneをyieldした場合は終了
            self.dialogue_coroutine = None
            self.dialogue_npc_id = None
            self.dialogue_renderer.reset()
            return

        if isinstance(yielded, tuple):
            cmd = yielded[0]
            if cmd == "say" and len(yielded) >= 3:
                speaker = str(yielded[1])
                text = str(yielded[2])
                self.dialogue_renderer.show_dialogue(speaker, text)
            elif cmd == "choice" and len(yielded) >= 2:
                options_raw = yielded[1]
                # Lua tableをPythonリストに変換
                options = self._lua_table_to_list(options_raw)
                self.dialogue_renderer.show_choice(options)
            elif cmd == "shop" and len(yielded) >= 2:
                # ショップ遷移: コルーチンを保持したままShopSceneへ
                shop_id = str(yielded[1])
                shop_scene = self.game.scenes.get("shop")
                if shop_scene:
                    shop_scene.open(shop_id)
                    self.game.push_scene("shop")
                else:
                    logger.warning("ShopScene not registered")
            elif cmd == "fade_out":
                self._script_fade_state = "out"
                self._script_fade_alpha = 0
            elif cmd == "fade_in":
                self._script_fade_state = "in"
                self._script_fade_alpha = 255
            elif cmd == "wait" and len(yielded) >= 2:
                self._script_wait_timer = float(yielded[1])
            elif cmd == "battle" and len(yielded) >= 2:
                # ボスバトル: コルーチンを保持したままバトルシーンへ
                enemy_type = str(yielded[1])
                count = int(yielded[2]) if len(yielded) >= 3 else 1
                level = int(yielded[3]) if len(yielded) >= 4 else 1
                self._start_script_battle(enemy_type, count, level)
            else:
                logger.warning("Unknown dialogue command: %s", cmd)
                self.dialogue_coroutine = None
                self.dialogue_npc_id = None
                self.dialogue_renderer.reset()
        else:
            # 単一値の場合（"say"など）
            logger.warning("Unexpected yield value: %s", yielded)
            self.dialogue_coroutine = None
            self.dialogue_npc_id = None
            self.dialogue_renderer.reset()

    def _lua_table_to_list(self, lua_table) -> list:
        """Luaテーブル（配列）をPythonリストに変換"""
        if isinstance(lua_table, (list, tuple)):
            return [str(x) for x in lua_table]
        # lupa Lua table: iterate with items or integer keys
        result = []
        try:
            # Try to iterate as a table with integer keys
            i = 1
            while True:
                val = lua_table[i]
                if val is None:
                    break
                result.append(str(val))
                i += 1
        except (TypeError, KeyError, IndexError):
            # Fallback: try iter
            try:
                for v in lua_table.values():
                    result.append(str(v))
            except Exception:
                result = [str(lua_table)]
        return result if result else ["..."]

    def _try_player_step(self, dx: int, dy: int):
        """プレイヤーの1マス移動を試行"""
        if self.player.try_move_grid(
            dx,
            dy,
            self.map_width_tiles,
            self.map_height_tiles,
            blocked_checker=self._is_blocked_tile
        ):
            self.player_grid_pos[0] = self.player.target_grid_x
            self.player_grid_pos[1] = self.player.target_grid_y

    def _update_camera(self):
        """プレイヤー中心でカメラ座標を更新"""
        if self.map_pixel_width <= 0 or self.map_pixel_height <= 0:
            self.camera_x = 0
            self.camera_y = 0
            return

        player_center_x = int(self.player.x + self.player.width // 2)
        player_center_y = int(self.player.y + self.player.height // 2)

        desired_x = player_center_x - SCREEN_WIDTH // 2
        desired_y = player_center_y - SCREEN_HEIGHT // 2

        max_camera_x = max(0, self.map_pixel_width - SCREEN_WIDTH)
        max_camera_y = max(0, self.map_pixel_height - SCREEN_HEIGHT)

        self.camera_x = max(0, min(desired_x, max_camera_x))
        self.camera_y = max(0, min(desired_y, max_camera_y))
    
    def _update_current_zone(self):
        """プレイヤーの現在のゾーンを更新"""
        if not self.current_map_data:
            return

        self.encounter_manager.update_location_by_position(
            self.current_map,
            self.player.grid_x,
            self.player.grid_y,
        )
    
    def _try_encounter(self):
        """エンカウント判定を実行"""
        party = getattr(self.game, "party", None)
        if not party:
            party = [{"level": 1}]
        encounter_group = self.encounter_manager.trigger_encounter(party)
        
        if encounter_group:
            # エンカウント効果音
            self.audio_manager.play_se("se_encounter")

            rewards_data = self.encounter_manager.build_encounter_rewards(encounter_group)
            
            # 戦闘シーンへ遷移
            self.game.scenes["battle"].start_battle_with_group(encounter_group, rewards_data)
            self.game.change_scene("battle")
    
    def _load_map_background(self):
        """マップ背景画像を読み込み"""
        self.background_image = None

    def _load_tmx_map(self):
        """TMX/TSX を読み込み、描画用Surfaceを構築"""
        self.tmx_data = None
        self.tmx_surface = None
        self.map_pixel_width = 0
        self.map_pixel_height = 0
        self.map_tile_layers = []
        self.warp_areas = []

        tmx_name = self.map_tmx_files.get(self.current_map)
        if not tmx_name:
            return

        tmx_rel = Path(str(tmx_name).replace("\\", "/"))
        if tmx_rel.parts and tmx_rel.parts[0].lower() == "maps":
            tmx_rel = Path(*tmx_rel.parts[1:])
        tmx_path = self.project_root / "assets" / "Maps" / tmx_rel
        if not tmx_path.exists():
            print(f"⚠️ TMXファイルが見つかりません: {tmx_path}")
            return

        try:
            self.tmx_data = load_pygame(str(tmx_path))
            self.tmx_tile_scale = max(1, int(TILE_SIZE // self.tmx_data.tilewidth))
            tile_width = self.tmx_data.tilewidth * self.tmx_tile_scale
            tile_height = self.tmx_data.tileheight * self.tmx_tile_scale
            self.map_pixel_width = self.tmx_data.width * tile_width
            self.map_pixel_height = self.tmx_data.height * tile_height
            self.map_tile_layers = [
                index for index, layer in enumerate(self.tmx_data.layers)
                if isinstance(layer, pytmx.TiledTileLayer)
            ]
            self._build_tmx_surface(tile_width, tile_height)
            self._extract_tmx_warps(tile_width, tile_height)
            print(f"🗺️ TMXマップを読み込み: {tmx_name}")
        except Exception as e:
            print(f"❌ TMX読み込みに失敗: {tmx_name} - {e}")
            self.tmx_data = None
            self.tmx_surface = None

    def _extract_tmx_warps(self, tile_width: int, tile_height: int):
        """TMXからワープ領域（オブジェクト/タイル）を抽出"""
        if self.tmx_data is None:
            return

        self.warp_areas = []

        for obj in self.tmx_data.objects:
            props = dict(getattr(obj, "properties", {}) or {})
            obj_name = str(getattr(obj, "name", "")).strip().lower()
            obj_type = str(getattr(obj, "type", "")).strip().lower()
            if not self._is_warp_marker(obj_name, obj_type, props):
                continue

            warp_data = self._parse_warp_properties(props)
            if not warp_data:
                continue

            rect_x = int(round(getattr(obj, "x", 0) * self.tmx_tile_scale))
            rect_y = int(round(getattr(obj, "y", 0) * self.tmx_tile_scale))
            rect_w = int(round((getattr(obj, "width", 0) or self.tmx_data.tilewidth) * self.tmx_tile_scale))
            rect_h = int(round((getattr(obj, "height", 0) or self.tmx_data.tileheight) * self.tmx_tile_scale))
            rect = pygame.Rect(rect_x, rect_y, max(1, rect_w), max(1, rect_h))

            self.warp_areas.append({"rect": rect, **warp_data})

        for layer_index, layer in enumerate(self.tmx_data.layers):
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue

            layer_name = str(getattr(layer, "name", "")).strip().lower()
            for y in range(self.tmx_data.height):
                for x in range(self.tmx_data.width):
                    gid = self.tmx_data.get_tile_gid(x, y, layer_index)
                    if gid == 0:
                        continue

                    props = self.tmx_data.get_tile_properties(x, y, layer_index) or self.tmx_data.get_tile_properties_by_gid(gid) or {}
                    if not self._is_warp_marker("", layer_name, props):
                        continue

                    warp_data = self._parse_warp_properties(props)
                    if not warp_data:
                        continue

                    rect = pygame.Rect(x * tile_width, y * tile_height, tile_width, tile_height)
                    self.warp_areas.append({"rect": rect, **warp_data})

    def _is_warp_marker(self, name_or_type: str, layer_or_type: str, props: dict) -> bool:
        """ワープ定義候補かを判定"""
        if name_or_type == "warp" or layer_or_type == "warp":
            return True

        warp_keys = {
            "dest_map",
            "dest_scene",
            "dest_x",
            "dest_y",
            "dest_entry",
            "to_map",
            "to_scene",
            "to_entry",
            "targetmap",
            "targetx",
            "targety",
        }
        lower_keys = {str(k).strip().lower() for k in props.keys()}
        return bool(lower_keys.intersection(warp_keys))

    def _parse_warp_properties(self, props: dict):
        """TMXプロパティから遷移情報を抽出"""
        lower_props = {str(k).strip().lower(): v for k, v in props.items()}

        dest_scene = lower_props.get("dest_scene") or lower_props.get("to_scene")
        raw_dest_map = lower_props.get("dest_map") or lower_props.get("to_map") or lower_props.get("targetmap")
        dest_map_id = self._resolve_map_id_from_dest(raw_dest_map) if raw_dest_map else None

        dest_x = self._safe_int(lower_props.get("dest_x", lower_props.get("targetx")))
        dest_y = self._safe_int(lower_props.get("dest_y", lower_props.get("targety")))
        dest_entry = lower_props.get("dest_entry") or lower_props.get("to_entry")

        if not dest_scene and not dest_map_id:
            return None

        return {
            "scene": str(dest_scene) if dest_scene else None,
            "map_id": dest_map_id,
            "dest_x": dest_x,
            "dest_y": dest_y,
            "dest_entry": str(dest_entry) if dest_entry else None,
        }

    def _safe_int(self, value):
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _resolve_map_id_from_dest(self, dest_map):
        """dest_map 文字列から map_id を解決"""
        dest_str = str(dest_map).strip() if dest_map is not None else ""
        if not dest_str:
            return None

        if dest_str in self.maps_data:
            return dest_str

        normalized = dest_str.replace("\\", "/")
        file_name = Path(normalized).name
        stem_name = Path(file_name).stem

        for map_id, tmx_file in self.map_tmx_files.items():
            tmx_name = str(tmx_file)
            if tmx_name.lower() == file_name.lower() or Path(tmx_name).stem.lower() == stem_name.lower():
                return map_id

        candidate_tmx = file_name if file_name.lower().endswith(".tmx") else f"{stem_name}.tmx"
        candidate_path = self.project_root / "assets" / "Maps" / candidate_tmx
        if candidate_path.exists():
            dynamic_map_id = stem_name
            if dynamic_map_id not in self.map_tmx_files:
                self.map_tmx_files[dynamic_map_id] = candidate_tmx
            if dynamic_map_id not in self.maps_data:
                self.maps_data[dynamic_map_id] = {
                    "map_id": dynamic_map_id,
                    "name": dynamic_map_id,
                    "width": 16,
                    "height": 12,
                    "encounter_rate": 0,
                    "encounter_zones": [],
                    "safe_zones": [],
                    "transitions": [],
                }
            return dynamic_map_id

        return None

    def _build_tmx_surface(self, tile_width: int, tile_height: int):
        """TMXタイルを1枚のSurfaceにレンダリング"""
        self.tmx_surface = pygame.Surface((self.map_pixel_width, self.map_pixel_height), pygame.SRCALPHA)
        scaled_cache = {}

        for layer in self.tmx_data.visible_layers:
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue

            for x, y, image in layer.tiles():
                if image is None:
                    continue

                key = id(image)
                if key not in scaled_cache:
                    if self.tmx_tile_scale != 1:
                        scaled_cache[key] = pygame.transform.scale(image, (tile_width, tile_height))
                    else:
                        scaled_cache[key] = image

                self.tmx_surface.blit(scaled_cache[key], (x * tile_width, y * tile_height))

    def _is_blocked_tile(self, tile_x: int, tile_y: int, direction: str = None) -> bool:
        """指定タイルが通行不可か判定（NPCタイル・宝箱・ギミックも含む）"""
        # NPCがいるタイルはブロック
        for npc in self.current_npcs:
            if npc.grid_x == tile_x and npc.grid_y == tile_y:
                return True

        # 宝箱チェック
        if hasattr(self, 'treasure_manager') and self.treasure_manager is not None:
            if self.treasure_manager.is_chest_at(tile_x, tile_y):
                return True

        # ギミックチェック（方向対応: 一方通行ドア等）
        if hasattr(self, 'gimmick_manager') and self.gimmick_manager is not None:
            if self.gimmick_manager.is_tile_blocked(tile_x, tile_y, direction):
                return True

        # ドアチェック（閉じたドアはブロック。開く処理はupdate内で実施）
        if self.door_manager is not None:
            if self.door_manager.is_tile_blocked(tile_x, tile_y):
                result = self.door_manager.try_open(tile_x, tile_y, self.game.inventory)
                if result is None:
                    return True
                if result.status in ("locked_no_key", "locked_wrong_key"):
                    self.dialogue_renderer.show_dialogue("", result.message)
                    return True
                # status == "opened": ドアが開いた
                if result.dest_map:
                    self._begin_door_transition(result)
                return False  # 通過OK

        if self.tmx_data is None:
            return False

        for layer_index in self.map_tile_layers:
            gid = self.tmx_data.get_tile_gid(tile_x, tile_y, layer_index)
            if gid == 0:
                continue

            properties = self.tmx_data.get_tile_properties_by_gid(gid) or {}
            tile_type = str(properties.get("Type", "")).strip().lower()
            if tile_type in self.blocked_tile_types:
                return True

        return False
    
    def _play_map_bgm(self):
        """マップBGMを再生"""
        map_data = self.current_map_data or {}
        map_id = str(self.current_map).lower()
        map_name = str(map_data.get("name", "")).lower()

        candidates = []

        explicit_music = map_data.get("music")
        if explicit_music:
            candidates.append(str(explicit_music))

        if any(token in map_id or token in map_name for token in ["dungeon", "cave", "洞窟"]):
            candidates.extend(["Dungeon", "dungeon"])
        elif any(token in map_id or token in map_name for token in ["town", "village", "城下町", "町"]):
            candidates.extend(["Town", "town"])
        elif any(token in map_id or token in map_name for token in ["castle", "城"]):
            candidates.extend(["Castle", "castle"])
        else:
            candidates.append("field")

        if "field" not in candidates:
            candidates.append("field")

        for bgm_id in candidates:
            if self.audio_manager.play_bgm(bgm_id, fade_in=500):
                return
    
    def _draw_npcs(self, screen: pygame.Surface, offset_x: int = 0, offset_y: int = 0):
        """NPCをマップ上に描画（プレースホルダー矩形+名前ラベル）"""
        tile_w = TILE_SIZE
        tile_h = TILE_SIZE
        if self.tmx_data:
            tile_w = self.tmx_data.tilewidth * self.tmx_tile_scale
            tile_h = self.tmx_data.tileheight * self.tmx_tile_scale

        margin = scaled(4)
        npc_w = tile_w - margin
        npc_h = tile_h - margin

        for npc in self.current_npcs:
            # 表示判定
            if self.npc_manager and not self.npc_manager.check_visibility(npc.id):
                continue

            draw_x = int(npc.grid_x * tile_w + offset_x)
            draw_y = int(npc.grid_y * tile_h + offset_y)

            # NPC矩形（緑色）
            npc_color = (0, 200, 80)
            pygame.draw.rect(screen, npc_color, (draw_x, draw_y, npc_w, npc_h))

            # 向きの三角形
            cx = draw_x + npc_w // 2
            cy = draw_y + npc_h // 2
            tri_size = scaled(6)
            if npc.facing == "up":
                pts = [(cx, draw_y), (cx - tri_size, draw_y + tri_size * 2), (cx + tri_size, draw_y + tri_size * 2)]
            elif npc.facing == "down":
                pts = [(cx, draw_y + npc_h), (cx - tri_size, draw_y + npc_h - tri_size * 2), (cx + tri_size, draw_y + npc_h - tri_size * 2)]
            elif npc.facing == "left":
                pts = [(draw_x, cy), (draw_x + tri_size * 2, cy - tri_size), (draw_x + tri_size * 2, cy + tri_size)]
            else:
                pts = [(draw_x + npc_w, cy), (draw_x + npc_w - tri_size * 2, cy - tri_size), (draw_x + npc_w - tri_size * 2, cy + tri_size)]
            pygame.draw.polygon(screen, WHITE, pts)

            # 名前ラベル
            label = self._npc_label_font.render(npc.name, True, WHITE)
            label_x = draw_x + (npc_w - label.get_width()) // 2
            label_y = draw_y - label.get_height() - scaled(2)
            # ラベル背景
            bg_rect = pygame.Rect(label_x - scaled(2), label_y - scaled(1), label.get_width() + scaled(4), label.get_height() + scaled(2))
            bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            bg_surf.fill((0, 0, 0, 140))
            screen.blit(bg_surf, bg_rect.topleft)
            screen.blit(label, (label_x, label_y))

    def _draw_chests(self, screen: pygame.Surface, offset_x: int = 0, offset_y: int = 0):
        """宝箱をマップ上に描画"""
        if self.treasure_manager is None:
            return

        tile_w = TILE_SIZE
        tile_h = TILE_SIZE
        if self.tmx_data:
            tile_w = self.tmx_data.tilewidth * self.tmx_tile_scale
            tile_h = self.tmx_data.tileheight * self.tmx_tile_scale

        margin = scaled(6)
        for chest in self.treasure_manager.get_chests():
            draw_x = int(chest.grid_x * tile_w + offset_x) + margin
            draw_y = int(chest.grid_y * tile_h + offset_y) + margin
            w = tile_w - margin * 2
            h = tile_h - margin * 2

            opened = self.treasure_manager.is_opened(chest.chest_id)
            if opened:
                # 開封済み: 暗い茶色
                pygame.draw.rect(screen, (80, 50, 20), (draw_x, draw_y, w, h))
                pygame.draw.rect(screen, (60, 40, 15), (draw_x, draw_y, w, h), 2)
            else:
                # 未開封: 茶色 + 黄色の帯
                pygame.draw.rect(screen, (139, 90, 43), (draw_x, draw_y, w, h))
                band_h = max(4, h // 4)
                pygame.draw.rect(screen, (220, 180, 50), (draw_x, draw_y + h // 2 - band_h // 2, w, band_h))
                pygame.draw.rect(screen, (100, 65, 30), (draw_x, draw_y, w, h), 2)

    def _try_interact_chest(self) -> bool:
        """プレイヤーの前の宝箱と対話を試みる"""
        if self.treasure_manager is None:
            return False

        # プレイヤーの向いている方向の1マス先
        dx, dy = 0, 0
        if self.player.direction == "up": dy = -1
        elif self.player.direction == "down": dy = 1
        elif self.player.direction == "left": dx = -1
        elif self.player.direction == "right": dx = 1

        target_x = self.player.grid_x + dx
        target_y = self.player.grid_y + dy

        chest = self.treasure_manager.is_chest_at(target_x, target_y)
        if chest is None:
            return False

        result = self.treasure_manager.interact(chest.chest_id)

        if result.status == "mimic":
            # ミミック: メッセージ表示後バトル遷移
            self.dialogue_renderer.show_dialogue("", result.message)
            # TODO: バトル遷移（enemy_groupを使ってエンカウント）
            return True

        if result.message:
            self.dialogue_renderer.show_dialogue("", result.message)

        return True

    def _check_gimmick_step(self):
        """移動完了時にギミック判定（落とし穴等）"""
        if self.gimmick_manager is None:
            return

        event = self.gimmick_manager.on_player_step(self.player.grid_x, self.player.grid_y)
        if event is None:
            return

        if event.type == "pitfall":
            # 落とし穴: フェード遷移で下の階へ
            dest = event.data
            self.pending_transition = {
                "kind": "map",
                "map_id": dest.get("dest_map", ""),
                "x": dest.get("dest_x", 0),
                "y": dest.get("dest_y", 0),
            }
            self.fade_state = "out"
            self.fade_alpha = 0
        elif event.type == "switch_toggle":
            if event.message:
                self.dialogue_renderer.show_dialogue("", event.message)

    def _start_script_battle(self, enemy_type: str, count: int, level: int):
        """スクリプトからのボスバトルを開始（push_scene経由）"""
        enemy_system = self.encounter_manager.enemy_system

        group_data = {
            "group_id": f"boss_{enemy_type}",
            "name": f"Boss: {enemy_type}",
            "difficulty": 3,
            "base_rewards": {
                "exp": level * 40,
                "gold": level * 25,
            },
            "drops": [],
            "enemies": [
                {
                    "enemy_type": enemy_type,
                    "min_count": count,
                    "max_count": count,
                    "level_modifier": 0,
                }
            ],
            "formation": {"positions": [], "sprite_scale": []},
        }

        party = getattr(self.game, "party", None)
        party_level = 1
        if party:
            party_level = max(1, max(m.get("level", 1) for m in party))

        enemy_group = EnemyGroup(group_data, enemy_system, party_level=level)
        rewards_data = self.encounter_manager.build_encounter_rewards(enemy_group)

        # バトルシーンを設定してpush_scene
        battle_scene = self.game.scenes.get("battle")
        if battle_scene:
            battle_scene.start_battle_with_group(enemy_group, rewards_data)
            self.game._battle_from_script = True
            self.audio_manager.play_se("se_encounter")
            self.game.push_scene("battle")
        else:
            logger.warning("BattleScene not found for script battle")

    def _try_interact_gimmick(self) -> bool:
        """プレイヤーの前のギミックと対話を試みる"""
        if self.gimmick_manager is None:
            return False

        dx, dy = 0, 0
        if self.player.direction == "up": dy = -1
        elif self.player.direction == "down": dy = 1
        elif self.player.direction == "left": dx = -1
        elif self.player.direction == "right": dx = 1

        target_x = self.player.grid_x + dx
        target_y = self.player.grid_y + dy

        event = self.gimmick_manager.interact(target_x, target_y, self.player.direction)
        if event is None:
            return False

        if event.message:
            self.dialogue_renderer.show_dialogue("", event.message)
        return True

    def draw(self, screen: pygame.Surface):
        """描画処理"""
        # TMXマップを描画
        if self.tmx_surface:
            screen.blit(self.tmx_surface, (-self.camera_x, -self.camera_y))

            # NPCの描画
            self._draw_npcs(screen, offset_x=-self.camera_x, offset_y=-self.camera_y)

            # プレイヤーの描画
            self.player.draw(screen, offset_x=-self.camera_x, offset_y=-self.camera_y)

            # グリッドガイド（見やすさのため薄く表示）
            tile_w = self.tmx_data.tilewidth * self.tmx_tile_scale
            tile_h = self.tmx_data.tileheight * self.tmx_tile_scale
            start_x = self.camera_x // tile_w
            end_x = min(self.map_width_tiles, start_x + (SCREEN_WIDTH // tile_w) + 2)
            start_y = self.camera_y // tile_h
            end_y = min(self.map_height_tiles, start_y + (SCREEN_HEIGHT // tile_h) + 2)

            grid_color = (255, 255, 255, 50)
            for gx in range(start_x, end_x):
                px = gx * tile_w - self.camera_x
                pygame.draw.line(screen, grid_color, (px, 0), (px, SCREEN_HEIGHT))
            for gy in range(start_y, end_y):
                py = gy * tile_h - self.camera_y
                pygame.draw.line(screen, grid_color, (0, py), (SCREEN_WIDTH, py))
        else:
            map_id = self.current_map
            if "forest" in map_id:
                bg_color = (34, 100, 34)
            elif "cave" in map_id:
                bg_color = (60, 60, 60)
            elif "mountain" in map_id:
                bg_color = (139, 90, 43)
            elif "town" in map_id:
                bg_color = (100, 140, 100)
            else:
                bg_color = (34, 139, 34)

            screen.fill(bg_color)

            for x in range(0, SCREEN_WIDTH, TILE_SIZE):
                for y in range(0, SCREEN_HEIGHT, TILE_SIZE):
                    pygame.draw.rect(screen, (30, min(139, max(0, bg_color[1]-10)), 30), (x, y, TILE_SIZE, TILE_SIZE), 1)

            # NPCの描画（非TMXマップ）
            self._draw_npcs(screen)

            self.player.draw(screen)

        # ロケーションマーカー（ワールドマップ上）
        self._draw_location_markers(screen)

        # ダイアログUIの描画（最前面）
        self.dialogue_renderer.draw(screen)

        # 宝箱の描画
        self._draw_chests(screen, offset_x=-self.camera_x, offset_y=-self.camera_y)

        # ドアの描画（アニメーション中のドア）
        if self.door_manager is not None and self.tmx_surface:
            tile_size = self.tmx_data.tilewidth * self.tmx_tile_scale
            self.door_manager.draw(screen, self.camera_x, self.camera_y, tile_size)

        if self.fade_alpha > 0:
            self.fade_surface.fill((0, 0, 0, self.fade_alpha))
            screen.blit(self.fade_surface, (0, 0))

        # スクリプトフェード（宿屋等の演出用）
        if self._script_fade_alpha > 0:
            self._script_fade_surface.set_alpha(self._script_fade_alpha)
            screen.blit(self._script_fade_surface, (0, 0))

        # ロケーション名表示（最前面）
        self._draw_location_name(screen)

    def _redraw_tmx_surface(self):
        """タイル変更後にTMXサーフェスを再描画"""
        if self.tmx_data is None:
            return
        tw = self.tmx_data.tilewidth * self.tmx_tile_scale
        th = self.tmx_data.tileheight * self.tmx_tile_scale
        self._build_tmx_surface(tw, th)

    def _begin_door_transition(self, result):
        """ドア経由のマップ遷移を開始。dest_map="_prev" で前のマップへ戻る"""
        from src.world.door_manager import DoorResult  # 循環import避けるため遅延import
        dest = result.dest_map
        dest_x = result.dest_x
        dest_y = result.dest_y

        if dest == "_prev":
            rp = self.return_points.get(self.current_map)
            if rp:
                dest = rp["map_id"]
                dest_x = rp.get("x")
                dest_y = rp.get("y")
            else:
                return  # return_pointsが未記録なら遷移しない

        self._begin_transition({
            "kind":   "map",
            "map_id": dest,
            "dest_x": dest_x,
            "dest_y": dest_y,
            "entry":  result.entry,
        })

    def _on_door_animation_complete(self, door):
        """ドアアニメーション完了コールバック。state保存とマップ遷移を発火"""
        # dv2_ フラグは DoorManager.update() で既に保存済み
        if door.dest_map:
            from src.world.door_manager import DoorResult
            result = DoorResult(
                status="opened",
                message=None,
                dest_map=door.dest_map,
                dest_x=door.dest_x,
                dest_y=door.dest_y,
                entry=door.entry,
            )
            self._begin_door_transition(result)


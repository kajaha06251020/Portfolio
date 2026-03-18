"""ドア管理 — Door Manager

DQスタイルの鍵階層システムを持つドアを管理する。
TMX マップオブジェクトから "door" タイプのオブジェクトを読み込み、
開閉状態を WorldStateManager のフラグで永続化する。

鍵の階層:
  0 = 鍵不要
  1 = とうぞくのカギ以上で開く
  2 = まほうのカギ以上で開く
  3 = さいごのカギのみ開く

フラグ名: dv2_<door_id>  (True = 開放済み)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# pygame は省略可能（テスト環境では未インストールの場合がある）
try:
    import pygame
    _PYGAME_AVAILABLE = True
except ImportError:
    pygame = None  # type: ignore[assignment]
    _PYGAME_AVAILABLE = False

# pytmx は省略可能
try:
    import pytmx
    _PYTMX_AVAILABLE = True
except ImportError:
    pytmx = None  # type: ignore[assignment]
    _PYTMX_AVAILABLE = False


# ------------------------------------------------------------------
# 鍵の階層定数
# ------------------------------------------------------------------

KEY_TIER_MAP: dict[str, int] = {
    "thieves_key": 1,
    "magic_key":   2,
    "final_key":   3,
}


# ------------------------------------------------------------------
# データクラス
# ------------------------------------------------------------------

@dataclass
class Door:
    """TMX から読み込まれた単一ドアのデータ。"""
    door_id: str
    x: int                       # グリッド座標
    y: int
    animated: bool               # door_animation プロパティ（Tiledから読む）
    key_tier: int                # 0=鍵不要, 1=とうぞくのカギ以上, 2=まほうのカギ以上, 3=さいごのカギのみ
    dest_map: Optional[str]      # "_prev" で前のマップへ戻る
    dest_x: Optional[int]
    dest_y: Optional[int]
    entry: Optional[str]
    sprite: Optional[str]        # スプライトシートファイル名（拡張子なし）
    anim_frames: int = 2
    anim_speed: float = 0.12
    # 実行時状態
    is_open: bool = False
    anim_frame: float = 0.0
    anim_playing: bool = False


@dataclass
class DoorResult:
    """try_open() の結果。MapScene が消費する。"""
    status: str                  # "opened" | "locked_no_key" | "locked_wrong_key"
    message: Optional[str]
    dest_map: Optional[str]
    dest_x: Optional[int]
    dest_y: Optional[int]
    entry: Optional[str]


# ------------------------------------------------------------------
# モジュールレベルヘルパー関数
# ------------------------------------------------------------------

def _get_player_key_tier(inventory: dict) -> int:
    """インベントリが保持している最高の鍵ティアを返す。"""
    best = 0
    for key_id, tier in KEY_TIER_MAP.items():
        if inventory.get(key_id, 0) > 0:
            best = max(best, tier)
    return best


def _can_open(door: Door, inventory: dict) -> bool:
    """このドアを現在のインベントリで開けられるか判定する。"""
    if door.key_tier == 0:
        return True
    return _get_player_key_tier(inventory) >= door.key_tier


# ------------------------------------------------------------------
# DoorManager
# ------------------------------------------------------------------

class DoorManager:
    """TMX マップから "door" オブジェクトを読み込み、開閉・描画を管理する。

    TMX オブジェクトのカスタムプロパティ:
        door_id         (str, 必須)
        door_animation  (bool, デフォルト False)
        key_tier        (int,  デフォルト 0)
        dest_map        (str)
        dest_x          (int)
        dest_y          (int)
        entry           (str)
        sprite          (str)  スプライトシートファイル名（拡張子なし）
        anim_frames     (int,  デフォルト 2)
        anim_speed      (float, デフォルト 0.12)
    """

    def __init__(self, world_state_manager) -> None:
        self.doors: dict[tuple[int, int], Door] = {}
        self.world_state = world_state_manager
        self._tmx_data = None           # load_from_tmx 時に保存
        self._sprite_cache: dict[str, Any] = {}   # sprite名 -> pygame.Surface
        self.on_door_opened: Optional[Callable[[Door], None]] = None
        self._on_tile_removed_callback: Optional[Callable[[], None]] = None

    # ------------------------------------------------------------------
    # 読み込み
    # ------------------------------------------------------------------

    def load_from_tmx(self, map_id: str, tmx_data) -> None:
        """TMX データからドアオブジェクトを抽出して初期化する。"""
        # 再ロード前にクリア
        self.doors.clear()
        self._tmx_data = tmx_data

        if tmx_data is None:
            return

        tile_width: int = tmx_data.tilewidth
        tile_height: int = tmx_data.tileheight

        for obj_group in tmx_data.objectgroups:
            for obj in obj_group:
                if getattr(obj, "type", "") != "door":
                    continue

                props: dict = (
                    obj.properties
                    if hasattr(obj, "properties") and obj.properties
                    else {}
                )

                door_id: str = props.get("door_id", "")
                if not door_id:
                    logger.warning(
                        "Door object without door_id at pixel (%.1f, %.1f)", obj.x, obj.y
                    )
                    continue

                gx = int(obj.x // tile_width)
                gy = int(obj.y // tile_height)

                # WorldStateManager のフラグで開放済みか確認
                flag_value = self.world_state.get_flag(f"dv2_{door_id}")
                already_open = flag_value is True

                sprite_name: Optional[str] = props.get("sprite")

                door = Door(
                    door_id=door_id,
                    x=gx,
                    y=gy,
                    animated=bool(props.get("door_animation", False)),
                    key_tier=int(props.get("key_tier", 0)),
                    dest_map=props.get("dest_map"),
                    dest_x=props.get("dest_x"),
                    dest_y=props.get("dest_y"),
                    entry=props.get("entry"),
                    sprite=sprite_name,
                    anim_frames=int(props.get("anim_frames", 2)),
                    anim_speed=float(props.get("anim_speed", 0.12)),
                    is_open=already_open,
                )

                # スプライト画像をキャッシュ
                if sprite_name and sprite_name not in self._sprite_cache:
                    self._load_sprite(sprite_name)

                self.doors[(gx, gy)] = door
                logger.debug(
                    "Loaded door %s at (%d, %d) key_tier=%d animated=%s open=%s",
                    door_id, gx, gy, door.key_tier, door.animated, already_open,
                )

        logger.info("Loaded %d doors for map %s", len(self.doors), map_id)

    def _load_sprite(self, sprite_name: str) -> None:
        """スプライトシート画像を assets/images/doors/ から読み込んでキャッシュする。"""
        if not _PYGAME_AVAILABLE:
            return
        from pathlib import Path
        sprite_path = (
            Path(__file__).resolve().parent.parent.parent
            / "assets" / "images" / "doors" / f"{sprite_name}.png"
        )
        try:
            surface = pygame.image.load(str(sprite_path)).convert_alpha()
            self._sprite_cache[sprite_name] = surface
            logger.debug("Cached door sprite: %s", sprite_path)
        except Exception:
            logger.warning("Failed to load door sprite: %s", sprite_path, exc_info=True)

    # ------------------------------------------------------------------
    # タイルブロック判定
    # ------------------------------------------------------------------

    def is_tile_blocked(self, x: int, y: int) -> bool:
        """(x, y) に閉じているドアがあれば True を返す。"""
        door = self.doors.get((x, y))
        if door is not None and not door.is_open:
            return True
        return False

    # ------------------------------------------------------------------
    # ドアを開ける
    # ------------------------------------------------------------------

    def try_open(self, x: int, y: int, inventory: dict) -> Optional[DoorResult]:
        """(x, y) のドアを開こうとする。

        Returns
        -------
        None
            その座標にドアが存在しない。
        DoorResult
            開けた結果または失敗理由。
        """
        door = self.doors.get((x, y))
        if door is None:
            return None

        # 鍵チェック
        if not _can_open(door, inventory):
            if _get_player_key_tier(inventory) == 0:
                return DoorResult(
                    status="locked_no_key",
                    message="カギが必要だ！",
                    dest_map=None,
                    dest_x=None,
                    dest_y=None,
                    entry=None,
                )
            else:
                return DoorResult(
                    status="locked_wrong_key",
                    message="持っているカギでは開かなかった！",
                    dest_map=None,
                    dest_x=None,
                    dest_y=None,
                    entry=None,
                )

        # 開けられる場合の処理
        if door.animated:
            # アニメーション付き — update() でフレームを進め、完了時に開放する
            door.anim_playing = True
        else:
            # 即座に開放
            door.is_open = True
            self.world_state.set_flag(f"dv2_{door.door_id}", True)
            self._remove_tile_door(door)

        logger.info(
            "Door %s opened at (%d, %d) animated=%s", door.door_id, door.x, door.y, door.animated
        )
        return DoorResult(
            status="opened",
            message=None,
            dest_map=door.dest_map,
            dest_x=door.dest_x,
            dest_y=door.dest_y,
            entry=door.entry,
        )

    # ------------------------------------------------------------------
    # タイルの消去
    # ------------------------------------------------------------------

    def _remove_tile_door(self, door: Door) -> None:
        """TMX の "Doors" レイヤーからドアタイルを消去する。

        MapScene 側が `_on_tile_removed_callback` に再描画関数を登録しておくと
        タイルが消えた後に画面が更新される。
        """
        if self._tmx_data is None:
            return

        if not _PYTMX_AVAILABLE:
            logger.debug("pytmx not available; skipping tile removal for door %s", door.door_id)
            return

        for layer in self._tmx_data.layers:
            if getattr(layer, "name", "") != "Doors":
                continue
            # TiledTileLayer のみ対象
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue
            try:
                layer.data[door.y][door.x] = 0
                logger.debug("Removed tile at (%d, %d) from Doors layer", door.x, door.y)
            except (IndexError, TypeError) as exc:
                logger.warning(
                    "Could not remove door tile at (%d, %d): %s", door.x, door.y, exc
                )
            break

        if self._on_tile_removed_callback is not None:
            try:
                self._on_tile_removed_callback()
            except Exception:
                logger.warning("on_tile_removed_callback raised an exception", exc_info=True)

    # ------------------------------------------------------------------
    # 更新（アニメーション）
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """アニメーション中のドアのフレームを進める。

        Parameters
        ----------
        dt : float
            前フレームからの経過秒数。
        """
        for door in self.doors.values():
            if not door.anim_playing:
                continue

            door.anim_frame += dt / door.anim_speed

            if door.anim_frame >= door.anim_frames:
                # アニメーション完了
                door.anim_frame = float(door.anim_frames - 1)
                door.anim_playing = False
                door.is_open = True
                self.world_state.set_flag(f"dv2_{door.door_id}", True)
                logger.info("Door %s animation complete; now open", door.door_id)
                if self.on_door_opened is not None:
                    try:
                        self.on_door_opened(door)
                    except Exception:
                        logger.warning("on_door_opened callback raised an exception", exc_info=True)

    # ------------------------------------------------------------------
    # 描画
    # ------------------------------------------------------------------

    def draw(self, surface, cam_x: int, cam_y: int, tile_size: int) -> None:
        """アニメーション再生中のドアを描画する。

        Parameters
        ----------
        surface
            描画先の pygame.Surface。
        cam_x, cam_y : int
            カメラのタイル単位オフセット。
        tile_size : int
            1 タイルのピクセルサイズ。
        """
        if not _PYGAME_AVAILABLE:
            return

        for door in self.doors.values():
            if not (door.animated and door.anim_playing):
                continue

            frame_idx = int(door.anim_frame)
            # スクリーン座標
            screen_x = (door.x - cam_x) * tile_size
            screen_y = (door.y - cam_y) * tile_size
            dest_rect = pygame.Rect(screen_x, screen_y, tile_size, tile_size)

            sprite_surface = self._sprite_cache.get(door.sprite) if door.sprite else None

            if sprite_surface is not None:
                # フレームをスライスして描画
                frame_w = sprite_surface.get_width() // door.anim_frames
                frame_h = sprite_surface.get_height()
                src_rect = pygame.Rect(frame_idx * frame_w, 0, frame_w, frame_h)
                frame_surf = sprite_surface.subsurface(src_rect)
                scaled = pygame.transform.scale(frame_surf, (tile_size, tile_size))
                surface.blit(scaled, dest_rect)
            else:
                # スプライトなし: 赤色の半透明矩形をプレースホルダとして描画
                placeholder = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
                alpha = max(0, 180 - frame_idx * (180 // max(door.anim_frames, 1)))
                placeholder.fill((220, 50, 50, alpha))
                surface.blit(placeholder, dest_rect)

    # ------------------------------------------------------------------
    # ユーティリティ
    # ------------------------------------------------------------------

    def is_animating(self) -> bool:
        """いずれかのドアがアニメーション再生中なら True を返す。"""
        return any(door.anim_playing for door in self.doors.values())

    def get_door_at(self, x: int, y: int) -> Optional[Door]:
        """グリッド座標 (x, y) のドアを返す。なければ None。"""
        return self.doors.get((x, y))

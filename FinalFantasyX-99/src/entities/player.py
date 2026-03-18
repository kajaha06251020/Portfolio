"""
プレイヤークラス
"""

import pygame
from src.constants import (
    TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT,
    PLAYER_INITIAL_HP, PLAYER_INITIAL_MP,
    PLAYER_INITIAL_ATTACK, PLAYER_INITIAL_DEFENSE, PLAYER_INITIAL_SPEED,
    PLAYER_MOVE_SPEED, PLAYER_RENDER_MARGIN, scaled
)


class Player:
    """プレイヤーキャラクター"""
    
    def __init__(self, x: int, y: int):
        self.x = float(x)
        self.y = float(y)
        self.speed = PLAYER_MOVE_SPEED
        self.width = TILE_SIZE - PLAYER_RENDER_MARGIN
        self.height = TILE_SIZE - PLAYER_RENDER_MARGIN

        # グリッド移動
        self.tile_size = TILE_SIZE
        self.grid_x = int(self.x // self.tile_size)
        self.grid_y = int(self.y // self.tile_size)
        self.target_grid_x = self.grid_x
        self.target_grid_y = self.grid_y
        self._move_start_x = self.x
        self._move_start_y = self.y
        self._move_target_x = self.x
        self._move_target_y = self.y
        self._move_progress = 0
        self._move_frames = 8
        self.is_grid_moving = False
        
        # ステータス
        self.max_hp = PLAYER_INITIAL_HP
        self.hp = self.max_hp
        self.max_mp = PLAYER_INITIAL_MP
        self.mp = self.max_mp
        self.attack = PLAYER_INITIAL_ATTACK
        self.defense = PLAYER_INITIAL_DEFENSE
        self.speed_stat = PLAYER_INITIAL_SPEED
        
        # 経験値・レベル
        self.level = 1
        self.exp = 0
        self.exp_to_next_level = 100
        
        # アニメーション
        self.direction = "down"  # up, down, left, right
        self.animation_frame = 0
        self.animation_speed = 8  # フレーム間隔
        self.is_moving = False  # 移動状態フラグ
        self.move_queue = []  # 移動キュー

    def set_grid_position(self, grid_x: int, grid_y: int):
        """グリッド座標を直接設定"""
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.target_grid_x = grid_x
        self.target_grid_y = grid_y
        self.x = float(grid_x * self.tile_size)
        self.y = float(grid_y * self.tile_size)
        self._move_start_x = self.x
        self._move_start_y = self.y
        self._move_target_x = self.x
        self._move_target_y = self.y
        self._move_progress = 0
        self.is_grid_moving = False
        self.is_moving = False

    def try_move_grid(self, dx: int, dy: int, max_cols: int, max_rows: int, blocked_checker=None) -> bool:
        """1マス単位で移動開始。移動開始できた場合はTrue。"""
        if dx < 0:
            self.direction = "left"
        elif dx > 0:
            self.direction = "right"
        elif dy < 0:
            self.direction = "up"
        elif dy > 0:
            self.direction = "down"

        if self.is_grid_moving:
            return False

        next_x = self.grid_x + dx
        next_y = self.grid_y + dy

        if next_x < 0 or next_x >= max_cols:
            return False
        if next_y < 0 or next_y >= max_rows:
            return False
        if blocked_checker and blocked_checker(next_x, next_y, self.direction):
            return False

        self.target_grid_x = next_x
        self.target_grid_y = next_y
        self._move_start_x = self.x
        self._move_start_y = self.y
        self._move_target_x = float(next_x * self.tile_size)
        self._move_target_y = float(next_y * self.tile_size)
        self._move_progress = 0
        self.is_grid_moving = True
        self.is_moving = True
        return True
    
    def move(self, dx: int, dy: int):
        """プレイヤーを移動"""
        if self.try_move_grid(dx, dy, int(SCREEN_WIDTH // self.tile_size), int(SCREEN_HEIGHT // self.tile_size)):
            return

        new_x = self.x + dx * self.speed
        new_y = self.y + dy * self.speed
        
        # 画面外に出ないように制限
        if 0 <= new_x <= SCREEN_WIDTH - self.width:
            self.x = new_x
        else:
            return
        
        if 0 <= new_y <= SCREEN_HEIGHT - self.height:
            self.y = new_y
        else:
            return
        
        # 向きを更新
        if dx < 0:
            self.direction = "left"
        elif dx > 0:
            self.direction = "right"
        if dy < 0:
            self.direction = "up"
        elif dy > 0:
            self.direction = "down"
        
        # 移動フラグを設定
        self.is_moving = True
    
    def update(self):
        """更新処理"""
        # アニメーションフレームを更新
        self.animation_frame = (self.animation_frame + 1) % (60)

        # 1マス移動の補間更新（タイル移動完了時にTrueを返す）
        if self.is_grid_moving:
            self._move_progress += 1
            ratio = min(1.0, self._move_progress / self._move_frames)
            self.x = self._move_start_x + (self._move_target_x - self._move_start_x) * ratio
            self.y = self._move_start_y + (self._move_target_y - self._move_start_y) * ratio

            if ratio >= 1.0:
                self.x = self._move_target_x
                self.y = self._move_target_y
                self.grid_x = self.target_grid_x
                self.grid_y = self.target_grid_y
                self.is_grid_moving = False
                self.is_moving = False
                return True

            return False
        
        # 移動状態をリセット
        if self.animation_frame % (self.animation_speed * 2) == 0:
            self.is_moving = False

        return False
    
    def get_animation_frame(self) -> int:
        """
        現在のアニメーションフレームを取得
        
        Returns:
            int: フレーム (0-3)
        """
        if not self.is_moving:
            return 0
        return (self.animation_frame // self.animation_speed) % 4
    
    def draw(self, screen: pygame.Surface, offset_x: int = 0, offset_y: int = 0):
        """描画処理"""
        draw_x = int(self.x + offset_x)
        draw_y = int(self.y + offset_y)

        # 簡易的なプレイヤー表示（四角形）
        color = (0, 100, 255)  # 青色
        pygame.draw.rect(screen, color, (draw_x, draw_y, self.width, self.height))
        
        # 向きを示す三角形
        if self.direction == "up":
            points = [(draw_x + self.width // 2, draw_y),
                      (draw_x, draw_y + scaled(10)),
                      (draw_x + self.width, draw_y + scaled(10))]
        elif self.direction == "down":
            points = [(draw_x + self.width // 2, draw_y + self.height),
                      (draw_x, draw_y + self.height - scaled(10)),
                      (draw_x + self.width, draw_y + self.height - scaled(10))]
        elif self.direction == "left":
            points = [(draw_x, draw_y + self.height // 2),
                      (draw_x + scaled(10), draw_y),
                      (draw_x + scaled(10), draw_y + self.height)]
        else:  # right
            points = [(draw_x + self.width, draw_y + self.height // 2),
                      (draw_x + self.width - scaled(10), draw_y),
                      (draw_x + self.width - scaled(10), draw_y + self.height)]
        
        pygame.draw.polygon(screen, (255, 255, 255), points)
    
    def gain_exp(self, amount: int):
        """経験値を獲得"""
        self.exp += amount
        while self.exp >= self.exp_to_next_level:
            self.level_up()
    
    def level_up(self):
        """レベルアップ"""
        self.level += 1
        self.exp -= self.exp_to_next_level
        self.exp_to_next_level = int(self.exp_to_next_level * 1.5)
        
        # ステータス上昇
        self.max_hp += 10
        self.hp = self.max_hp
        self.max_mp += 5
        self.mp = self.max_mp
        self.attack += 3
        self.defense += 2

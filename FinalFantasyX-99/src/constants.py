"""
ゲームの定数
"""

from pathlib import Path


UI_SCALE = 1.5

# 画面設定
BASE_SCREEN_WIDTH = 800
BASE_SCREEN_HEIGHT = 600
SCREEN_WIDTH = int(BASE_SCREEN_WIDTH * UI_SCALE)
SCREEN_HEIGHT = int(BASE_SCREEN_HEIGHT * UI_SCALE)
FPS = 60
GAME_TITLE = "Final Fantasy X-99"

# タイルサイズ
TILE_SIZE = int(32 * UI_SCALE)

# 色の定義
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

# フォントサイズ
FONT_SIZE_SMALL = int(16 * UI_SCALE)
FONT_SIZE_MEDIUM = int(24 * UI_SCALE)
FONT_SIZE_LARGE = int(32 * UI_SCALE)

# フォントファイル
FONT_PATH = str(Path(__file__).resolve().parent.parent / "assets" / "fonts" / "DotGothic16-Regular.ttf")

# 描画サイズ
PLAYER_RENDER_MARGIN = int(4 * UI_SCALE)
PLAYER_MOVE_SPEED = int(4 * UI_SCALE)


def scaled(value: int) -> int:
	return int(value * UI_SCALE)

# プレイヤー初期ステータス
PLAYER_INITIAL_HP = 100
PLAYER_INITIAL_MP = 50
PLAYER_INITIAL_ATTACK = 10
PLAYER_INITIAL_DEFENSE = 5
PLAYER_INITIAL_SPEED = 5

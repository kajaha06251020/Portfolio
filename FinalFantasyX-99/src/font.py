"""
フォントユーティリティ
"""

import pygame
from src.constants import FONT_PATH


def get_font(size: int) -> pygame.font.Font:
    """共通日本語フォントを取得"""
    return pygame.font.Font(FONT_PATH, size)

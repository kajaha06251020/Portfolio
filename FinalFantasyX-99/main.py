"""
Final Fantasy X-99 - JRPG Game
PyGameで作成したJRPGゲーム
"""

import pygame
from src.game import Game


def main():
    """ゲームのエントリーポイント"""
    pygame.init()
    
    game = Game()
    game.run()
    
    pygame.quit()


if __name__ == "__main__":
    main()

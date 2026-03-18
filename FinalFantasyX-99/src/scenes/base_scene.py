"""
シーンの基底クラス
"""

from abc import ABC, abstractmethod
import pygame


class BaseScene(ABC):
    """シーンの基底クラス"""
    
    def __init__(self, game):
        self.game = game
    
    def on_enter(self):
        """シーンに入った時に呼ばれる"""
        pass
    
    def on_exit(self):
        """シーンから出る時に呼ばれる"""
        pass
    
    @abstractmethod
    def handle_events(self, events: list):
        """イベント処理"""
        pass
    
    @abstractmethod
    def update(self):
        """更新処理"""
        pass
    
    @abstractmethod
    def draw(self, screen: pygame.Surface):
        """描画処理"""
        pass

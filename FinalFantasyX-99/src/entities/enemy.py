"""
敵キャラクタークラス
"""

import random


class Enemy:
    """敵キャラクター"""
    
    # 敵のテンプレート
    ENEMY_TYPES = [
        {"name": "スライム", "hp": 30, "attack": 5, "defense": 2, "exp": 10, "color": (0, 200, 100)},
        {"name": "ゴブリン", "hp": 50, "attack": 8, "defense": 3, "exp": 20, "color": (100, 150, 50)},
        {"name": "オオカミ", "hp": 40, "attack": 10, "defense": 2, "exp": 15, "color": (100, 100, 100)},
        {"name": "スケルトン", "hp": 60, "attack": 12, "defense": 5, "exp": 30, "color": (200, 200, 200)},
        {"name": "オーク", "hp": 80, "attack": 15, "defense": 8, "exp": 50, "color": (50, 100, 50)},
    ]
    
    def __init__(self, name: str, hp: int, attack: int, defense: int, exp: int, color: tuple):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.attack = attack
        self.defense = defense
        self.exp_reward = exp
        self.color = color
    
    @classmethod
    def create_random_enemy(cls) -> "Enemy":
        """ランダムな敵を生成"""
        enemy_data = random.choice(cls.ENEMY_TYPES)
        return cls(
            name=enemy_data["name"],
            hp=enemy_data["hp"],
            attack=enemy_data["attack"],
            defense=enemy_data["defense"],
            exp=enemy_data["exp"],
            color=enemy_data["color"]
        )
    
    def take_damage(self, damage: int) -> int:
        """ダメージを受ける"""
        actual_damage = max(1, damage - self.defense)
        self.hp -= actual_damage
        return actual_damage
    
    def is_alive(self) -> bool:
        """生存判定"""
        return self.hp > 0

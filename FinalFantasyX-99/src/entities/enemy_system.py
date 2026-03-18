import json
import os
import random
from pathlib import Path


class Enemy:
    """敵キャラクタークラス"""
    
    def __init__(self, enemy_type_data, level=None):
        """
        敵オブジェクトを初期化
        
        Args:
            enemy_type_data (dict): 敵タイプの定義データ
            level (int): 敵のレベル (Noneの場合はbase_levelを使用)
        """
        self.name = enemy_type_data.get("name", "Unknown")
        self.description = enemy_type_data.get("description", "")
        self.icon = enemy_type_data.get("icon", "")
        self.color = enemy_type_data.get("color", [128, 128, 128])
        
        # レベルの設定
        if level is None:
            self.level = enemy_type_data.get("base_level", 1)
        else:
            self.level = level
        
        # 基本ステータス（レベルで調整）
        base_hp = enemy_type_data.get("base_hp", 10)
        base_mp = enemy_type_data.get("base_mp", 0)
        base_attack = enemy_type_data.get("base_attack", 5)
        base_defense = enemy_type_data.get("base_defense", 2)
        base_speed = enemy_type_data.get("base_speed", 1.0)
        base_level = enemy_type_data.get("base_level", 1)
        
        # レベルに応じた成長 (1.1倍/レベル)
        level_factor = 1.0 + (self.level - base_level) * 0.08
        
        self.max_hp = max(1, int(base_hp * level_factor))
        self.hp = self.max_hp
        self.max_mp = max(0, int(base_mp * level_factor))
        self.mp = self.max_mp
        self.attack = max(1, int(base_attack * level_factor))
        self.defense = max(0, int(base_defense * level_factor))
        self.speed = base_speed
        
        # アビリティとドロップ
        self.abilities = enemy_type_data.get("abilities", ["attack"])
        self.drops = enemy_type_data.get("drops", [])
        
        # ステータス異常管理用
        self.status_effects = {}
        
        # 元のデータ参照（敵タイプID等が必要な場合）
        self.raw_data = enemy_type_data
    
    def apply_damage(self, damage):
        """ダメージを適用"""
        self.hp = max(0, self.hp - damage)
    
    def heal(self, amount):
        """回復"""
        self.hp = min(self.max_hp, self.hp + amount)
    
    def restore_mp(self, amount):
        """MP回復"""
        self.mp = min(self.max_mp, self.mp + amount)
    
    def is_alive(self):
        """生きているかチェック"""
        return self.hp > 0
    
    def add_status_effect(self, effect_name):
        """ステータス異常を付与"""
        if effect_name not in self.status_effects:
            self.status_effects[effect_name] = 0
        self.status_effects[effect_name] = max(1, self.status_effects[effect_name])
    
    def remove_status_effect(self, effect_name):
        """ステータス異常を除去"""
        if effect_name in self.status_effects:
            del self.status_effects[effect_name]
    
    def has_status_effect(self, effect_name):
        """特定のステータス異常を持っているか"""
        return effect_name in self.status_effects and self.status_effects[effect_name] > 0
    
    def to_dict(self):
        """辞書形式でダンプ"""
        return {
            "name": self.name,
            "level": self.level,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "mp": self.mp,
            "max_mp": self.max_mp,
            "attack": self.attack,
            "defense": self.defense,
            "speed": self.speed,
            "abilities": self.abilities,
            "status_effects": self.status_effects
        }


class EnemyGroup:
    """敵グループクラス"""
    
    def __init__(self, group_data, enemy_system, party_level=1):
        """
        敵グループを初期化
        
        Args:
            group_data (dict): 敵グループの定義データ
            enemy_system (EnemySystem): 敵システムへの参照
            party_level (int): パーティのレベル（敵レベル調整用）
        """
        self.group_id = group_data.get("group_id", "unknown")
        self.name = group_data.get("name", "Unknown Group")
        self.difficulty = group_data.get("difficulty", 1)
        self.base_rewards = group_data.get("base_rewards", {"exp": 0, "gold": 0})
        self.drops = group_data.get("drops", [])
        self.formation = group_data.get("formation", {"positions": [], "sprite_scale": []})
        self.enemy_ai = group_data.get("enemy_ai", "default")
        
        # 敵メンバーを生成
        self.enemies = []
        enemies_config = group_data.get("enemies", [])
        
        for enemy_config in enemies_config:
            enemy_type = enemy_config.get("enemy_type", "slime")
            min_count = enemy_config.get("min_count", 1)
            max_count = enemy_config.get("max_count", 1)
            level_modifier = enemy_config.get("level_modifier", 0)
            
            # ランダムな敵数を決定
            count = random.randint(min_count, max_count)
            
            # 敵レベルの計算
            # パーティレベル + level_modifier ± ランダム（±20%まで）
            base_enemy_level = party_level + level_modifier
            level_variance = int(base_enemy_level * 0.2)
            
            for _ in range(count):
                enemy_level = base_enemy_level + random.randint(-level_variance, level_variance)
                enemy_level = max(1, enemy_level)  # 最小レベルは1
                
                enemy_data = enemy_system.get_enemy_type(enemy_type)
                if enemy_data:
                    enemy = Enemy(enemy_data, level=enemy_level)
                    self.enemies.append(enemy)
    
    def get_alive_enemies(self):
        """生きている敵のリストを取得"""
        return [e for e in self.enemies if e.is_alive()]
    
    def total_exp_reward(self):
        """敵グループ全体の経験値報酬を計算"""
        base_exp = self.base_rewards.get("exp", 0)
        # 難度に応じた調整
        return int(base_exp * (1.0 + (self.difficulty - 1) * 0.2))
    
    def total_gold_reward(self):
        """敵グループ全体のゴール報酬を計算"""
        base_gold = self.base_rewards.get("gold", 0)
        # ドロップ完全成功時のゴール加算
        return int(base_gold * (1.0 + (self.difficulty - 1) * 0.15))
    
    def to_dict(self):
        """辞書形式でダンプ"""
        return {
            "group_id": self.group_id,
            "name": self.name,
            "difficulty": self.difficulty,
            "enemies": [e.to_dict() for e in self.enemies],
            "alive_count": len(self.get_alive_enemies()),
            "exp_reward": self.total_exp_reward(),
            "gold_reward": self.total_gold_reward(),
            "drops": self.drops,
        }


class EnemySystem:
    """敵システム全体を管理するクラス"""
    
    def __init__(self):
        """敵システムを初期化"""
        self.enemies_data = {}
        self.encounter_groups_data = {}
        self.maps_data = {}
        self._data_dir = Path(__file__).resolve().parents[2] / "data"
        
        # JSONデータを読み込み
        self._load_enemy_data()
        self._load_encounter_groups()
        self._load_maps()
    
    def _load_enemy_data(self):
        """敵オブジェクトをロード"""
        enemy_file = self._data_dir / "enemies.json"
        if enemy_file.exists():
            with open(enemy_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.enemies_data = data.get("enemies", {})
    
    def _load_encounter_groups(self):
        """敵グループをロード"""
        groups_file = self._data_dir / "encounter_groups.json"
        if groups_file.exists():
            with open(groups_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.encounter_groups_data = data.get("encounter_groups", {})
    
    def _load_maps(self):
        """マップデータをロード"""
        maps_file = self._data_dir / "maps.json"
        if maps_file.exists():
            with open(maps_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.maps_data = {m["map_id"]: m for m in data.get("maps", [])}
    
    def get_enemy_type(self, enemy_type_id):
        """敵タイプの定義を取得"""
        return self.enemies_data.get(enemy_type_id)
    
    def create_enemy(self, enemy_type_id, level=None):
        """敵オブジェクトを作成"""
        enemy_data = self.get_enemy_type(enemy_type_id)
        if enemy_data:
            return Enemy(enemy_data, level=level)
        return None
    
    def get_encounter_group(self, group_id):
        """敵グループの定義を取得"""
        return self.encounter_groups_data.get(group_id)
    
    def create_encounter_group(self, group_id, party_level=1):
        """敵グループを生成"""
        group_data = self.get_encounter_group(group_id)
        if group_data:
            return EnemyGroup(group_data, self, party_level=party_level)
        return None
    
    def get_map(self, map_id):
        """マップデータを取得"""
        return self.maps_data.get(map_id)
    
    def get_encounter_zones_for_map(self, map_id):
        """特定のマップのエンカウントゾーンを取得"""
        map_data = self.get_map(map_id)
        if map_data:
            return map_data.get("encounter_zones", [])
        return []
    
    def select_random_encounter(self, map_id, party_level=1, zone_id=None):
        """マップ内でランダムなエンカウント敵グループを選択"""
        zones = self.get_encounter_zones_for_map(map_id)
        if not zones:
            return None

        if zone_id:
            zones = [zone for zone in zones if zone.get("zone_id") == zone_id]
            if not zones:
                return None
        
        # ランダムにゾーンを選択
        zone = random.choice(zones)
        enemy_groups = zone.get("enemy_groups", [])
        
        if not enemy_groups:
            return None
        
        # ランダムに敵グループを選択
        group_id = random.choice(enemy_groups)
        return self.create_encounter_group(group_id, party_level=party_level)


def check_encounter(encounter_rate):
    """
    エンカウント判定
    
    Args:
        encounter_rate (int): エンカウント率 (0-100)
    
    Returns:
        bool: エンカウントするかどうか
    """
    return random.randint(0, 100) < encounter_rate


def calculate_party_average_level(party):
    """
    パーティの平均レベルを計算
    
    Args:
        party (list): パーティメンバーのリスト
    
    Returns:
        int: 平均レベル（四捨五入）
    """
    if not party:
        return 1
    total_level = sum(member.get("level", 1) for member in party)
    return round(total_level / len(party))

import random
from pathlib import Path
import json
from src.entities.enemy_system import EnemySystem, check_encounter, calculate_party_average_level


class EncounterManager:
    """エンカウント処理を管理するクラス"""
    
    def __init__(self):
        """エンカウント管理を初期化"""
        self.enemy_system = EnemySystem()
        self.current_map = None
        self.current_zone = None
        self.last_encounter_group = None
        self._item_name_cache = None
    
    def set_current_location(self, map_id, zone_id=None):
        """
        現在の位置を更新
        
        Args:
            map_id (str): マップID
            zone_id (str): ゾーンID（オプション）
        """
        self.current_map = map_id
        self.current_zone = zone_id

    def _point_in_zone(self, x, y, zone):
        """座標がゾーン内かを判定"""
        zone_x = zone.get("x", 0)
        zone_y = zone.get("y", 0)
        zone_width = zone.get("width", 0)
        zone_height = zone.get("height", 0)
        return zone_x <= x < zone_x + zone_width and zone_y <= y < zone_y + zone_height

    def get_encounter_zone_at_position(self, map_id, x, y):
        """
        指定マップ座標に対応するエンカウントゾーンIDを取得

        Args:
            map_id (str): マップID
            x (int): タイルX座標
            y (int): タイルY座標

        Returns:
            str or None: ゾーンID
        """
        map_data = self.enemy_system.get_map(map_id)
        if not map_data:
            return None

        for zone in map_data.get("encounter_zones", []):
            if self._point_in_zone(x, y, zone):
                return zone.get("zone_id")
        return None

    def update_location_by_position(self, map_id, x, y):
        """
        座標から現在位置（マップ/ゾーン）を更新

        Args:
            map_id (str): マップID
            x (int): タイルX座標
            y (int): タイルY座標

        Returns:
            str or None: 判定されたゾーンID
        """
        zone_id = self.get_encounter_zone_at_position(map_id, x, y)
        self.set_current_location(map_id, zone_id)
        return zone_id
    
    def check_encounter_trigger(self, party):
        """
        エンカウント判定を実行
        
        Args:
            party (list): パーティメンバーのリスト
        
        Returns:
            bool: エンカウントするかどうか
        """
        if not self.current_map:
            return False
        
        map_data = self.enemy_system.get_map(self.current_map)
        if not map_data:
            return False
        
        # マップ全体のエンカウント率
        map_encounter_rate = map_data.get("encounter_rate", 0)
        
        # 特定ゾーンのエンカウント率を優先
        if self.current_zone:
            zones = map_data.get("encounter_zones", [])
            for zone in zones:
                if zone.get("zone_id") == self.current_zone:
                    zone_encounter_rate = zone.get("encounter_rate", map_encounter_rate)
                    # ランダムエンカウント判定
                    return check_encounter(zone_encounter_rate)
        
        # ゾーン指定がない場合は、マップの基本エンカウント率を使用
        return check_encounter(map_encounter_rate)
    
    def generate_encounter(self, party):
        """
        エンカウント敵グループを生成
        
        Args:
            party (list): パーティメンバーのリスト
        
        Returns:
            EnemyGroup or None: 敵グループ、またはエンカウント失敗時はNone
        """
        if not self.current_map:
            return None
        
        # パーティの平均レベルを計算
        party_avg_level = calculate_party_average_level(party)
        
        # 敵グループを生成
        encounter_group = self.enemy_system.select_random_encounter(
            self.current_map,
            party_level=party_avg_level,
            zone_id=self.current_zone,
        )
        
        if encounter_group:
            self.last_encounter_group = encounter_group
            return encounter_group
        
        return None
    
    def trigger_encounter(self, party):
        """
        エンカウント判定から敵グループ生成までの一連の処理
        
        Args:
            party (list): パーティメンバーのリスト
        
        Returns:
            EnemyGroup or None: 敵グループ、またはエンカウント成功しない場合はNone
        """
        if self.check_encounter_trigger(party):
            return self.generate_encounter(party)
        return None

    def trigger_encounter_at_position(self, party, map_id, x, y):
        """
        座標ベースで現在地更新後、エンカウント判定を実行

        Args:
            party (list): パーティメンバー
            map_id (str): マップID
            x (int): タイルX座標
            y (int): タイルY座標

        Returns:
            EnemyGroup or None: 生成された敵グループ
        """
        self.update_location_by_position(map_id, x, y)
        return self.trigger_encounter(party)
    
    def get_available_zones_for_map(self, map_id):
        """
        マップ内の利用可能なゾーンを取得
        
        Args:
            map_id (str): マップID
        
        Returns:
            list: ゾーン情報のリスト
        """
        map_data = self.enemy_system.get_map(map_id)
        if map_data:
            return map_data.get("encounter_zones", [])
        return []
    
    def enter_map(self, map_id):
        """
        マップに入場
        
        Args:
            map_id (str): マップID
        
        Returns:
            dict or None: マップデータ
        """
        map_data = self.enemy_system.get_map(map_id)
        if map_data:
            self.current_map = map_id
            self.current_zone = None
            return map_data
        return None
    
    def get_current_map_info(self):
        """
        現在のマップ情報を取得
        
        Returns:
            dict: マップ情報
        """
        if self.current_map:
            return self.enemy_system.get_map(self.current_map)
        return None
    
    def get_last_battle_rewards(self):
        """
        直前の戦闘の報酬を計算
        
        Returns:
            dict: report酬情報 (exp, gold)
        """
        if self.last_encounter_group:
            return {
                "exp": self.last_encounter_group.total_exp_reward(),
                "gold": self.last_encounter_group.total_gold_reward()
            }
        return {"exp": 0, "gold": 0}

    def build_encounter_rewards(self, encounter_group=None):
        """
        エンカウント報酬情報を構築

        Args:
            encounter_group (EnemyGroup | None): 対象グループ。省略時は直前グループ

        Returns:
            dict: 統一報酬データ
        """
        group = encounter_group or self.last_encounter_group
        if not group:
            return {
                "exp": 0,
                "gold": 0,
                "drops": [],
                "job_points": 0,
            }

        return {
            "exp": group.total_exp_reward(),
            "gold": group.total_gold_reward(),
            "drops": group.drops,
            "job_points": max(1, group.difficulty * 2),
        }

    def _load_item_name_cache(self):
        """items.json から item_id -> name のキャッシュを作成"""
        if self._item_name_cache is not None:
            return self._item_name_cache

        self._item_name_cache = {}
        items_file = Path(__file__).resolve().parents[2] / "data" / "items.json"
        if not items_file.exists():
            return self._item_name_cache

        with open(items_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for section in ("weapons", "armor", "accessory", "consumable", "materials"):
            for item in data.get(section, []):
                item_id = item.get("item_id")
                if not item_id:
                    continue
                self._item_name_cache[item_id] = item.get("name", item_id)

        return self._item_name_cache

    def resolve_battle_rewards(self, game, rewards_data=None):
        """
        戦闘勝利時の報酬（Gold + Drops）を確定しゲーム状態へ反映

        Args:
            game: Gameインスタンス（gold, inventory を保持）
            rewards_data (dict | None): build_encounter_rewards の結果

        Returns:
            dict: 反映後の結果
        """
        rewards = rewards_data or self.build_encounter_rewards()
        total_gold = int(rewards.get("gold", 0))
        drops = rewards.get("drops", [])

        item_names = self._load_item_name_cache()
        obtained_drops = []

        for drop in drops:
            rate = int(drop.get("rate", 0))
            if random.randint(1, 100) > rate:
                continue

            item_id = drop.get("item_id")
            amount = max(1, int(drop.get("amount", 1)))
            if not item_id:
                continue

            game.inventory[item_id] = game.inventory.get(item_id, 0) + amount
            obtained_drops.append({
                "item_id": item_id,
                "item_name": item_names.get(item_id, item_id),
                "amount": amount,
            })

        game.gold += total_gold

        return {
            "gold": total_gold,
            "obtained_drops": obtained_drops,
        }

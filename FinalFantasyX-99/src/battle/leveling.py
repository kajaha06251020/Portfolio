"""
レベルアップシステムモジュール

FF5型固定テーブルを使用したレベルアップ処理を提供します。
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class LevelingSystem:
    """FF5型のレベルアップシステム管理クラス"""

    def __init__(self, level_table_path: Optional[str] = None):
        """
        レベルテーブルを初期化
        
        Args:
            level_table_path: leveling_table.jsonへのパス。省略時は自動検出
        """
        if level_table_path is None:
            level_table_path = Path(__file__).resolve().parents[2] / "data" / "leveling_table.json"
        
        with open(level_table_path, "r", encoding="utf-8") as f:
            self.table = json.load(f)
        
        self.levels = self.table["levels"]
        self.character_bonuses = self.table["character_bonuses"]
        self.enemy_exp_table = self.table["enemy_exp_table"]

    def get_level_for_exp(self, current_exp: int) -> int:
        """
        現在のEXPからレベルを取得
        
        Args:
            current_exp: 現在のEXP値
            
        Returns:
            レベル（1-99）
        """
        for i in range(len(self.levels) - 1, -1, -1):
            if current_exp >= self.levels[i]["required_exp"]:
                return self.levels[i]["level"]
        return 1

    def get_exp_for_next_level(self, current_level: int) -> int:
        """
        次のレベルに必要な総EXPを取得
        
        Args:
            current_level: 現在のレベル
            
        Returns:
            次のレベルに必要な総EXP値
        """
        if current_level >= 99:
            return self.levels[98]["required_exp"]
        
        next_level_index = min(current_level, 98)  # レベル99は最大
        return self.levels[next_level_index]["required_exp"]

    def get_growth_rates(self, level: int) -> Dict[str, float]:
        """
        指定レベルの成長率を取得
        
        Args:
            level: レベル（1-99）
            
        Returns:
            成長率を含むDictionary
        """
        if level < 1 or level > 99:
            level = max(1, min(99, level))
        return self.levels[level - 1]["growth_rates"].copy()

    def calculate_stat(
        self,
        base_stat: int,
        level: int,
        character_name: str,
        stat_type: str
    ) -> int:
        """
        キャラクターのステータス値を計算（成長ボーナス適用）
        
        Args:
            base_stat: 初期値
            level: レベル
            character_name: キャラクター名（バッツ、レナ、ガラフ）
            stat_type: ステータスタイプ（hp, mp, attack, defense, magic など）
            
        Returns:
            計算後のステータス値
        """
        growth_rates = self.get_growth_rates(level)
        growth_rate = growth_rates.get(stat_type, 0.0)
        
        # 基本の成長計算
        stat = int(base_stat * (1.0 + growth_rate * (level - 1)))
        
        # キャラクター別ボーナスを適用
        bonus_key = f"{stat_type}_bonus"
        if character_name in self.character_bonuses:
            bonus = self.character_bonuses[character_name].get(bonus_key, 1.0)
            stat = int(stat * bonus)
        
        return max(1, stat)  # 最小値1を保証

    def apply_level_up(
        self,
        actor: Dict,
        target_level: int,
        current_level: int
    ) -> Dict[str, any]:
        """
        レベルアップ時の能力値を再計算して適用
        
        Args:
            actor: キャラクターデータ（dict）
            target_level: 目標レベル
            current_level: 現在のレベル
            
        Returns:
            変化した能力値を含むDictionary
        """
        if target_level <= current_level:
            return {}
        
        character_name = actor["name"]
        stats_before = {
            "hp": actor["hp"],
            "max_hp": actor["max_hp"],
            "mp": actor["mp"],
            "max_mp": actor["max_mp"],
            "attack": actor["attack"],
            "defense": actor["defense"],
            "magic": actor.get("magic", 0),
        }
        
        # 初期値（レベル1時の値）を取得するため base_stat を使用
        # actor の初期値を記録する必要があるため、レベルアップ時に初期値を参照する
        # 現在の実装では初期値を再計算ベースにしている
        
        # 初期値を基準に新レベルでの値を計算
        # actor に level フィールドがあると仮定
        current_actor_level = actor.get("level", 1)
        
        # 基本能力値から初期値を逆算（簡易版）
        # より正確には actor に初期値を保存する必要があります
        base_hp = int(actor["max_hp"] / (1.0 + self.get_growth_rates(current_actor_level).get("hp", 0.06) * (current_actor_level - 1)))
        base_mp = int(actor["max_mp"] / (1.0 + self.get_growth_rates(current_actor_level).get("mp", 0.04) * (current_actor_level - 1)))
        base_attack = int(actor["attack"] / (1.0 + self.get_growth_rates(current_actor_level).get("attack", 0.03) * (current_actor_level - 1)))
        base_defense = int(actor["defense"] / (1.0 + self.get_growth_rates(current_actor_level).get("defense", 0.02) * (current_actor_level - 1)))
        base_magic = int(actor.get("magic", 0) / (1.0 + self.get_growth_rates(current_actor_level).get("magic", 0.03) * (current_actor_level - 1)))
        
        # 新レベルでの能力値を計算
        new_max_hp = self.calculate_stat(base_hp, target_level, character_name, "hp")
        new_max_mp = self.calculate_stat(base_mp, target_level, character_name, "mp")
        new_attack = self.calculate_stat(base_attack, target_level, character_name, "attack")
        new_defense = self.calculate_stat(base_defense, target_level, character_name, "defense")
        new_magic = self.calculate_stat(base_magic, target_level, character_name, "magic")
        
        # 現在のHP/MPを維持しつつ、最大値更新（オーバーフロー対応）
        hp_ratio = actor["hp"] / max(1, actor["max_hp"])
        mp_ratio = actor["mp"] / max(1, actor["max_mp"])
        
        actor["max_hp"] = new_max_hp
        actor["hp"] = min(new_max_hp, int(new_max_hp * hp_ratio))
        actor["max_mp"] = new_max_mp
        actor["mp"] = min(new_max_mp, int(new_max_mp * mp_ratio))
        
        actor["attack"] = new_attack
        actor["defense"] = new_defense
        actor["magic"] = new_magic
        actor["level"] = target_level
        
        # 変化量を記録
        stats_after = {
            "hp": actor["hp"],
            "max_hp": actor["max_hp"],
            "mp": actor["mp"],
            "max_mp": actor["max_mp"],
            "attack": actor["attack"],
            "defense": actor["defense"],
            "magic": actor["magic"],
        }
        
        changes = {
            "max_hp": stats_after["max_hp"] - stats_before["max_hp"],
            "max_mp": stats_after["max_mp"] - stats_before["max_mp"],
            "attack": stats_after["attack"] - stats_before["attack"],
            "defense": stats_after["defense"] - stats_before["defense"],
            "magic": stats_after["magic"] - stats_before["magic"],
        }
        
        return changes

    def gain_exp(
        self,
        actor: Dict,
        exp_amount: int
    ) -> Tuple[bool, Optional[int]]:
        """
        EXPを獲得し、レベルアップするかチェック
        
        Args:
            actor: キャラクターデータ
            exp_amount: 獲得EXP
            
        Returns:
            (レベルアップしたか, レベルアップ後のレベル)
        """
        if "current_exp" not in actor:
            actor["current_exp"] = 0
        
        current_level = actor.get("level", 1)
        old_exp = actor["current_exp"]
        actor["current_exp"] += exp_amount
        
        new_level = self.get_level_for_exp(actor["current_exp"])
        
        if new_level > current_level:
            self.apply_level_up(actor, new_level, current_level)
            return True, new_level
        
        return False, None

    def get_base_exp_from_enemies(self, enemies: List[Dict]) -> int:
        """
        敵グループから獲得できるベースEXPを計算
        
        Args:
            enemies: 敵リスト（各敵は "name" フィールドを持つ）
            
        Returns:
            合計EXP
        """
        total_exp = 0
        for enemy in enemies:
            enemy_name = enemy.get("name", "Slime")
            base_exp = self.enemy_exp_table.get(enemy_name, 10)
            total_exp += base_exp
        return total_exp


def apply_battle_rewards(
    party: List[Dict],
    enemies: List[Dict],
    leveling_system: LevelingSystem,
    total_exp_override: Optional[int] = None,
) -> Dict:
    """
    バトル終了後の報酬処理（EXP分配）
    
    Args:
        party: パーティメンバーリスト
        enemies: 倒した敵リスト
        leveling_system: LevelingSystemインスタンス
        
    Returns:
        レベルアップ情報を含むDictionary
    """
    total_base_exp = total_exp_override if total_exp_override is not None else leveling_system.get_base_exp_from_enemies(enemies)
    alive_party_count = sum(1 for member in party if member.get("alive", True))
    
    exp_per_member = total_base_exp // max(1, alive_party_count)
    
    level_ups = []
    
    for actor in party:
        if not actor.get("alive", True):
            continue
        
        leveled_up, new_level = leveling_system.gain_exp(actor, exp_per_member)
        if leveled_up:
            level_ups.append({
                "name": actor["name"],
                "new_level": new_level,
                "exp_gained": exp_per_member,
            })
    
    return {
        "total_exp_distributed": exp_per_member * max(1, alive_party_count),
        "exp_per_member": exp_per_member,
        "level_ups": level_ups,
    }

"""
状態異常システムモジュール

複数の状態異常と相互作用を管理
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


class StatusEffect:
    """状態異常定義クラス"""
    
    def __init__(self, effect_id: str, effect_data: Dict[str, Any]):
        self.effect_id = effect_id
        self.name = effect_data.get("name")
        self.description = effect_data.get("description")
        self.severity = effect_data.get("severity", 1)
        self.resistance_type = effect_data.get("resistance_type")
        self.can_stack = effect_data.get("can_stack", False)
        self.duration = effect_data.get("duration", -1)  # -1 = 無期限
        self.effect_type = effect_data.get("effect_type")
        self.is_beneficial = effect_data.get("is_beneficial", False)
        self.raw_data = effect_data


class ActiveEffect:
    """活動中の状態異常インスタンス"""
    
    def __init__(self, effect: StatusEffect, duration: int = None):
        self.effect = effect
        self.applied_turn = 0
        self.duration = duration if duration is not None else effect.duration
        self.remaining_turns = self.duration
        self.stage = 1  # 石化等の段階状態用
    
    def reduce_duration(self) -> bool:
        """
        継続時間を減らす
        
        Returns:
            効果が失効したか
        """
        if self.duration == -1:  # 無期限
            return False
        
        self.remaining_turns -= 1
        return self.remaining_turns <= 0
    
    def is_expired(self) -> bool:
        """効果が失効しているか確認"""
        if self.duration == -1:  # 無期限
            return False
        return self.remaining_turns <= 0


class StatusEffectManager:
    """状態異常管理クラス"""
    
    def __init__(self, status_path: Optional[str] = None):
        """
        状態異常データを初期化
        
        Args:
            status_path: status_effects.jsonへのパス
        """
        if status_path is None:
            status_path = Path(__file__).resolve().parents[2] / "data" / "status_effects.json"
        
        with open(status_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 状態異常定義を読み込み
        self.effects = {}
        for effect_id, effect_data in data.get("status_effects", {}).items():
            self.effects[effect_id] = StatusEffect(effect_id, effect_data)
        
        # 耐性ベース値を読み込み
        self.base_resistances = data.get("base_resistances", {})
    
    def get_effect(self, effect_id: str) -> Optional[StatusEffect]:
        """状態異常定義を取得"""
        return self.effects.get(effect_id)
    
    def apply_effect(
        self,
        actor: Dict,
        effect_id: str,
        duration: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        状態異常を適用
        
        Args:
            actor: キャラクターデータ
            effect_id: 状態異常ID
            duration: 継続ターン数（省略時は定義値）
            
        Returns:
            (適用成功したか, メッセージ)
        """
        effect = self.get_effect(effect_id)
        if not effect:
            return False, f"状態異常{effect_id}が見つかりません"
        
        # 状態異常リストの初期化
        if "status_effects" not in actor:
            actor["status_effects"] = []
        
        # 既に同じ効果があるか確認
        for active in actor["status_effects"]:
            if active.effect.effect_id == effect_id:
                if not effect.can_stack:
                    return False, f"{actor['name']}は既に{effect.name}状態です"
                # スタック可能な場合は段階を進める
                if hasattr(active, "stage"):
                    active.stage += 1
                return True, f"{actor['name']}に{effect.name}を付与！"
        
        # 抵抗判定（耐性による回避）
        if effect.resistance_type:
            resistance = self._get_resistance(actor, effect.resistance_type)
            if random.random() < resistance:
                return False, f"{actor['name']}は{effect.name}に耐性がある！"
        
        # 効果を適用
        active_effect = ActiveEffect(effect, duration)
        actor["status_effects"].append(active_effect)
        
        return True, f"{actor['name']}に{effect.name}を付与！"
    
    def remove_effect(self, actor: Dict, effect_id: str) -> bool:
        """
        状態異常を削除
        
        Args:
            actor: キャラクターデータ
            effect_id: 状態異常ID
            
        Returns:
            削除成功したか
        """
        if "status_effects" not in actor:
            return False
        
        for i, active in enumerate(actor["status_effects"]):
            if active.effect.effect_id == effect_id:
                actor["status_effects"].pop(i)
                return True
        
        return False
    
    def has_effect(self, actor: Dict, effect_id: str) -> bool:
        """状態異常を持っているか確認"""
        if "status_effects" not in actor:
            return False
        
        for active in actor["status_effects"]:
            if active.effect.effect_id == effect_id:
                return True
        
        return False
    
    def get_active_effects(self, actor: Dict) -> List[ActiveEffect]:
        """活動中の状態異常一覧を取得"""
        if "status_effects" not in actor:
            return []
        
        return [e for e in actor["status_effects"] if not e.is_expired()]
    
    def get_effect_names(self, actor: Dict) -> List[str]:
        """状態異常の名前リストを取得（UI表示用）"""
        active = self.get_active_effects(actor)
        return [e.effect.name for e in active]
    
    def on_turn_start(self, actor: Dict) -> Tuple[int, str]:
        """
        ターン開始時の処理（毒ダメージ等）
        
        Args:
            actor: キャラクターデータ
            
        Returns:
            (ダメージ量, メッセージ)
        """
        damage = 0
        message = ""
        
        if "status_effects" not in actor:
            return damage, message
        
        effects_to_remove = []
        
        for i, active in enumerate(actor["status_effects"]):
            effect = active.effect
            
            # 毒ダメージ
            if effect.effect_id == "poison":
                poison_damage = max(1, int(actor.get("max_hp", 100) * 0.05))
                damage += poison_damage
                message += f"{actor['name']}は毒状態だ！\n"
            
            # 期間満了判定
            if active.reduce_duration():
                effects_to_remove.append(i)
        
        # 期限切れの効果を削除
        for i in reversed(effects_to_remove):
            actor["status_effects"].pop(i)
        
        return damage, message.strip()
    
    def on_physical_attack(self, actor: Dict) -> None:
        """
        物理攻撃時の処理（睡眠解除等）
        
        Args:
            actor: 攻撃対象
        """
        self.remove_effect(actor, "sleep")
    
    def get_action_restrictions(self, actor: Dict) -> Dict[str, bool]:
        """
        行動制限を取得
        
        Args:
            actor: キャラクターデータ
            
        Returns:
            制限情報 {can_act, can_choose_command, can_attack, ...}
        """
        restrictions = {
            "can_act": True,
            "can_choose_command": True,
            "can_attack": True,
            "can_use_ability": True,
            "can_use_item": True,
        }
        
        if "status_effects" not in actor:
            return restrictions
        
        for active in self.get_active_effects(actor):
            effect = active.effect
            
            # ストップ：完全に行動不可
            if effect.effect_id == "stop":
                restrictions["can_act"] = False
                restrictions["can_choose_command"] = False
            
            # 睡眠、石化Lv3：行動選択不可
            elif effect.effect_id == "sleep":
                restrictions["can_choose_command"] = False
            
            elif effect.effect_id == "petrify" and active.stage >= 3:
                restrictions["can_act"] = False
                restrictions["can_choose_command"] = False
        
        return restrictions
    
    def get_atb_multiplier(self, actor: Dict) -> float:
        """
        ATB進行速度の倍率を計算
        
        Args:
            actor: キャラクターデータ
            
        Returns:
            ATB倍率
        """
        multiplier = 1.0
        
        if "status_effects" not in actor:
            return multiplier
        
        for active in self.get_active_effects(actor):
            effect = active.effect
            
            # スロウ・麻痺：50%に低下
            if effect.effect_id in ["slow", "paralysis"]:
                multiplier *= 0.5
            
            # ヘイスト：150%に上昇
            elif effect.effect_id == "haste":
                multiplier *= 1.5
        
        return multiplier
    
    def get_accuracy_multiplier(self, actor: Dict) -> float:
        """
        命中率の倍率を計算
        
        Args:
            actor: キャラクターデータ
            
        Returns:
            命中率倍率
        """
        multiplier = 1.0
        
        if "status_effects" not in actor:
            return multiplier
        
        for active in self.get_active_effects(actor):
            effect = active.effect
            
            # 暗闇：75%に低下
            if effect.effect_id == "blind":
                multiplier *= 0.75
        
        return multiplier
    
    def get_damage_reduction_rate(self, actor: Dict) -> float:
        """
        ダメージ軽減率を計算
        
        Args:
            actor: キャラクターデータ
            
        Returns:
            ダメージ軽減率（0～1）
        """
        reduction = 0.0
        
        if "status_effects" not in actor:
            return reduction
        
        for active in self.get_active_effects(actor):
            effect = active.effect
            
            # プロテス：25%軽減
            if effect.effect_id == "protect":
                reduction += effect.raw_data.get("damage_reduction_rate", 0.0)
        
        return min(0.5, reduction)  # 最大50%
    
    def _get_resistance(self, actor: Dict, resistance_type: str, item_system=None) -> float:
        """
        キャラクターの耐性値を取得

        Args:
            actor: キャラクターデータ
            resistance_type: 耐性タイプ
            item_system: ItemSystemインスタンス（装備耐性計算用）

        Returns:
            耐性値（0～1）
        """
        job_id = actor.get("current_job", "fighter")

        # ジョブ名をタイトルケースに変換（アンダースコア除去）
        job_name = job_id.replace("_", " ").title().replace(" ", "")

        # ベース耐性を取得
        base_resistance = self.base_resistances.get(job_name, {}).get(resistance_type, 0.0)

        # 装備による耐性ボーナス
        equipment_bonus = 0.0
        if item_system is not None:
            from src.battle.equipment import get_equipment_resistance_bonus
            equipment_bonus = get_equipment_resistance_bonus(actor, item_system, resistance_type)

        return min(1.0, base_resistance + equipment_bonus)


def get_random_action(actor: Dict) -> str:
    """
    混乱状態のランダム行動を決定
    
    Args:
        actor: キャラクターデータ
        
    Returns:
        行動タイプ
    """
    rand = random.randint(0, 99)
    
    if rand < 50:
        return "attack_enemy"
    elif rand < 80:
        return "attack_ally"
    else:
        return "do_nothing"

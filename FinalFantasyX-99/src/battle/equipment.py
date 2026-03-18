"""
装備・インベントリシステムモジュール

FF5型の装備管理＆インベントリメカニズムを実装
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


class Item:
    """アイテムデータクラス"""
    
    def __init__(self, item_id: str, item_type: str, item_data: Dict[str, Any]):
        self.item_id = item_id
        self.item_type = item_type  # weapon, armor, accessory, consumable
        self.name = item_data.get("name")
        self.description = item_data.get("description")
        self.price = item_data.get("price", 0)
        self.stat_bonuses = item_data.get("stat_bonuses", {})
        self.special_abilities = item_data.get("special_abilities", [])
        self.required_level = item_data.get("required_level", 1)
        self.required_job = item_data.get("required_job")
        self.raw_data = item_data
    
    def can_equip(self, actor: Dict) -> Tuple[bool, Optional[str]]:
        """
        アクターが装備できるか判定
        
        Returns:
            (装備可能か, エラーメッセージ)
        """
        if actor.get("level", 1) < self.required_level:
            return False, f"レベル{self.required_level}以上が必要です"
        
        if self.required_job and actor.get("current_job") != self.required_job:
            return False, f"ジョブ{self.required_job}でのみ装備可能です"
        
        return True, None


class Equipment:
    """装備品管理クラス"""
    
    # 装備スロット定義
    EQUIPMENT_SLOTS = {
        "weapon": "weapon",
        "head": "head",
        "body": "body",
        "accessory1": "accessory",
        "accessory2": "accessory",
    }
    
    def __init__(self):
        # {slot: item_id}
        self.equipped = {
            "weapon": None,
            "head": None,
            "body": None,
            "accessory1": None,
            "accessory2": None,
        }
    
    def equip(self, item: Item, slot: str) -> Tuple[bool, Optional[str]]:
        """
        装備品を装備
        
        Args:
            item: 装備アイテム
            slot: 装備スロット
            
        Returns:
            (成功したか, エラーメッセージ)
        """
        if slot not in self.equipped:
            return False, f"スロット{slot}は存在しません"
        
        if item.item_type == "weapon" and slot != "weapon":
            return False, "武器はweaponスロットに装備してください"
        
        if item.item_type == "armor":
            armor_slot = item.raw_data.get("slot")
            if armor_slot not in ["head", "body"]:
                return False, f"防具スロット{armor_slot}が無効です"
            if slot not in [armor_slot, "head", "body"]:
                return False, f"防具は{armor_slot}スロットに装備してください"
            # スロット名を統一
            slot = armor_slot
        
        if item.item_type == "accessory" and slot not in ["accessory1", "accessory2"]:
            return False, "アクセサリはaccessory1またはaccessory2に装備してください"
        
        # 現在の装備を保存
        old_item_id = self.equipped[slot]
        
        # 装備を変更
        self.equipped[slot] = item.item_id
        
        return True, None
    
    def unequip(self, slot: str) -> Optional[str]:
        """
        装備を外す
        
        Args:
            slot: 装備スロット
            
        Returns:
            外した装備のアイテムID
        """
        if slot not in self.equipped:
            return None
        
        old_item_id = self.equipped[slot]
        self.equipped[slot] = None
        return old_item_id
    
    def get_equipped_item_id(self, slot: str) -> Optional[str]:
        """装備スロットの装備アイテムIDを取得"""
        return self.equipped.get(slot)
    
    def get_all_equipped_items(self) -> Dict[str, Optional[str]]:
        """全装備スロットの装備リストを取得"""
        return self.equipped.copy()


class Inventory:
    """インベントリ管理クラス"""
    
    def __init__(self, item_system: 'ItemSystem', actor: Dict):
        """
        インベントリを初期化
        
        Args:
            item_system: ItemSystemインスタンス
            actor: キャラクターデータ
        """
        self.item_system = item_system
        self.actor = actor
        self.equipment = Equipment()
        
        # アイテム在庫管理 {item_id: quantity}
        self.items = {}
        
        # 初期装備を設定
        self._apply_initial_equipment()
    
    def _apply_initial_equipment(self):
        """初期装備を設定"""
        character_name = self.actor.get("name")
        
        # キャラクター別初期装備（簡易版）
        initial_equips = {
            "バッツ": {"weapon": "sword_steel", "head": "helmet_steel", "body": "armor_leather"},
            "レナ": {"weapon": "staff_magic", "head": "helmet_steel", "body": "armor_white"},
            "ガラフ": {"weapon": "axe_battle", "head": "helmet_steel", "body": "armor_plate"},
        }
        
        equips = initial_equips.get(character_name, {})
        for slot, item_id in equips.items():
            item = self.item_system.get_item(item_id)
            if item:
                self.equipment.equip(item, slot)
    
    def add_item(self, item_id: str, quantity: int = 1) -> Tuple[bool, Optional[str]]:
        """
        アイテムを追加
        
        Args:
            item_id: アイテムID
            quantity: 数量
            
        Returns:
            (成功したか, エラーメッセージ)
        """
        item = self.item_system.get_item(item_id)
        if not item:
            return False, f"アイテム{item_id}が見つかりません"
        
        if item_id not in self.items:
            self.items[item_id] = 0
        
        self.items[item_id] += quantity
        return True, None
    
    def remove_item(self, item_id: str, quantity: int = 1) -> Tuple[bool, Optional[str]]:
        """
        アイテムを削除
        
        Args:
            item_id: アイテムID
            quantity: 数量
            
        Returns:
            (成功したか, エラーメッセージ)
        """
        current = self.items.get(item_id, 0)
        
        if current < quantity:
            return False, f"{item_id}が{quantity}個足りません（現在{current}個）"
        
        self.items[item_id] -= quantity
        if self.items[item_id] <= 0:
            del self.items[item_id]
        
        return True, None
    
    def get_item_count(self, item_id: str) -> int:
        """アイテムの在庫数を取得"""
        return self.items.get(item_id, 0)
    
    def has_item(self, item_id: str, quantity: int = 1) -> bool:
        """アイテムが指定数以上あるか確認"""
        return self.get_item_count(item_id) >= quantity
    
    def calculate_stat_bonuses(self, stat_type: str) -> int:
        """
        装備による能力値補正を計算
        
        Args:
            stat_type: ステータスタイプ（attack, defense等）
            
        Returns:
            補正値
        """
        total_bonus = 0
        
        for slot, item_id in self.equipment.get_all_equipped_items().items():
            if item_id is None:
                continue
            
            item = self.item_system.get_item(item_id)
            if item:
                bonus = item.stat_bonuses.get(stat_type, 0)
                total_bonus += bonus
        
        return total_bonus
    
    def get_equipped_items(self) -> List[Item]:
        """装備中のアイテムリストを取得"""
        equipped_items = []
        
        for item_id in self.equipment.get_all_equipped_items().values():
            if item_id:
                item = self.item_system.get_item(item_id)
                if item:
                    equipped_items.append(item)
        
        return equipped_items


class ItemSystem:
    """アイテムシステム管理クラス"""
    
    def __init__(self, items_path: Optional[str] = None):
        """
        アイテムデータを初期化
        
        Args:
            items_path: items.jsonへのパス
        """
        if items_path is None:
            items_path = Path(__file__).resolve().parents[2] / "data" / "items.json"
        
        with open(items_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.items = {}
        
        # 武器を読み込み
        for weapon_data in data.get("weapons", []):
            item_id = weapon_data.get("item_id")
            self.items[item_id] = Item(item_id, "weapon", weapon_data)
        
        # 防具を読み込み
        for armor_data in data.get("armor", []):
            item_id = armor_data.get("item_id")
            self.items[item_id] = Item(item_id, "armor", armor_data)
        
        # アクセサリを読み込み
        for accessory_data in data.get("accessory", []):
            item_id = accessory_data.get("item_id")
            self.items[item_id] = Item(item_id, "accessory", accessory_data)
        
        # 消費アイテムを読み込み
        for consumable_data in data.get("consumable", []):
            item_id = consumable_data.get("item_id")
            self.items[item_id] = Item(item_id, "consumable", consumable_data)
    
    def get_item(self, item_id: str) -> Optional[Item]:
        """アイテムIDからアイテムオブジェクトを取得"""
        return self.items.get(item_id)
    
    def get_items_by_type(self, item_type: str) -> List[Item]:
        """タイプ別にアイテムを取得"""
        return [item for item in self.items.values() if item.item_type == item_type]
    
    def get_all_items(self) -> List[Item]:
        """全アイテムリストを取得"""
        return list(self.items.values())


def apply_equipment_stats(actor: Dict, inventory: Inventory) -> None:
    """
    装備によるステータス補正をアクターに適用

    基本値 x ジョブ補正 の後に呼ばれ、装備ボーナスを加算する。

    Args:
        actor: キャラクターデータ
        inventory: インベントリ
    """
    hp_ratio = actor.get("hp", 1) / max(1, actor.get("max_hp", 1))
    mp_ratio = actor.get("mp", 0) / max(1, actor.get("max_mp", 1))

    stat_to_key = {
        "attack": "attack",
        "defense": "defense",
        "magic": "magic",
        "magic_defense": "magic_defense",
        "hp": "max_hp",
        "agility": "agility",
    }

    for stat_type, actor_key in stat_to_key.items():
        bonus = inventory.calculate_stat_bonuses(stat_type)
        if bonus != 0:
            actor[f"{actor_key}_equipment_bonus"] = bonus
            current = actor.get(actor_key, 0)
            actor[actor_key] = max(0, current + bonus)

    # HP/MPの比率を維持
    if actor.get("max_hp", 0) > 0:
        actor["hp"] = max(1, min(actor["max_hp"], int(actor["max_hp"] * hp_ratio)))
    if actor.get("max_mp", 0) > 0:
        actor["mp"] = max(0, min(actor["max_mp"], int(actor["max_mp"] * mp_ratio)))


def apply_equipment_stats_from_data(actor: Dict, item_system) -> None:
    """
    actor["equipment"]辞書とItemSystemから装備ボーナスを直接計算して適用する。
    Inventoryオブジェクトを必要としない簡易版。

    Args:
        actor: キャラクターデータ（equipment フィールドを持つ）
        item_system: ItemSystemインスタンス
    """
    equipment = actor.get("equipment", {})
    if not equipment or item_system is None:
        return

    hp_ratio = actor.get("hp", 1) / max(1, actor.get("max_hp", 1))
    mp_ratio = actor.get("mp", 0) / max(1, actor.get("max_mp", 1))

    stat_to_key = {
        "attack": "attack",
        "defense": "defense",
        "magic": "magic",
        "magic_defense": "magic_defense",
        "hp": "max_hp",
        "agility": "agility",
    }

    for slot, item_id in equipment.items():
        if item_id is None:
            continue
        item = item_system.get_item(item_id)
        if item is None:
            continue
        for stat_type, actor_key in stat_to_key.items():
            bonus = item.stat_bonuses.get(stat_type, 0)
            if bonus != 0:
                current = actor.get(actor_key, 0)
                actor[actor_key] = max(0, current + bonus)

    # HP/MPの比率を維持
    if actor.get("max_hp", 0) > 0:
        actor["hp"] = max(1, min(actor["max_hp"], int(actor["max_hp"] * hp_ratio)))
    if actor.get("max_mp", 0) > 0:
        actor["mp"] = max(0, min(actor["max_mp"], int(actor["max_mp"] * mp_ratio)))


def get_equipment_resistance_bonus(actor: Dict, item_system, resistance_type: str) -> float:
    """
    装備による耐性ボーナスを計算

    Args:
        actor: キャラクターデータ
        item_system: ItemSystemインスタンス
        resistance_type: 耐性タイプ

    Returns:
        耐性ボーナス値（0～1）
    """
    equipment = actor.get("equipment", {})
    if not equipment or item_system is None:
        return 0.0

    bonus = 0.0
    for slot, item_id in equipment.items():
        if item_id is None:
            continue
        item = item_system.get_item(item_id)
        if item is None:
            continue
        # special_abilities から耐性を読み取る
        for ability in item.special_abilities:
            if isinstance(ability, str) and ability == resistance_type:
                bonus += 0.15  # 耐性アビリティ1つにつき15%
            elif isinstance(ability, dict):
                bonus += ability.get(resistance_type, 0.0)

    return min(0.5, bonus)  # 装備耐性の上限50%

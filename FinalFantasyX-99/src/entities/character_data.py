"""キャラクターデータの一元管理"""

from copy import deepcopy
from typing import Dict, Optional, Any


class CharacterDataManager:
    """パーティキャラクターデータの単一情報源"""

    # キャラクター別の速度係数とスプライト設定
    CHARACTER_BATTLE_DEFAULTS = {
        "バッツ": {"speed": 1.05, "sprite": "ally_bartz.png"},
        "レナ": {"speed": 1.2, "sprite": "ally_lenna.png"},
        "ガラフ": {"speed": 0.95, "sprite": "ally_galuf.png"},
    }

    def __init__(self):
        self._party = self._build_default_party()
        self.ensure_integrity()

    def _build_default_party(self):
        return [
            {
                "name": "バッツ",
                "level": 12,
                "current_exp": 3700,
                "job_points": 0,
                "job_mastery": 0,
                "current_job": "freelancer",
                "max_hp": 180,
                "hp": 180,
                "max_mp": 42,
                "mp": 42,
                "attack": 18,
                "defense": 9,
                "magic": 23,
                "base_max_hp": 180,
                "base_max_mp": 42,
                "base_attack": 18,
                "base_defense": 9,
                "base_magic": 23,
                "equipment": {"weapon": None, "head": None, "body": None, "accessory1": None, "accessory2": None},
            },
            {
                "name": "レナ",
                "level": 12,
                "current_exp": 3700,
                "job_points": 0,
                "job_mastery": 0,
                "current_job": "freelancer",
                "max_hp": 148,
                "hp": 148,
                "max_mp": 64,
                "mp": 64,
                "attack": 14,
                "defense": 8,
                "magic": 19,
                "base_max_hp": 148,
                "base_max_mp": 64,
                "base_attack": 14,
                "base_defense": 8,
                "base_magic": 19,
                "equipment": {"weapon": None, "head": None, "body": None, "accessory1": None, "accessory2": None},
            },
            {
                "name": "ガラフ",
                "level": 12,
                "current_exp": 3700,
                "job_points": 0,
                "job_mastery": 0,
                "current_job": "freelancer",
                "max_hp": 200,
                "hp": 200,
                "max_mp": 28,
                "mp": 28,
                "attack": 20,
                "defense": 11,
                "magic": 25,
                "base_max_hp": 200,
                "base_max_mp": 28,
                "base_attack": 20,
                "base_defense": 11,
                "base_magic": 25,
                "equipment": {"weapon": None, "head": None, "body": None, "accessory1": None, "accessory2": None},
            },
        ]

    def get_party(self):
        return self._party

    def replace_party(self, party):
        """外部更新を既存データへマージし、情報欠落を防ぐ"""
        current_by_name = {member.get("name"): member for member in self._party}
        merged_party = []

        for incoming in party:
            name = incoming.get("name")
            base = deepcopy(current_by_name.get(name, {}))
            base.update(incoming)
            self._ensure_actor_fields(base)
            merged_party.append(base)

        self._party = merged_party
        self.ensure_integrity()

    def ensure_integrity(self):
        for actor in self._party:
            self._ensure_actor_fields(actor)

    def _ensure_actor_fields(self, actor):
        actor.setdefault("level", 1)
        actor.setdefault("current_exp", 0)
        actor.setdefault("job_points", 0)
        actor.setdefault("job_mastery", 0)
        actor.setdefault("current_job", "freelancer")

        actor.setdefault("max_hp", 1)
        actor.setdefault("hp", actor["max_hp"])
        actor.setdefault("max_mp", 0)
        actor.setdefault("mp", actor["max_mp"])

        actor.setdefault("attack", 1)
        actor.setdefault("defense", 0)
        actor.setdefault("magic", 0)

        actor.setdefault("base_max_hp", actor["max_hp"])
        actor.setdefault("base_max_mp", actor["max_mp"])
        actor.setdefault("base_attack", actor["attack"])
        actor.setdefault("base_defense", actor["defense"])
        actor.setdefault("base_magic", actor["magic"])

        actor.setdefault("equipment", {"weapon": None, "head": None, "body": None, "accessory1": None, "accessory2": None})

        actor["hp"] = min(actor.get("hp", actor["max_hp"]), actor["max_hp"])
        actor["mp"] = min(actor.get("mp", actor["max_mp"]), actor["max_mp"])

    @staticmethod
    def calculate_final_stats(actor: Dict, job_system=None, item_system=None) -> Dict[str, int]:
        """
        ステータス計算パイプライン:
          base stat (from leveling table)
            x job multiplier (job.stat_bonuses)
            + equipment bonus (equipment.stat_bonuses)
            = final stat

        Args:
            actor: キャラクターデータ
            job_system: JobSystemインスタンス（省略可）
            item_system: ItemSystemインスタンス（省略可）

        Returns:
            計算後のステータス辞書
        """
        # 1) ベースステータスを取得
        base_hp = actor.get("base_max_hp", actor.get("max_hp", 1))
        base_mp = actor.get("base_max_mp", actor.get("max_mp", 0))
        base_attack = actor.get("base_attack", actor.get("attack", 1))
        base_defense = actor.get("base_defense", actor.get("defense", 0))
        base_magic = actor.get("base_magic", actor.get("magic", 0))

        # 2) ジョブ補正倍率を適用
        hp_mult = 1.0
        mp_mult = 1.0
        atk_mult = 1.0
        def_mult = 1.0
        mag_mult = 1.0

        if job_system is not None:
            job_id = actor.get("current_job")
            if job_id:
                job = job_system.get_job(job_id)
                if job:
                    hp_mult = job.stat_bonuses.get("hp_multiplier", 1.0)
                    mp_mult = job.stat_bonuses.get("mp_multiplier", 1.0)
                    atk_mult = job.stat_bonuses.get("attack_multiplier", 1.0)
                    def_mult = job.stat_bonuses.get("defense_multiplier", 1.0)
                    mag_mult = job.stat_bonuses.get("magic_multiplier", 1.0)

        final_hp = int(base_hp * hp_mult)
        final_mp = int(base_mp * mp_mult)
        final_attack = int(base_attack * atk_mult)
        final_defense = int(base_defense * def_mult)
        final_magic = int(base_magic * mag_mult)

        # 3) 装備ボーナスを加算
        if item_system is not None:
            equipment = actor.get("equipment", {})
            for slot, item_id in equipment.items():
                if item_id is None:
                    continue
                item = item_system.get_item(item_id)
                if item is None:
                    continue
                bonuses = item.stat_bonuses
                final_hp += bonuses.get("hp", 0)
                final_mp += bonuses.get("mp", 0)
                final_attack += bonuses.get("attack", 0)
                final_defense += bonuses.get("defense", 0)
                final_magic += bonuses.get("magic", 0)

        # 最小値を保証
        return {
            "max_hp": max(1, final_hp),
            "max_mp": max(0, final_mp),
            "attack": max(1, final_attack),
            "defense": max(0, final_defense),
            "magic": max(0, final_magic),
        }

    def get_battle_defaults(self, character_name: str) -> Dict[str, Any]:
        """バトル用のデフォルト値を取得（速度係数、スプライト名）"""
        return self.CHARACTER_BATTLE_DEFAULTS.get(character_name, {"speed": 1.0, "sprite": "ally_default.png"})

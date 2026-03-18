"""
ジョブ・アビリティシステムモジュール

FF5型のジョブチェンジ＆アビリティ習得メカニズムを実装
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


class Ability:
    """アビリティデータクラス"""
    
    def __init__(self, ability_dict: Dict[str, Any]):
        self.ability_id = ability_dict.get("ability_id")
        self.name = ability_dict.get("name")
        self.type = ability_dict.get("type")  # attack, magic, heal, support, special
        self.description = ability_dict.get("description")
        self.mp_cost = ability_dict.get("mp_cost", 0)
        self.power = ability_dict.get("power", [0, 0])
        self.accuracy = ability_dict.get("accuracy", 100)
        self.target_type = ability_dict.get("target_type", "single_enemy")
        self.effect = ability_dict.get("effect")
        self.raw_data = ability_dict
    
    def can_use(self, actor: Dict) -> Tuple[bool, Optional[str]]:
        """
        アクターがこのアビリティを使用可能か判定
        
        Returns:
            (使用可能か, エラーメッセージ)
        """
        if actor.get("mp", 0) < self.mp_cost:
            return False, f"MPが{self.mp_cost}足りません"
        return True, None


class Job:
    """ジョブデータクラス"""
    
    def __init__(self, job_dict: Dict[str, Any], ability_system: 'AbilitySystem'):
        self.job_id = job_dict.get("job_id")
        self.name = job_dict.get("name")
        self.character = job_dict.get("character")
        self.description = job_dict.get("description")
        self.required_level = job_dict.get("required_level", 1)
        self.stat_bonuses = job_dict.get("stat_bonuses", {})
        self.ability_list = job_dict.get("abilities", [])
        self.ability_system = ability_system
        self.raw_data = job_dict
    
    def get_learned_abilities(self, actor_level: int) -> List[Ability]:
        """
        そのジョブで習得済みのアビリティリストを取得
        
        Args:
            actor_level: キャラクターレベル
            
        Returns:
            習得済みアビリティのリスト
        """
        learned = []
        for ability_info in self.ability_list:
            if actor_level >= ability_info["learn_level"]:
                ability = self.ability_system.get_ability(ability_info["ability_id"])
                if ability:
                    learned.append(ability)
        return learned
    
    def get_stat_multiplier(self, stat_type: str) -> float:
        """ジョブのステータス補正倍率を取得"""
        multiplier_key = f"{stat_type}_multiplier"
        return self.stat_bonuses.get(multiplier_key, 1.0)


class AbilitySystem:
    """アビリティシステム管理クラス"""
    
    def __init__(self, abilities_path: Optional[str] = None):
        """
        アビリティデータを初期化
        
        Args:
            abilities_path: abilities.jsonへのパス
        """
        if abilities_path is None:
            abilities_path = Path(__file__).resolve().parents[2] / "data" / "abilities.json"
        
        with open(abilities_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.abilities = {}
        for ability_dict in data.get("abilities", []):
            ability_id = ability_dict.get("ability_id")
            self.abilities[ability_id] = Ability(ability_dict)
    
    def get_ability(self, ability_id: str) -> Optional[Ability]:
        """アビリティIDからアビリティオブジェクトを取得"""
        return self.abilities.get(ability_id)
    
    def get_all_abilities(self) -> List[Ability]:
        """全アビリティのリストを取得"""
        return list(self.abilities.values())


class JobSystem:
    """ジョブシステム管理クラス"""
    
    def __init__(
        self,
        jobs_path: Optional[str] = None,
        abilities_path: Optional[str] = None
    ):
        """
        ジョブとアビリティシステムを初期化
        
        Args:
            jobs_path: jobs.jsonへのパス
            abilities_path: abilities.jsonへのパス
        """
        if jobs_path is None:
            jobs_path = Path(__file__).resolve().parents[2] / "data" / "jobs.json"
        
        # アビリティシステムを先に初期化
        self.ability_system = AbilitySystem(abilities_path)
        
        # ジョブデータを読み込み
        with open(jobs_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.jobs = {}
        for job_dict in data.get("jobs", []):
            job_id = job_dict.get("job_id")
            self.jobs[job_id] = Job(job_dict, self.ability_system)
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """ジョブIDからジョブオブジェクトを取得"""
        return self.jobs.get(job_id)
    
    def get_jobs_for_character(self, character_name: str) -> List[Job]:
        """キャラクター名から習得可能なジョブリストを取得"""
        return [job for job in self.jobs.values() if job.character == character_name]
    
    def apply_job_stats(self, actor: Dict, job: Job) -> None:
        """
        ジョブのステータス補正をアクターに適用

        基本値（base_*）にジョブ補正倍率を掛けて現在のステータスを更新する。
        HP/MPは比率を維持する。

        Args:
            actor: キャラクターデータ
            job: ジョブオブジェクト
        """
        stat_mapping = {
            "max_hp": ("base_max_hp", "hp_multiplier"),
            "max_mp": ("base_max_mp", "mp_multiplier"),
            "attack": ("base_attack", "attack_multiplier"),
            "defense": ("base_defense", "defense_multiplier"),
            "magic": ("base_magic", "magic_multiplier"),
        }

        # HP/MPの比率を保存
        hp_ratio = actor.get("hp", 1) / max(1, actor.get("max_hp", 1))
        mp_ratio = actor.get("mp", 0) / max(1, actor.get("max_mp", 1))

        for stat_key, (base_key, mult_key) in stat_mapping.items():
            base_val = actor.get(base_key, actor.get(stat_key, 1))
            multiplier = job.stat_bonuses.get(mult_key, 1.0)
            actor[stat_key] = max(1, int(base_val * multiplier))

        # HP/MPの比率を復元
        actor["hp"] = max(1, min(actor["max_hp"], int(actor["max_hp"] * hp_ratio)))
        actor["mp"] = max(0, min(actor["max_mp"], int(actor["max_mp"] * mp_ratio)))


def change_job(
    actor: Dict,
    job_system: JobSystem,
    job_id: str
) -> Tuple[bool, Optional[str]]:
    """
    キャラクターのジョブをチェンジ
    
    Args:
        actor: キャラクターデータ
        job_system: JobSystemインスタンス
        job_id: チェンジ先のジョブID
        
    Returns:
        (成功したか, エラーメッセージ)
    """
    job = job_system.get_job(job_id)
    if not job:
        return False, f"ジョブ{job_id}が見つかりません"
    
    # キャラクター確認
    if job.character != actor.get("name"):
        return False, f"{actor.get('name')}はそのジョブに就けません"
    
    # レベル確認
    if actor.get("level", 1) < job.required_level:
        return False, f"レベル{job.required_level}以上が必要です"
    
    # ジョブをチェンジ
    actor["current_job"] = job_id
    actor["job_object"] = job
    
    return True, None


def get_available_abilities(
    actor: Dict,
    job_system: JobSystem
) -> List[Ability]:
    """
    アクターが使用可能なアビリティリストを取得
    
    Args:
        actor: キャラクターデータ
        job_system: JobSystemインスタンス
        
    Returns:
        使用可能なアビリティのリスト
    """
    job_id = actor.get("current_job")
    if not job_id:
        # デフォルトジョブ設定（未実装時の処理）
        jobs = job_system.get_jobs_for_character(actor.get("name"))
        if jobs:
            job = jobs[0]
        else:
            return []
    else:
        job = job_system.get_job(job_id)
        if not job:
            return []
    
    actor_level = actor.get("level", 1)
    return job.get_learned_abilities(actor_level)


def can_use_ability(
    actor: Dict,
    ability_id: str,
    job_system: JobSystem
) -> Tuple[bool, Optional[str]]:
    """
    アビリティが使用可能か判定
    
    Args:
        actor: キャラクターデータ
        ability_id: アビリティID
        job_system: JobSystemインスタンス
        
    Returns:
        (使用可能か, エラーメッセージ)
    """
    # アビリティを習得しているか確認
    available_abilities = get_available_abilities(actor, job_system)
    ability = None
    for ab in available_abilities:
        if ab.ability_id == ability_id:
            ability = ab
            break
    
    if not ability:
        return False, "そのアビリティは習得していません"
    
    # 使用条件を確認（MP等）
    return ability.can_use(actor)


def use_ability(
    actor: Dict,
    ability_id: str,
    target: Dict,
    job_system: JobSystem
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    アビリティを使用
    
    Args:
        actor: アクター
        ability_id: アビリティID
        target: ターゲット
        job_system: JobSystemインスタンス
        
    Returns:
        (成功したか, 効果情報)
    """
    can_use, error_msg = can_use_ability(actor, ability_id, job_system)
    if not can_use:
        return False, {"error": error_msg}
    
    ability = job_system.ability_system.get_ability(ability_id)
    
    # MP消費
    actor["mp"] -= ability.mp_cost
    
    # 効果情報を返す（具体的な計算はダメージシステムで行う）
    effect_info = {
        "ability_id": ability_id,
        "ability_name": ability.name,
        "mp_cost": ability.mp_cost,
        "power": ability.power,
        "accuracy": ability.accuracy,
        "target_type": ability.target_type,
        "effect": ability.effect,
        "raw_data": ability.raw_data,
    }
    
    return True, effect_info


def initialize_actor_job(
    actor: Dict,
    job_system: JobSystem,
    character_name: str
) -> None:
    """
    アクターに初期ジョブを設定
    
    Args:
        actor: キャラクターデータ
        job_system: JobSystemインスタンス
        character_name: キャラクター名
    """
    current_job_id = actor.get("current_job")
    if current_job_id:
        existing_job = job_system.get_job(current_job_id)
        if existing_job and existing_job.character == character_name:
            actor["job_object"] = existing_job
            return

    jobs = job_system.get_jobs_for_character(character_name)
    if jobs:
        # ジョブ未設定時のみ最初のジョブをデフォルトに設定
        actor["current_job"] = jobs[0].job_id
        actor["job_object"] = jobs[0]

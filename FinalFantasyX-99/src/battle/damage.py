"""ダメージ計算モジュール（FF5/FF6寄り）"""

from __future__ import annotations

import random


def _random_factor() -> float:
    return random.uniform(0.875, 1.0)


def _clamp_damage(value: float, max_damage: int = 9999) -> int:
    return max(0, min(max_damage, int(value)))


def calculate_physical_damage(
    attacker: dict,
    defender: dict,
    *,
    critical_rate: float = 1 / 32,
    berserk: bool = False,
    front_back_modifier: float = 1.0,
    max_damage: int = 9999,
) -> tuple[int, bool]:
    """FF6風の物理ダメージ計算（簡略版）"""
    level = int(attacker.get("level", 1))
    vigor = int(attacker.get("vigor", attacker.get("attack", 10)))
    weapon_power = int(attacker.get("weapon_power", attacker.get("attack", 10)))
    defense = int(defender.get("defense", 0))

    attack_value = weapon_power + 2 * vigor
    if vigor >= 128:
        attack_value = 255

    base = weapon_power + (((level ** 2) * attack_value) / 256) * 1.5

    is_critical = random.random() < critical_rate
    if is_critical:
        base *= 2.0
    if berserk:
        base *= 1.5

    base *= front_back_modifier
    base *= _random_factor()

    reduced = max(1.0, base - defense * 0.9)
    return _clamp_damage(reduced, max_damage), is_critical


def calculate_magic_damage(
    attacker: dict,
    defender: dict,
    *,
    spell_power: int,
    accessory_modifier: float = 1.0,
    back_attack_modifier: float = 1.0,
    element_modifier: float = 1.0,
    max_damage: int = 9999,
) -> int:
    """FF6風の魔法ダメージ計算（簡略版）"""
    level = int(attacker.get("level", 1))
    magic = int(attacker.get("magic", attacker.get("attack", 10)))
    mdef = int(defender.get("magic_defense", defender.get("defense", 0)))

    base = spell_power * 4 + (level * spell_power * magic / 32)
    base *= accessory_modifier
    base *= back_attack_modifier
    base *= _random_factor()

    reduced = max(0.0, base - mdef * 1.1)
    reduced *= element_modifier
    return _clamp_damage(reduced, max_damage)


def calculate_heal_amount(caster: dict, *, spell_power: int, variance: tuple[float, float] = (0.92, 1.08)) -> int:
    """魔法/アイテム回復量の共通計算"""
    level = int(caster.get("level", 1))
    magic = int(caster.get("magic", caster.get("attack", 10)))
    low, high = variance
    amount = (spell_power * 2.2) + (level * magic / 12)
    amount *= random.uniform(low, high)
    return max(1, int(amount))

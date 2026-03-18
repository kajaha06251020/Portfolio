"""ATBゲージ計算モジュール"""

from __future__ import annotations


def calculate_atb_increment(
    *,
    agility: int,
    weight: int,
    speed_coeff: float = 1.0,
    haste: bool = False,
    slow: bool = False,
    status_multiplier: float = 1.0,
    base_rate: float = 0.0048,
) -> float:
    """素早さと装備重量を反映したATB増加量を返す

    status_multiplier が指定されている場合（1.0以外）、haste/slow フラグは無視され
    StatusEffectManager.get_atb_multiplier() が返す値が使われる。
    """
    effective_agility = max(1.0, agility - (weight * 0.35))
    modifier = speed_coeff
    if status_multiplier != 1.0:
        # StatusEffectManager経由の倍率を使用
        modifier *= status_multiplier
    else:
        # 旧来のブーリアンフラグによる計算（後方互換性）
        if haste:
            modifier *= 1.5
        if slow:
            modifier *= 0.5
    return base_rate * (effective_agility / 32.0) * modifier


def advance_atb(current: float, increment: float) -> float:
    return min(1.0, current + max(0.0, increment))

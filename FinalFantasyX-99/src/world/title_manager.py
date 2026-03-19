"""称号システム — Title Manager"""
from __future__ import annotations
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TitleManager:
    """称号の付与と管理を担当する。"""

    def __init__(self, game):
        self.game = game
        self._definitions: list[dict] = []
        self._load_definitions()

    def _load_definitions(self) -> None:
        path = Path(__file__).resolve().parents[2] / "data" / "titles.json"
        try:
            self._definitions = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Failed to load titles.json")
            self._definitions = []

    def get_stat_bonus(self) -> dict:
        """現在の称号リストから合算ボーナスを返す（atk/def/spd/lck）。"""
        bonus: dict = {}
        awarded = getattr(self.game, "titles", [])
        for title in self._definitions:
            if title["id"] in awarded:
                for stat, val in title.get("bonus", {}).items():
                    bonus[stat] = bonus.get(stat, 0) + val
        return bonus

    def check_and_award(self) -> list[str]:
        """未獲得の称号のうち条件を満たすものを付与し、新しく獲得した称号名リストを返す。"""
        awarded = list(getattr(self.game, "titles", []))  # defensive copy
        newly_awarded: list[str] = []

        for title in self._definitions:
            if title["id"] in awarded:
                continue
            if self._check_condition(title["condition"]):
                awarded.append(title["id"])
                newly_awarded.append(title["name"])
                logger.info("Title awarded: %s", title["name"])

        self.game.titles = awarded
        return newly_awarded

    def _check_condition(self, cond: dict) -> bool:
        ctype = cond.get("type")
        threshold = cond.get("threshold", 0)

        if ctype == "enemies_defeated_total":
            bestiary = getattr(self.game, "bestiary", {})
            total = sum(bestiary.get("enemies_defeated", {}).values())
            return total >= threshold

        if ctype == "battles_fled":
            return getattr(self.game, "battles_fled", 0) >= threshold

        if ctype == "gold_owned":
            return self.game.gold >= threshold

        if ctype == "total_damage_dealt":
            return getattr(self.game, "total_damage_dealt", 0) >= threshold

        logger.warning("Unknown title condition type: %s", ctype)
        return False

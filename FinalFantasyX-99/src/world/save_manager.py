"""セーブ管理 — Save Manager

3スロット JSON セーブ/ロード、ゲームオーバーペナルティ付き。
"""

from __future__ import annotations

import copy
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class SaveManager:
    SLOT_COUNT = 3
    SAVE_DIR = "saves"

    def __init__(self, game):
        self.game = game
        self._last_save_type: str | None = None  # 最後にロードしたセーブの種別
        # saves ディレクトリを自動作成
        save_dir = Path(self._get_project_root()) / self.SAVE_DIR
        save_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _get_project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def _slot_path(self, slot: int) -> Path:
        return Path(self._get_project_root()) / self.SAVE_DIR / f"slot_{slot}.json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, slot: int, save_type: str = "tile") -> bool:
        """ゲーム状態を *slot* にセーブする。成功時 ``True`` を返す。"""
        try:
            data = self._serialize(save_type)
            data["meta"]["slot"] = slot

            slot_path = self._slot_path(slot)
            tmp_path = slot_path.with_suffix(".json.tmp")

            tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_path.replace(slot_path)

            logger.info("Saved to slot %d (type=%s)", slot, save_type)
            return True
        except Exception:
            logger.exception("Failed to save to slot %d", slot)
            return False

    def load(self, slot: int) -> bool:
        """*slot* からゲーム状態をロードする。成功時 ``True`` を返す。"""
        slot_path = self._slot_path(slot)
        if not slot_path.exists():
            logger.warning("Save slot %d not found: %s", slot, slot_path)
            return False

        try:
            data = json.loads(slot_path.read_text(encoding="utf-8"))
            self._deserialize(data)
            self._last_save_type = data["location"]["save_type"]
            logger.info("Loaded slot %d (type=%s)", slot, self._last_save_type)
            return True
        except Exception:
            logger.exception("Failed to load slot %d", slot)
            return False

    def load_latest(self) -> bool:
        """タイムスタンプが最新のスロットをロードする。セーブがなければ ``False``。"""
        best_slot: int | None = None
        best_ts: str = ""

        for slot in range(self.SLOT_COUNT):
            info = self.get_slot_info(slot)
            if info is None:
                continue
            ts = info["meta"].get("timestamp", "")
            # 同一タイムスタンプはスロット番号大を優先
            if ts > best_ts or (ts == best_ts and (best_slot is None or slot > best_slot)):
                best_ts = ts
                best_slot = slot

        if best_slot is None:
            return False

        return self.load(best_slot)

    def get_slot_info(self, slot: int) -> dict | None:
        """スロットの ``meta`` と ``location`` だけ返す。ファイルがなければ ``None``。"""
        slot_path = self._slot_path(slot)
        if not slot_path.exists():
            return None

        try:
            data = json.loads(slot_path.read_text(encoding="utf-8"))
            return {
                "meta": data.get("meta", {}),
                "location": data.get("location", {}),
            }
        except Exception:
            logger.exception("Failed to read slot info for slot %d", slot)
            return None

    def apply_game_over_penalty(self) -> None:
        """ゲームオーバーペナルティ: 先頭のみHP/MP全快、他メンバーはHP/MP 0、ゴールド半減。"""
        # game.party は game.character_data.get_party() の _party への参照。
        # インプレース変更するため replace_party() は呼ばない。
        party = self.game.party
        if party:
            party[0]["hp"] = party[0]["max_hp"]
            party[0]["mp"] = party[0]["max_mp"]
            for member in party[1:]:
                member["hp"] = 0
                member["mp"] = 0
        self.game.gold = max(self.game.gold // 2, 0)

    def has_any_save(self) -> bool:
        """いずれかのスロットファイルが存在すれば ``True``。"""
        return any(self._slot_path(slot).exists() for slot in range(self.SLOT_COUNT))

    def get_save_type(self) -> str | None:
        """最後にロードしたセーブの種別を返す。"""
        return self._last_save_type

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def _serialize(self, save_type: str) -> dict:
        map_scene = self.game.scenes.get("map")
        party_data = copy.deepcopy(self.game.character_data.get_party())
        return {
            "meta": {
                "slot": None,  # save() で上書き
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "playtime_seconds": getattr(self.game, "playtime_seconds", 0.0),
                "map_display_name": (map_scene.current_map_data or {}).get("display_name", ""),
                "party_leader_level": party_data[0]["level"] if party_data else 1,
            },
            "location": {
                "map_id": map_scene.current_map if map_scene else "DQ_OverWorld",
                "player_x": map_scene.player.grid_x if map_scene else 0,
                "player_y": map_scene.player.grid_y if map_scene else 0,
                "layer": map_scene._current_layer if map_scene else "physical",
                "save_type": save_type,
            },
            "party": party_data,
            "inventory": dict(self.game.inventory),
            "gold": self.game.gold,
            "world_state": copy.deepcopy(self.game.world_state_manager._state),
        }

    def _deserialize(self, data: dict) -> None:
        loc = data["location"]
        map_scene = self.game.scenes.get("map")

        # マップ位置を復元
        if map_scene:
            map_scene.current_map = loc["map_id"]
            map_scene.player_grid_pos = [loc["player_x"], loc["player_y"]]
            map_scene._current_layer = loc.get("layer", "physical")

        # パーティを復元
        self.game.character_data.replace_party(data["party"])

        # インベントリを復元
        self.game.inventory.clear()
        self.game.inventory.update(data["inventory"])

        # ゴールドを復元
        self.game.gold = data["gold"]

        # ワールド状態を復元
        self.game.world_state_manager._state = copy.deepcopy(data["world_state"])

        # プレイ時間を復元
        if hasattr(self.game, "playtime_seconds"):
            self.game.playtime_seconds = data.get("meta", {}).get("playtime_seconds", 0.0)

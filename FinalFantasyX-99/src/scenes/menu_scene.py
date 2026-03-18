"""キーボード操作専用メニューシーン"""

import json
from pathlib import Path
import pygame

from src.scenes.base_scene import BaseScene
from src.audio_manager import get_audio_manager
from src.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    WHITE,
    YELLOW,
    FONT_SIZE_SMALL,
    FONT_SIZE_MEDIUM,
    scaled,
)
from src.font import get_font
from src.ui.panel import UIPanel


class MenuScene(BaseScene):
    """キーボードのみで操作するインゲームメニュー"""

    def __init__(self, game):
        super().__init__(game)
        self.font = None
        self.small_font = None
        self.state = "main"
        self.selected_index = 0
        self.main_items = ["パーティ", "インベントリ", "装備変更", "クエスト", "セーブ", "タイトルへ", "もどる"]
        self.item_name_cache = None
        self.item_data_cache = None
        self.selected_actor_index = 0
        self.selected_slot = "weapon"
        self.selected_item_id = None
        self.equipment_slots = ["weapon", "head", "body", "accessory1", "accessory2"]
        self.inventory_order = []
        self.inventory_swap_index = None
        self.return_state_after_target = "inventory"
        self.info_message = ""
        self.audio_manager = get_audio_manager()
        self.cursor_surface = None

    def on_enter(self):
        self.font = get_font(FONT_SIZE_MEDIUM)
        self.small_font = get_font(FONT_SIZE_SMALL)
        self.state = "main"
        self.selected_index = 0
        if self.item_name_cache is None:
            self.item_name_cache = self._load_item_name_cache()
        if self.item_data_cache is None:
            self.item_data_cache = self._load_item_data_cache()
        self._sync_inventory_order()
        self.inventory_swap_index = None
        self._ensure_cursor_loaded()
        if hasattr(self.game, "character_data"):
            self.game.character_data.ensure_integrity()

    def handle_events(self, events: list):
        # Save slot UI handles its own input when active
        map_scene = self.game.scenes.get("map")
        save_slot_ui = getattr(map_scene, "save_slot_ui", None) if map_scene else None
        if save_slot_ui is not None and save_slot_ui.is_active:
            for event in events:
                save_slot_ui.handle_event(event)
            return

        # Quest log overlay handles its own input when active
        if self.state == "quest_log":
            quest_log = getattr(self.game, "quest_log_ui", None)
            if quest_log is not None and quest_log.active:
                quest_log.handle_events(events)
                if not quest_log.active:
                    # Quest log was closed
                    self.state = "main"
                    self.selected_index = 3
                    self.info_message = ""
                return

        for event in events:
            if event.type != pygame.KEYDOWN:
                continue

            if event.key in (pygame.K_UP, pygame.K_w):
                self._move_cursor(-1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._move_cursor(1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._play_menu_se("menu_confirm")
                self._confirm()
            elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self._play_menu_se("menu_cancel")
                self._back()

    def _play_menu_se(self, se_id: str):
        if self.audio_manager:
            self.audio_manager.play_se(se_id)

    def _move_cursor(self, direction: int):
        options_len = self._current_option_count()
        if options_len <= 0:
            self.selected_index = 0
            return
        prev_index = self.selected_index
        self.selected_index = (self.selected_index + direction) % options_len
        if self.selected_index != prev_index:
            self._play_menu_se("menu_select")
        self._update_info_message_for_selection()

    def _current_option_count(self) -> int:
        return len(self._get_right_options())

    def _get_right_title(self) -> str:
        titles = {
            "main": "コマンド",
            "party": "パーティ情報",
            "party_detail": "キャラ選択",
            "inventory": "所持アイテム",
            "use_item": "使用するアイテム",
            "use_item_target": "対象キャラ選択",
            "equip_actor": "装備変更キャラ",
            "equip_slot": "装備スロット",
            "equip_item": "装備アイテム",
        }
        return titles.get(self.state, "コマンド")

    def _get_right_options(self):
        party = getattr(self.game, "party", [])

        if self.state == "main":
            return list(self.main_items)

        if self.state == "party":
            if not party:
                return ["パーティメンバーなし"]
            return [
                f"{actor.get('name', '???')}  Lv{actor.get('level', 1)}  HP {actor.get('hp', 0)}/{actor.get('max_hp', 0)}"
                for actor in party
            ]

        if self.state == "party_detail":
            if not party:
                return ["パーティメンバーなし"]
            return [
                f"{actor.get('name', '???')}  Lv{actor.get('level', 1)}"
                for actor in party
            ]

        if self.state == "inventory":
            entries = self._get_inventory_id_entries()
            if not entries:
                return ["インベントリは空です"]
            return [f"{name} x{amount}" for _, name, amount in entries]

        if self.state == "use_item":
            entries = self._get_usable_item_entries()
            if not entries:
                return ["使用可能なアイテムなし"]
            return [f"{name} x{amount}" for _, name, amount in entries]

        if self.state in ["use_item_target", "equip_actor"]:
            if not party:
                return ["対象キャラがいません"]
            return [f"{actor.get('name', '???')}  HP {actor.get('hp', 0)}/{actor.get('max_hp', 0)}  MP {actor.get('mp', 0)}/{actor.get('max_mp', 0)}" for actor in party]

        if self.state == "equip_slot":
            slot_labels = self._slot_labels()
            if not party:
                return ["スロットなし"]
            actor = party[self.selected_actor_index]
            options = []
            for slot in self.equipment_slots:
                item_id = actor.get("equipment", {}).get(slot)
                equip_name = self._resolve_item_name(item_id) if item_id else "-"
                options.append(f"{slot_labels.get(slot, slot)}: {equip_name}")
            return options

        if self.state == "equip_item":
            options = self._get_equip_options(self.selected_actor_index, self.selected_slot)
            if not options:
                return ["装備候補なし"]
            return [label for _, label in options]

        return []

    def _confirm(self):
        if self.state == "main":
            self._select_main_item()
            return

        if self.state == "party":
            party = getattr(self.game, "party", [])
            if party:
                self.selected_actor_index = self.selected_index
                self.state = "party_detail"
                self.selected_index = self.selected_actor_index
                actor = party[self.selected_actor_index]
                self.info_message = f"{actor.get('name', '???')} の詳細を表示中"
            return

        if self.state == "party_detail":
            party = getattr(self.game, "party", [])
            if party:
                self.selected_actor_index = self.selected_index
                actor = party[self.selected_actor_index]
                self.info_message = f"{actor.get('name', '???')} の詳細を表示中"
            return

        if self.state == "inventory":
            self._confirm_inventory_selection()
            return

        if self.state == "use_item_target":
            self._use_item_on_actor(self.selected_item_id, self.selected_index)
            return

        if self.state == "equip_actor":
            if not getattr(self.game, "party", []):
                self.info_message = "パーティメンバーがいません"
                return
            self.selected_actor_index = self.selected_index
            self.state = "equip_slot"
            self.selected_index = 0
            self._update_info_message_for_selection()
            return

        if self.state == "equip_slot":
            self.selected_slot = self.equipment_slots[self.selected_index]
            self.state = "equip_item"
            self.selected_index = 0
            self._update_info_message_for_selection()
            return

        if self.state == "equip_item":
            options = self._get_equip_options(self.selected_actor_index, self.selected_slot)
            if not options:
                self.info_message = "装備可能なアイテムがありません"
                return
            selected = options[self.selected_index]
            self._equip_item(self.selected_actor_index, self.selected_slot, selected[0])

    def _back(self):
        if self.state == "main":
            self.game.change_scene("map")
            return

        if self.state == "quest_log":
            quest_log = getattr(self.game, "quest_log_ui", None)
            if quest_log is not None:
                quest_log.close()
            self.state = "main"
            self.selected_index = 3
            self.info_message = ""
            return

        if self.state in ["party", "inventory", "use_item", "equip_actor"]:
            self.inventory_swap_index = None
            self.state = "main"
            self.selected_index = 0
            self.info_message = ""
            return

        if self.state == "party_detail":
            self.state = "party"
            self.selected_index = self.selected_actor_index
            self.info_message = ""
            return

        if self.state == "use_item_target":
            self.state = self.return_state_after_target
            self.selected_index = 0
            self._update_info_message_for_selection()
            return

        if self.state == "equip_slot":
            self.state = "equip_actor"
            self.selected_index = self.selected_actor_index
            self.info_message = "装備を変更するキャラを選択"
            return

        if self.state == "equip_item":
            self.state = "equip_slot"
            self.selected_index = self.equipment_slots.index(self.selected_slot)
            self._update_info_message_for_selection()
            return

        self.state = "main"
        self.selected_index = 0
        self.info_message = ""

    def _select_main_item(self):
        index = self.selected_index

        if index == 0:
            self.state = "party"
            self.selected_index = 0
            self.info_message = "左に全体ステータス、右でメンバー確認"
        elif index == 1:
            self.state = "inventory"
            self.selected_index = 0
            self.inventory_swap_index = None
            self._update_info_message_for_selection()
        elif index == 2:
            self.state = "equip_actor"
            self.selected_index = 0
            self.info_message = "装備を変更するキャラを選択"
        elif index == 3:
            # クエストログを開く
            quest_log = getattr(self.game, "quest_log_ui", None)
            if quest_log is not None:
                self.state = "quest_log"
                quest_log.open()
            else:
                self.info_message = "クエストシステムは未初期化です"
        elif index == 4:
            map_scene = self.game.scenes.get("map")
            save_slot_ui = getattr(map_scene, "save_slot_ui", None) if map_scene else None
            if save_slot_ui is None:
                self.info_message = "セーブUIが初期化されていません"
            else:
                save_slot_ui.show("menu", self._on_menu_save_done)
        elif index == 5:
            self.game.change_scene("title")
        elif index == 6:
            self.game.change_scene("map")

    def _on_menu_save_done(self, slot):
        """セーブスロット選択コールバック"""
        if slot is None:
            self.info_message = "キャンセルしました"
            return
        save_manager = getattr(self.game, "save_manager", None)
        if save_manager and save_manager.save(slot, "menu"):
            self.info_message = f"スロット{slot}にセーブしました"
        else:
            self.info_message = "セーブに失敗しました"

    def _slot_labels(self):
        return {
            "weapon": "武器",
            "head": "頭",
            "body": "体",
            "accessory1": "アクセ1",
            "accessory2": "アクセ2",
        }

    def _load_item_name_cache(self):
        cache = {}
        items_file = Path(__file__).resolve().parents[2] / "data" / "items.json"
        if not items_file.exists():
            return cache

        with open(items_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for section in ("weapons", "armor", "accessory", "consumable", "materials"):
            for item in data.get(section, []):
                item_id = item.get("item_id")
                if not item_id:
                    continue
                cache[item_id] = item.get("name", item_id)

        return cache

    def _load_item_data_cache(self):
        cache = {}
        items_file = Path(__file__).resolve().parents[2] / "data" / "items.json"
        if not items_file.exists():
            return cache

        with open(items_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for section in ("weapons", "armor", "accessory", "consumable", "materials"):
            for item in data.get(section, []):
                item_id = item.get("item_id")
                if not item_id:
                    continue
                item_copy = dict(item)
                if section == "weapons":
                    item_copy["item_type"] = "weapon"
                elif section == "armor":
                    item_copy["item_type"] = "armor"
                elif section == "accessory":
                    item_copy["item_type"] = "accessory"
                elif section == "consumable":
                    item_copy["item_type"] = "consumable"
                else:
                    item_copy["item_type"] = "materials"
                cache[item_id] = item_copy

        return cache

    def _resolve_item_name(self, item_id: str) -> str:
        if not item_id:
            return "-"
        if not self.item_name_cache:
            return item_id
        return self.item_name_cache.get(item_id, item_id)

    def _get_inventory_id_entries(self):
        inventory = getattr(self.game, "inventory", {})
        self._sync_inventory_order()
        entries = []
        for item_id in self.inventory_order:
            amount = inventory.get(item_id, 0)
            if amount <= 0:
                continue
            entries.append((item_id, self._resolve_item_name(item_id), amount))
        return entries

    def _get_usable_item_entries(self):
        inventory = getattr(self.game, "inventory", {})
        self._sync_inventory_order()
        entries = []
        for item_id in self.inventory_order:
            amount = inventory.get(item_id, 0)
            if amount <= 0:
                continue
            item_data = self.item_data_cache.get(item_id, {}) if self.item_data_cache else {}
            if item_data.get("item_type") != "consumable":
                continue
            if not item_data.get("field_use", False):
                continue
            entries.append((item_id, self._resolve_item_name(item_id), amount))
        return entries

    def _can_equip_on_slot(self, item_data: dict, slot: str) -> bool:
        item_type = item_data.get("item_type")
        if item_type == "weapon":
            return slot == "weapon"
        if item_type == "armor":
            return item_data.get("slot") == slot
        if item_type == "accessory":
            return slot in ["accessory1", "accessory2"]
        return False

    def _get_equip_options(self, actor_index: int, slot: str):
        party = getattr(self.game, "party", [])
        if not party or actor_index >= len(party):
            return []

        actor = party[actor_index]
        options = [(None, "はずす")]
        inventory = getattr(self.game, "inventory", {})

        for item_id, amount in inventory.items():
            if amount <= 0:
                continue
            item_data = self.item_data_cache.get(item_id, {}) if self.item_data_cache else {}
            if not self._can_equip_on_slot(item_data, slot):
                continue
            required_level = int(item_data.get("required_level", 1))
            if actor.get("level", 1) < required_level:
                continue
            options.append((item_id, f"{self._resolve_item_name(item_id)} x{amount}"))

        return options

    def _consume_inventory_item(self, item_id: str, amount: int = 1):
        inventory = getattr(self.game, "inventory", {})
        current = inventory.get(item_id, 0)
        if current < amount:
            return False
        inventory[item_id] = current - amount
        if inventory[item_id] <= 0:
            del inventory[item_id]
        self._sync_inventory_order()
        return True

    def _add_inventory_item(self, item_id: str, amount: int = 1):
        inventory = getattr(self.game, "inventory", {})
        inventory[item_id] = inventory.get(item_id, 0) + amount
        self._sync_inventory_order()

    def _sync_inventory_order(self):
        inventory = getattr(self.game, "inventory", {})
        available_ids = [item_id for item_id, amount in inventory.items() if amount > 0]

        if not self.inventory_order:
            self.inventory_order = sorted(available_ids, key=lambda item_id: self._resolve_item_name(item_id))
        else:
            reordered = [item_id for item_id in self.inventory_order if item_id in available_ids]
            for item_id in available_ids:
                if item_id not in reordered:
                    reordered.append(item_id)
            self.inventory_order = reordered

        if self.inventory_swap_index is not None and self.inventory_swap_index >= len(self.inventory_order):
            self.inventory_swap_index = None

    def _swap_inventory_positions(self, from_index: int, to_index: int):
        if from_index == to_index:
            return
        if from_index < 0 or to_index < 0:
            return
        if from_index >= len(self.inventory_order) or to_index >= len(self.inventory_order):
            return
        self.inventory_order[from_index], self.inventory_order[to_index] = (
            self.inventory_order[to_index],
            self.inventory_order[from_index],
        )

    def _confirm_inventory_selection(self):
        entries = self._get_inventory_id_entries()
        if not entries:
            self.info_message = "インベントリは空です"
            self.inventory_swap_index = None
            return

        item_id, item_name, _ = entries[self.selected_index]

        if self.inventory_swap_index is None:
            self.inventory_swap_index = self.selected_index
            self.info_message = f"移動元: {item_name}  移動先でEnter。もう一度同じ項目で使用"
            return

        source_index = self.inventory_swap_index
        self.inventory_swap_index = None

        if source_index != self.selected_index:
            self._swap_inventory_positions(source_index, self.selected_index)
            self.info_message = "アイテム位置を入れ替えました"
            return

        self._start_item_use_from_inventory(item_id)

    def _start_item_use_from_inventory(self, item_id: str):
        item_data = self.item_data_cache.get(item_id, {}) if self.item_data_cache else {}
        if item_data.get("item_type") != "consumable" or not item_data.get("field_use", False):
            self.info_message = f"{self._resolve_item_name(item_id)} はフィールドで使用できません"
            return

        # party対象アイテムはキャラ選択不要
        if item_data.get("target") == "party":
            self.return_state_after_target = "inventory"
            self._use_item_on_actor(item_id, 0)  # actor_index=0 は使用されない
            return

        self.selected_item_id = item_id
        self.return_state_after_target = "inventory"
        self.state = "use_item_target"
        self.selected_index = 0
        self.info_message = f"{self._resolve_item_name(item_id)} を使う対象を選択"

    def _describe_item(self, item_id: str, amount: int | None = None) -> str:
        name = self._resolve_item_name(item_id)
        if not self.item_data_cache:
            return f"{name} x{amount}" if amount is not None else name

        item_data = self.item_data_cache.get(item_id, {})
        desc = item_data.get("description", "")
        base = f"{name} x{amount}" if amount is not None else name
        return f"{base}  {desc}" if desc else base

    def _update_info_message_for_selection(self):
        if self.state == "party_detail":
            party = getattr(self.game, "party", [])
            if not party:
                self.info_message = "パーティメンバーがいません"
                return
            if self.selected_index >= len(party):
                self.selected_index = len(party) - 1
            self.selected_actor_index = self.selected_index
            actor = party[self.selected_actor_index]
            self.info_message = f"{actor.get('name', '???')} の詳細を表示中"
            return

        if self.state == "inventory":
            entries = self._get_inventory_id_entries()
            if not entries:
                self.info_message = "インベントリは空です"
                return
            if self.selected_index >= len(entries):
                self.selected_index = len(entries) - 1
            item_id, _, amount = entries[self.selected_index]
            details = self._describe_item(item_id, amount)
            if self.inventory_swap_index is not None:
                self.info_message = f"{details}  Enterで移動確定 / 同じ項目で使用"
            else:
                self.info_message = details
            return

        if self.state == "use_item":
            entries = self._get_usable_item_entries()
            if not entries:
                self.info_message = "使用可能なアイテムがありません"
                return
            if self.selected_index >= len(entries):
                self.selected_index = len(entries) - 1
            item_id, _, amount = entries[self.selected_index]
            self.info_message = self._describe_item(item_id, amount)
            return

        if self.state == "equip_item":
            options = self._get_equip_options(self.selected_actor_index, self.selected_slot)
            if not options:
                self.info_message = "装備可能なアイテムがありません"
                return
            if self.selected_index >= len(options):
                self.selected_index = len(options) - 1
            item_id, label = options[self.selected_index]
            if item_id is None:
                self.info_message = "現在の装備を外します"
            else:
                self.info_message = self._describe_item(item_id)
            return

        if self.state == "equip_slot":
            party = getattr(self.game, "party", [])
            if not party or self.selected_actor_index >= len(party):
                return
            actor = party[self.selected_actor_index]
            if self.selected_index >= len(self.equipment_slots):
                self.selected_index = len(self.equipment_slots) - 1
            slot = self.equipment_slots[self.selected_index]
            equipped_item_id = actor.get("equipment", {}).get(slot)
            if not equipped_item_id:
                self.info_message = "このスロットには現在装備がありません"
            else:
                self.info_message = self._describe_item(equipped_item_id)
            return

    def _recalculate_actor_stats(self, actor: dict):
        equipment = actor.get("equipment", {})

        atk_bonus = 0
        def_bonus = 0
        mag_bonus = 0
        hp_bonus = 0
        mp_bonus = 0

        for item_id in equipment.values():
            if not item_id:
                continue
            item_data = self.item_data_cache.get(item_id, {}) if self.item_data_cache else {}
            bonuses = item_data.get("stat_bonuses", {})
            atk_bonus += int(bonuses.get("attack", 0))
            def_bonus += int(bonuses.get("defense", 0))
            mag_bonus += int(bonuses.get("magic", 0))
            hp_bonus += int(bonuses.get("hp", 0))
            mp_bonus += int(bonuses.get("mp", 0))

        actor["attack"] = max(1, int(actor.get("base_attack", actor.get("attack", 1))) + atk_bonus)
        actor["defense"] = max(0, int(actor.get("base_defense", actor.get("defense", 0))) + def_bonus)
        actor["magic"] = max(0, int(actor.get("base_magic", actor.get("magic", 0))) + mag_bonus)

        new_max_hp = max(1, int(actor.get("base_max_hp", actor.get("max_hp", 1))) + hp_bonus)
        new_max_mp = max(0, int(actor.get("base_max_mp", actor.get("max_mp", 0))) + mp_bonus)

        actor["max_hp"] = new_max_hp
        actor["max_mp"] = new_max_mp
        actor["hp"] = min(actor.get("hp", new_max_hp), new_max_hp)
        actor["mp"] = min(actor.get("mp", new_max_mp), new_max_mp)

    def _equip_item(self, actor_index: int, slot: str, new_item_id):
        party = getattr(self.game, "party", [])
        if not party or actor_index >= len(party):
            self.info_message = "パーティメンバーがいません"
            return

        actor = party[actor_index]
        actor.setdefault(
            "equipment",
            {
                "weapon": None,
                "head": None,
                "body": None,
                "accessory1": None,
                "accessory2": None,
            },
        )

        old_item_id = actor["equipment"].get(slot)

        if new_item_id is None:
            if old_item_id:
                self._add_inventory_item(old_item_id, 1)
                actor["equipment"][slot] = None
                self._recalculate_actor_stats(actor)
                self.info_message = f"{actor.get('name', '???')} の{self._slot_labels().get(slot, slot)}を外しました"
            else:
                self.info_message = "外せる装備がありません"
            return

        if not self._consume_inventory_item(new_item_id, 1):
            self.info_message = "アイテム在庫が不足しています"
            return

        if old_item_id:
            self._add_inventory_item(old_item_id, 1)

        actor["equipment"][slot] = new_item_id
        self._recalculate_actor_stats(actor)
        self.info_message = f"{actor.get('name', '???')} に {self._resolve_item_name(new_item_id)} を装備"

    def _use_item_on_actor(self, item_id: str, actor_index: int):
        party = getattr(self.game, "party", [])
        if not party or actor_index >= len(party):
            self.info_message = "対象キャラがいません"
            return

        item_data = self.item_data_cache.get(item_id, {}) if self.item_data_cache else {}
        if item_data.get("item_type") != "consumable":
            self.info_message = "このアイテムは使用できません"
            return

        if not self._consume_inventory_item(item_id, 1):
            self.info_message = "アイテム在庫が不足しています"
            return

        actor = party[actor_index]
        effect = item_data.get("effect")
        power = item_data.get("power")

        if effect == "heal" and isinstance(power, list) and len(power) == 2:
            heal_amount = (int(power[0]) + int(power[1])) // 2
            before = actor.get("hp", 0)
            actor["hp"] = min(actor.get("max_hp", before), before + heal_amount)
            actual = actor["hp"] - before
            self.info_message = f"{actor.get('name', '???')} のHPが{actual}回復"
        elif effect == "restore_mp" and isinstance(power, list) and len(power) == 2:
            mp_amount = (int(power[0]) + int(power[1])) // 2
            before = actor.get("mp", 0)
            actor["mp"] = min(actor.get("max_mp", before), before + mp_amount)
            actual = actor["mp"] - before
            self.info_message = f"{actor.get('name', '???')} のMPが{actual}回復"
        elif effect == "revive":
            if actor.get("hp", 0) <= 0:
                actor["hp"] = actor.get("max_hp", 1)
                self.info_message = f"{actor.get('name', '???')} が戦闘不能から回復"
            else:
                self.info_message = f"{actor.get('name', '???')} には効果がありません"
        elif effect == "rura":
            last_town = getattr(self.game, "last_town", None)
            if last_town is None:
                self.info_message = "まだ町を訪れていません"
                # アイテムを返却（消費済みを戻す）
                self._add_inventory_item(item_id, 1)
                return
            map_scene = self.game.scenes.get("map")
            if map_scene:
                # pending_transition を使って正式なマップ遷移を起動（TMX再読み込み・NPC再生成を含む）
                map_scene.pending_transition = {
                    "kind": "map",
                    "map_id": last_town["map_id"],
                    "x": last_town["x"],
                    "y": last_town["y"],
                }
                map_scene.fade_alpha = 0
                map_scene.fade_state = "out"
                self.info_message = f"キメラのつばさで {last_town['map_id']} へ戻った！"
                self.game.change_scene("map")
            return
        else:
            self.info_message = f"{self._resolve_item_name(item_id)} を使用しました"

        if self.return_state_after_target == "inventory":
            self.state = "inventory"
            self.selected_index = 0
            self.inventory_swap_index = None
            self._update_info_message_for_selection()

    def update(self):
        pass

    def _ensure_cursor_loaded(self):
        if self.cursor_surface is not None:
            return
        cursor_path = Path(__file__).resolve().parents[2] / "assets" / "images" / "UI" / "FinalFantasyCursor.png"
        try:
            image = pygame.image.load(str(cursor_path)).convert_alpha()
            target_h = scaled(16)
            ratio = target_h / max(1, image.get_height())
            target_w = max(1, int(image.get_width() * ratio))
            self.cursor_surface = pygame.transform.smoothscale(image, (target_w, target_h))
        except (pygame.error, FileNotFoundError):
            self.cursor_surface = None

    def _draw_cursor(self, screen: pygame.Surface, x: int, y: int, blink: bool = False):
        if blink and ((pygame.time.get_ticks() // 180) % 2 == 1):
            return
        if self.cursor_surface is not None:
            screen.blit(self.cursor_surface, (x, y))
            return
        fallback = self.small_font.render("▶", True, YELLOW)
        screen.blit(fallback, (x, y))

    def draw(self, screen: pygame.Surface):
        # Quest log overlay takes over the full screen
        if self.state == "quest_log":
            quest_log = getattr(self.game, "quest_log_ui", None)
            if quest_log is not None and quest_log.active:
                quest_log.draw(screen)
                return

        screen.fill((10, 16, 46))

        header_panel = UIPanel(
            scaled(20),
            scaled(16),
            SCREEN_WIDTH - scaled(40),
            scaled(58),
            title=f"状態: {self._get_right_title()}   所持ギル: {getattr(self.game, 'gold', 0)}",
            bg_color=(16, 24, 64),
            border_radius=scaled(6),
            padding=scaled(10),
            texture_scale=1.25,
            texture_repeat=False,
        )
        header_content = header_panel.draw(screen, title_font=self.small_font)

        left_panel = UIPanel(
            scaled(20),
            scaled(84),
            int(SCREEN_WIDTH * 0.58),
            SCREEN_HEIGHT - scaled(170),
            title="パーティ",
            bg_color=(20, 28, 74),
            border_radius=scaled(8),
            padding=scaled(12),
            texture_scale=1.55,
            texture_repeat=False,
        )
        left_content = left_panel.draw(screen, title_font=self.small_font)
        self._draw_party_summary(screen, left_content)

        right_panel = UIPanel(
            int(SCREEN_WIDTH * 0.60),
            scaled(84),
            SCREEN_WIDTH - int(SCREEN_WIDTH * 0.60) - scaled(20),
            SCREEN_HEIGHT - scaled(170),
            title=self._get_right_title(),
            bg_color=(20, 28, 74),
            border_radius=scaled(8),
            padding=scaled(12),
            texture_scale=1.55,
            texture_repeat=False,
        )
        right_content = right_panel.draw(screen, title_font=self.small_font)
        self._draw_right_options(screen, right_content)

        info_panel = UIPanel(
            scaled(20),
            SCREEN_HEIGHT - scaled(76),
            SCREEN_WIDTH - scaled(40),
            scaled(48),
            title="",
            bg_color=(14, 20, 56),
            border_radius=scaled(6),
            border_width=1,
            padding=scaled(10),
            texture_scale=1.1,
            texture_repeat=False,
        )
        info_content = info_panel.draw(screen, title_font=self.small_font)
        if self.info_message:
            info = self.small_font.render(self.info_message, True, WHITE)
            screen.blit(info, (info_content.x, info_content.y))

        # セーブスロットUIオーバーレイ
        map_scene = self.game.scenes.get("map")
        save_slot_ui = getattr(map_scene, "save_slot_ui", None) if map_scene else None
        if save_slot_ui is not None:
            save_slot_ui.draw(screen)

    def _draw_party_summary(self, screen: pygame.Surface, content_rect: pygame.Rect):
        party = getattr(self.game, "party", [])
        if not party:
            label = self.font.render("パーティメンバーがいません", True, WHITE)
            screen.blit(label, (content_rect.x, content_rect.y))
            return

        if self.state == "party_detail":
            if self.selected_actor_index >= len(party):
                self.selected_actor_index = len(party) - 1
            actor = party[self.selected_actor_index]

            lines = [
                f"名前: {actor.get('name', '???')}",
                f"レベル: {actor.get('level', 1)}",
                f"ジョブ: {actor.get('current_job', 'freelancer')}",
                f"JP: {actor.get('job_points', 0)}    習熟度: {actor.get('job_mastery', 0)}",
                f"EXP: {actor.get('current_exp', 0)}",
                f"HP: {actor.get('hp', 0)} / {actor.get('max_hp', 0)}",
                f"MP: {actor.get('mp', 0)} / {actor.get('max_mp', 0)}",
                f"攻撃: {actor.get('attack', 0)}   防御: {actor.get('defense', 0)}   魔力: {actor.get('magic', 0)}",
                f"基礎HP: {actor.get('base_max_hp', 0)}   基礎MP: {actor.get('base_max_mp', 0)}",
                f"基礎攻撃: {actor.get('base_attack', 0)}   基礎防御: {actor.get('base_defense', 0)}   基礎魔力: {actor.get('base_magic', 0)}",
            ]

            equipment = actor.get("equipment", {})
            slot_labels = self._slot_labels()
            for slot in self.equipment_slots:
                item_name = self._resolve_item_name(equipment.get(slot))
                lines.append(f"{slot_labels.get(slot, slot)}: {item_name}")

            line_y = content_rect.y
            line_gap = scaled(28)
            for line in lines:
                if line_y > content_rect.bottom - scaled(22):
                    break
                text = self.small_font.render(line, True, WHITE)
                screen.blit(text, (content_rect.x, line_y))
                line_y += line_gap
            return

        for i, actor in enumerate(party):
            y = content_rect.y + i * scaled(78)
            is_actor_cursor = self.state in ["party", "use_item_target", "equip_actor"] and i == self.selected_index
            color = YELLOW if is_actor_cursor else WHITE

            name_line = (
                f"{actor.get('name', '???')}  Lv {actor.get('level', 1)}  "
                f"Job {actor.get('current_job', 'freelancer')}  習熟度 {actor.get('job_mastery', 0)}"
            )
            hp_line = (
                f"HP {actor.get('hp', 0)}/{actor.get('max_hp', 0)}    "
                f"MP {actor.get('mp', 0)}/{actor.get('max_mp', 0)}    "
                f"EXP {actor.get('current_exp', 0)}    JP {actor.get('job_points', 0)}"
            )
            eq = actor.get("equipment", {})
            equip_line = (
                f"W:{self._resolve_item_name(eq.get('weapon'))}  "
                f"H:{self._resolve_item_name(eq.get('head'))}  "
                f"B:{self._resolve_item_name(eq.get('body'))}"
            )

            text1 = self.small_font.render(name_line, True, color)
            text2 = self.small_font.render(hp_line, True, color)
            text3 = self.small_font.render(equip_line, True, color)
            screen.blit(text1, (content_rect.x, y))
            screen.blit(text2, (content_rect.x + scaled(8), y + scaled(24)))
            screen.blit(text3, (content_rect.x + scaled(8), y + scaled(47)))

    def _draw_right_options(self, screen: pygame.Surface, content_rect: pygame.Rect):
        options = self._get_right_options()
        if not options:
            return

        for i, option in enumerate(options):
            y = content_rect.y + i * scaled(34)
            if y > content_rect.bottom - scaled(28):
                break
            color = YELLOW if i == self.selected_index else WHITE
            text = self.small_font.render(option, True, color)
            screen.blit(text, (content_rect.x + scaled(12), y))
            if self.state == "inventory" and self.inventory_swap_index == i:
                self._draw_cursor(screen, content_rect.x - scaled(34), y + scaled(2), blink=True)
            if i == self.selected_index:
                self._draw_cursor(screen, content_rect.x - scaled(14), y + scaled(2))

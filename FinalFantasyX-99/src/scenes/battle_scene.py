"""
バトルシーン（ATB + FF5/FF6風レイアウト）

Section 6 リファクタリング済み:
- StatusEffectManager統合
- CharacterDataManagerからのパーティ読み込み
- 装備・ジョブステータス統合パイプライン
- データ駆動のアイテム/魔法システム
- カーソルベースのターゲット選択
- 敵AIの能力使用
"""

from pathlib import Path
import json
import random
import pygame

from src.scenes.base_scene import BaseScene
from src.entities.enemy import Enemy
from src.entities.character_data import CharacterDataManager
from src.audio_manager import get_audio_manager
from src.battle.encounter import EncounterManager
from src.battle.damage import calculate_physical_damage, calculate_magic_damage, calculate_heal_amount
from src.battle.atb import calculate_atb_increment, advance_atb
from src.battle.leveling import LevelingSystem, apply_battle_rewards
from src.battle.job_ability import JobSystem, initialize_actor_job, get_available_abilities, use_ability
from src.battle.equipment import ItemSystem, apply_equipment_stats_from_data
from src.battle.status_effects import StatusEffectManager, get_random_action
from src.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    WHITE,
    YELLOW,
    RED,
    GREEN,
    FONT_SIZE_SMALL,
    FONT_SIZE_MEDIUM,
    scaled,
)
from src.font import get_font


# 敵データをファイルから読み込み（敵AI用）
_ENEMY_DATA_CACHE = None


def _load_enemy_data():
    """enemies.json の敵データを読み込みキャッシュ"""
    global _ENEMY_DATA_CACHE
    if _ENEMY_DATA_CACHE is not None:
        return _ENEMY_DATA_CACHE
    enemy_path = Path(__file__).resolve().parents[2] / "data" / "enemies.json"
    try:
        with open(enemy_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _ENEMY_DATA_CACHE = data.get("enemies", {})
    except (FileNotFoundError, json.JSONDecodeError):
        _ENEMY_DATA_CACHE = {}
    return _ENEMY_DATA_CACHE


class BattleScene(BaseScene):
    """ATB方式のFF風バトルシーン"""

    def __init__(self, game):
        super().__init__(game)
        self.font = None
        self.small_font = None

        self.allies = []
        self.enemies = []
        self.damage_popups = []

        self.leveling_system = LevelingSystem()
        self.job_system = JobSystem()
        self.item_system = ItemSystem()
        self.status_manager = StatusEffectManager()
        self.encounter_manager = EncounterManager()
        self.level_up_messages = []

        # オーディオマネージャー
        self.audio_manager = get_audio_manager()

        # まほうコマンドを削除 -- 魔法はジョブ技に統合
        self.main_commands = ["たたかう", "ジョブ技", "アイテム", "ぼうぎょ", "にげる"]

        # menu_state: none, main, ability, item, target_selection
        self.menu_state = "none"
        self.menu_index = 0
        self.active_actor_index = None
        self.ready_allies = []

        # ターゲット選択用
        self.target_index = 0
        self.target_side = "enemy"  # "enemy" or "ally"
        self._pending_action = None  # ターゲット選択後に実行するアクション情報

        self.battle_state = "running"  # running, victory, defeat
        self.message_log = []
        self.escape_message_timer = 0
        self.pending_encounter_group = None
        self.encounter_rewards = None
        self.last_reward_result = None
        self.cursor_surface = None

    def on_enter(self):
        self.font = get_font(FONT_SIZE_MEDIUM)
        self.small_font = get_font(FONT_SIZE_SMALL)
        self._ensure_cursor_loaded()

        self.allies = self._create_party()
        if self.pending_encounter_group:
            self.enemies = self._create_enemy_group_from_encounter(self.pending_encounter_group)
        else:
            self.enemies = self._create_enemy_group()
            self.encounter_rewards = None
        self.pending_encounter_group = None

        self.damage_popups = []
        self.ready_allies = []
        self.menu_state = "none"
        self.menu_index = 0
        self.active_actor_index = None
        self.target_index = 0
        self._pending_action = None
        self.battle_state = "running"
        self.victory_bgm_played = False

        # バトルBGMを再生
        self.audio_manager.play_bgm("battle", fade_in=500)
        # エンカウント効果音
        self.audio_manager.play_se("se_battle_start")
        self.message_log = []
        self.level_up_messages = []
        self.escape_message_timer = 0
        self.last_reward_result = None

        enemy_names = " / ".join(enemy["name"] for enemy in self.enemies)
        self._push_message(f"{enemy_names} があらわれた！")
        # 図鑑に敵を記録
        bestiary = getattr(self.game, "bestiary", None)
        if bestiary is not None:
            for enemy in self.enemies:
                name = enemy.get("name", "")
                if name and name not in bestiary["enemies_seen"]:
                    bestiary["enemies_seen"].append(name)

    # ------------------------------------------------------------------
    # パーティ生成: CharacterDataManagerからデータを読み込む
    # ------------------------------------------------------------------
    def _create_party(self):
        """CharacterDataManagerからパーティを読み込み、バトル用フィールドを付加"""
        party_data = self.game.character_data.get_party()
        party = []

        for member in party_data:
            name = member.get("name", "???")
            defaults = self.game.character_data.get_battle_defaults(name)

            # ステータス計算パイプライン: base x job x equipment
            final_stats = CharacterDataManager.calculate_final_stats(
                member, self.job_system, self.item_system
            )

            sprite_name = defaults.get("sprite", "ally_default.png")
            sprite = self._load_sprite(sprite_name, facing="left", tint=(100, 170, 255), kind="ally")

            speed = defaults.get("speed", 1.0)
            attack_val = final_stats["attack"]
            defense_val = final_stats["defense"]
            magic_val = final_stats["magic"]

            actor = {
                "name": name,
                "hp": min(member.get("hp", final_stats["max_hp"]), final_stats["max_hp"]),
                "max_hp": final_stats["max_hp"],
                "mp": min(member.get("mp", final_stats["max_mp"]), final_stats["max_mp"]),
                "max_mp": final_stats["max_mp"],
                "attack": attack_val,
                "defense": defense_val,
                "speed": speed,
                "level": member.get("level", 12),
                "vigor": attack_val + 6,
                "magic": magic_val,
                "weapon_power": attack_val + 22,
                "magic_defense": defense_val + 6,
                "agility": int(26 * speed),
                "weight": 14,
                "haste": False,
                "slow": False,
                "atb": random.uniform(0.15, 0.65),
                "alive": True,
                "defending": False,
                "sprite": sprite,
                "x": 0,
                "y": 0,
                "w": sprite.get_width(),
                "h": sprite.get_height(),
                "current_exp": member.get("current_exp", 3700),
                "job_points": member.get("job_points", 0),
                "job_mastery": member.get("job_mastery", 0),
                "current_job": member.get("current_job"),
                "base_max_hp": member.get("base_max_hp", final_stats["max_hp"]),
                "base_max_mp": member.get("base_max_mp", final_stats["max_mp"]),
                "base_attack": member.get("base_attack", attack_val),
                "base_defense": member.get("base_defense", defense_val),
                "base_magic": member.get("base_magic", magic_val),
                "equipment": member.get(
                    "equipment",
                    {"weapon": None, "head": None, "body": None, "accessory1": None, "accessory2": None},
                ),
                "status_effects": [],
            }
            party.append(actor)

        # 各キャラクターに初期ジョブを設定
        for actor in party:
            initialize_actor_job(actor, self.job_system, actor["name"])

        return party

    def _create_enemy_group_from_encounter(self, encounter_group):
        enemies = []
        enemy_data_db = _load_enemy_data()
        for enemy in encounter_group.enemies:
            sprite = self._load_sprite(
                f"enemy_{enemy.name}.png",
                facing="right",
                tint=tuple(enemy.color) if enemy.color else (200, 100, 100),
                kind="enemy",
            )
            # 敵の能力リストを取得
            abilities = self._get_enemy_abilities(enemy.name, enemy_data_db)
            enemies.append(
                {
                    "name": enemy.name,
                    "hp": enemy.hp,
                    "max_hp": enemy.max_hp,
                    "mp": enemy.mp,
                    "max_mp": enemy.max_mp,
                    "attack": enemy.attack,
                    "defense": enemy.defense,
                    "speed": enemy.speed,
                    "level": enemy.level,
                    "vigor": enemy.attack + 4,
                    "magic": max(1, int(enemy.attack * 0.8)),
                    "weapon_power": enemy.attack + 18,
                    "magic_defense": max(1, enemy.defense + 4),
                    "agility": max(12, int(20 * enemy.speed)),
                    "weight": 12,
                    "haste": False,
                    "slow": False,
                    "atb": random.uniform(0.0, 0.35),
                    "alive": True,
                    "sprite": sprite,
                    "x": 0,
                    "y": 0,
                    "w": sprite.get_width(),
                    "h": sprite.get_height(),
                    "abilities": abilities,
                    "status_effects": [],
                }
            )
        return enemies

    def _create_enemy_group(self):
        count = random.randint(1, 3)
        enemies = []
        enemy_data_db = _load_enemy_data()
        for i in range(count):
            base_enemy = Enemy.create_random_enemy()
            sprite = self._load_sprite(
                f"enemy_{base_enemy.name}.png",
                facing="right",
                tint=base_enemy.color,
                kind="enemy",
            )
            abilities = self._get_enemy_abilities(base_enemy.name, enemy_data_db)
            enemies.append(
                {
                    "name": base_enemy.name,
                    "hp": base_enemy.hp,
                    "max_hp": base_enemy.max_hp,
                    "mp": 0,
                    "max_mp": 0,
                    "attack": base_enemy.attack,
                    "defense": base_enemy.defense,
                    "speed": random.uniform(0.82, 1.18),
                    "level": random.randint(9, 14),
                    "vigor": base_enemy.attack + 4,
                    "magic": random.randint(8, 14),
                    "weapon_power": base_enemy.attack + 18,
                    "magic_defense": max(1, base_enemy.defense + random.randint(2, 6)),
                    "agility": random.randint(18, 28),
                    "weight": random.randint(10, 16),
                    "haste": False,
                    "slow": False,
                    "atb": random.uniform(0.0, 0.45),
                    "alive": True,
                    "sprite": sprite,
                    "x": 0,
                    "y": 0,
                    "w": sprite.get_width(),
                    "h": sprite.get_height(),
                    "abilities": abilities,
                    "status_effects": [],
                }
            )
        return enemies

    def _get_enemy_abilities(self, enemy_name, enemy_data_db):
        """enemies.json から敵の能力リストを取得"""
        for key, edata in enemy_data_db.items():
            if edata.get("name") == enemy_name:
                return edata.get("abilities", ["attack"])
        return ["attack"]

    # ------------------------------------------------------------------
    # スプライト関連（変更なし）
    # ------------------------------------------------------------------
    def _load_sprite(self, filename: str, facing: str, tint: tuple, kind: str):
        image_path = Path(__file__).resolve().parents[2] / "assets" / "images" / filename
        if image_path.exists():
            sprite = pygame.image.load(str(image_path)).convert_alpha()
            target_h = scaled(112) if kind == "enemy" else scaled(96)
            ratio = target_h / max(1, sprite.get_height())
            sprite = pygame.transform.smoothscale(
                sprite,
                (int(sprite.get_width() * ratio), target_h),
            )
        else:
            sprite = self._create_placeholder_sprite(facing=facing, tint=tint, kind=kind)
        if (facing == "left" and kind == "enemy") or (facing == "right" and kind == "ally"):
            sprite = pygame.transform.flip(sprite, True, False)
        return sprite

    def _create_placeholder_sprite(self, facing: str, tint: tuple, kind: str):
        width = scaled(108) if kind == "enemy" else scaled(86)
        height = scaled(118) if kind == "enemy" else scaled(96)
        surf = pygame.Surface((width, height), pygame.SRCALPHA)

        if kind == "enemy":
            pygame.draw.ellipse(surf, tint, (scaled(8), scaled(20), width - scaled(16), height - scaled(28)))
            eye_y = scaled(50)
            pygame.draw.circle(surf, WHITE, (scaled(38), eye_y), scaled(4))
            pygame.draw.circle(surf, WHITE, (width - scaled(38), eye_y), scaled(4))
            mouth = [(scaled(30), scaled(75)), (width // 2, scaled(87)), (width - scaled(30), scaled(75))]
            pygame.draw.polygon(surf, (30, 30, 30), mouth)
        else:
            pygame.draw.rect(surf, tint, (scaled(20), scaled(26), width - scaled(40), height - scaled(32)), border_radius=scaled(10))
            pygame.draw.circle(surf, (255, 224, 189), (width // 2, scaled(18)), scaled(12))
            arm_y = scaled(50)
            pygame.draw.line(surf, tint, (scaled(8), arm_y), (scaled(20), arm_y + scaled(10)), scaled(5))
            pygame.draw.line(surf, tint, (width - scaled(8), arm_y), (width - scaled(20), arm_y + scaled(10)), scaled(5))

        if facing == "left":
            surf = pygame.transform.flip(surf, True, False)
        return surf

    # ------------------------------------------------------------------
    # メッセージ / レイアウト
    # ------------------------------------------------------------------
    def _push_message(self, message: str):
        self.message_log.append(message)
        if len(self.message_log) > 4:
            self.message_log = self.message_log[-4:]

    def _layout_units(self):
        enemy_positions = self._calc_positions(
            count=len(self.enemies),
            side="left",
            start_x=scaled(130),
            start_y=scaled(140),
            col_gap=scaled(130),
            row_gap=scaled(110),
        )
        for idx, enemy in enumerate(self.enemies):
            enemy["x"], enemy["y"] = enemy_positions[idx]

        ally_positions = self._calc_positions(
            count=len(self.allies),
            side="right",
            start_x=SCREEN_WIDTH - scaled(240),
            start_y=scaled(190),
            col_gap=scaled(120),
            row_gap=scaled(92),
        )
        for idx, ally in enumerate(self.allies):
            ally["x"], ally["y"] = ally_positions[idx]

    def _calc_positions(self, count: int, side: str, start_x: int, start_y: int, col_gap: int, row_gap: int):
        positions = []
        cols = 2 if count >= 4 else 1
        rows = (count + cols - 1) // cols
        for i in range(count):
            col = i // rows if cols > 1 else 0
            row = i % rows
            x = start_x + col * col_gap
            y = start_y + row * row_gap
            if side == "right":
                x -= col * scaled(30)
            else:
                x += col * scaled(30)
            positions.append((x, y))
        return positions

    # ------------------------------------------------------------------
    # イベント処理
    # ------------------------------------------------------------------
    def handle_events(self, events: list):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.battle_state in ["victory", "defeat"]:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        # スクリプト経由のボスバトルはpop_sceneで戻る
                        if getattr(self.game, '_battle_from_script', False):
                            self.game._battle_from_script = False
                            self.game._last_battle_result = self.battle_state
                            self.game.pop_scene()
                        elif self.battle_state == "defeat":
                            self.game.change_scene("game_over")
                        else:
                            self.game.change_scene("map")
                    continue

                if self.active_actor_index is None:
                    continue

                if self.menu_state == "target_selection":
                    self._handle_target_selection(event)
                    continue

                if event.key == pygame.K_UP:
                    self._move_menu(-1)
                elif event.key == pygame.K_DOWN:
                    self._move_menu(1)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._play_menu_se("menu_confirm")
                    self._confirm_menu()
                elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self._play_menu_se("menu_cancel")
                    self._back_menu()

    def _handle_target_selection(self, event):
        """ターゲット選択モードのキー処理"""
        targets = self.enemies if self.target_side == "enemy" else self.allies
        alive_indices = [i for i, u in enumerate(targets) if u["alive"]]
        if not alive_indices:
            self._cancel_target_selection()
            return

        if event.key == pygame.K_UP:
            current_pos = alive_indices.index(self.target_index) if self.target_index in alive_indices else 0
            new_pos = (current_pos - 1) % len(alive_indices)
            self.target_index = alive_indices[new_pos]
            self._play_menu_se("menu_select")
        elif event.key == pygame.K_DOWN:
            current_pos = alive_indices.index(self.target_index) if self.target_index in alive_indices else 0
            new_pos = (current_pos + 1) % len(alive_indices)
            self.target_index = alive_indices[new_pos]
            self._play_menu_se("menu_select")
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._play_menu_se("menu_confirm")
            self._confirm_target_selection()
        elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self._play_menu_se("menu_cancel")
            self._cancel_target_selection()

    def _enter_target_selection(self, side: str, action_info: dict):
        """ターゲット選択モードに入る"""
        self.target_side = side
        self._pending_action = action_info
        targets = self.enemies if side == "enemy" else self.allies
        alive_indices = [i for i, u in enumerate(targets) if u["alive"]]
        self.target_index = alive_indices[0] if alive_indices else 0
        self.menu_state = "target_selection"

    def _confirm_target_selection(self):
        """ターゲット選択を確定して保留中のアクションを実行"""
        if self._pending_action is None:
            self._cancel_target_selection()
            return

        action = self._pending_action
        self._pending_action = None

        action_type = action.get("type")
        targets = self.enemies if self.target_side == "enemy" else self.allies
        target = targets[self.target_index]

        if action_type == "attack":
            self._execute_attack(target)
        elif action_type == "ability":
            self._execute_ability(action.get("ability"), target)
        elif action_type == "item":
            self._execute_item_on_target(action.get("item_entry"), target)

        # target_selectionから抜ける（_end_actor_actionで処理される）

    def _cancel_target_selection(self):
        """ターゲット選択をキャンセル"""
        self._pending_action = None
        self.menu_state = "main"
        self.menu_index = 0

    def _play_menu_se(self, se_id: str):
        self.audio_manager.play_se(se_id)

    def _move_menu(self, direction: int):
        options = self._current_options()
        if not options:
            return
        prev_index = self.menu_index
        self.menu_index = (self.menu_index + direction) % len(options)
        if self.menu_index != prev_index:
            self._play_menu_se("menu_select")

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

    def _draw_cursor(self, screen: pygame.Surface, x: int, y: int):
        if self.cursor_surface is not None:
            screen.blit(self.cursor_surface, (x, y))
            return
        fallback = self.small_font.render("▶", True, YELLOW)
        screen.blit(fallback, (x, y))

    # ------------------------------------------------------------------
    # メニューオプション
    # ------------------------------------------------------------------
    def _current_options(self):
        if self.menu_state == "main":
            return self.main_commands
        if self.menu_state == "ability":
            actor = self.allies[self.active_actor_index]
            abilities = get_available_abilities(actor, self.job_system)
            return [ability.name for ability in abilities]
        if self.menu_state == "item":
            usable = self._get_usable_items()
            return [f"{entry['name']} x{entry['count']}" for entry in usable]
        if self.menu_state == "target_selection":
            targets = self.enemies if self.target_side == "enemy" else self.allies
            return [t["name"] for t in targets if t["alive"]]
        return []

    def _get_usable_items(self):
        """ゲームのインベントリからバトルで使用可能なアイテムを取得"""
        usable = []
        inventory = getattr(self.game, "inventory", {})
        for item_id, count in inventory.items():
            if count <= 0:
                continue
            item = self.item_system.get_item(item_id)
            if item is None:
                continue
            # 消費アイテムのみバトルで使用可能
            if item.item_type != "consumable":
                continue
            # battle_use フラグがあるか確認
            if not item.raw_data.get("battle_use", False):
                continue
            usable.append({
                "item_id": item_id,
                "name": item.name,
                "count": count,
                "effect": item.raw_data.get("effect"),
                "power": item.raw_data.get("power"),
                "target": item.raw_data.get("target", "single_ally"),
            })
        return usable

    # ------------------------------------------------------------------
    # メニュー確定
    # ------------------------------------------------------------------
    def _confirm_menu(self):
        if self.menu_state == "main":
            self._confirm_main_command()
        elif self.menu_state == "ability":
            self._use_job_ability(self.menu_index)
        elif self.menu_state == "item":
            self._use_item(self.menu_index)

    def _back_menu(self):
        if self.menu_state in ["ability", "item"]:
            self.menu_state = "main"
            self.menu_index = 0
        elif self.menu_state == "target_selection":
            self._cancel_target_selection()

    def _confirm_main_command(self):
        command = self.main_commands[self.menu_index]
        actor = self.allies[self.active_actor_index]

        if command == "たたかう":
            weapon_data = self._get_actor_weapon_data(actor)
            if weapon_data.get("hits_all_enemies"):
                # 全体攻撃はターゲット選択不要
                self._execute_attack(None)
            else:
                self._enter_target_selection("enemy", {"type": "attack"})

        elif command == "ジョブ技":
            self.menu_state = "ability"
            self.menu_index = 0

        elif command == "アイテム":
            self.menu_state = "item"
            self.menu_index = 0

        elif command == "ぼうぎょ":
            actor["defending"] = True
            self._push_message(f"{actor['name']}は ぼうぎょのたいせい！")
            self._end_actor_action()

        elif command == "にげる":
            if random.random() < 0.55:
                self._push_message("うまく にげきれた！")
                if getattr(self.game, '_battle_from_script', False):
                    self.game._battle_from_script = False
                    self.game._last_battle_result = "escape"
                    self.game.pop_scene()
                else:
                    self.game.change_scene("map")
            else:
                self._push_message("にげられない！")
                self._end_actor_action()

    # ------------------------------------------------------------------
    # 攻撃実行（ターゲット選択後）
    # ------------------------------------------------------------------
    def _get_actor_weapon_data(self, actor: dict) -> dict:
        """アクターが装備中の武器データを取得（なければ空dict）"""
        weapon_id = actor.get("equipment", {}).get("weapon")
        if not weapon_id or not self.item_system:
            return {}
        item = self.item_system.get_item(weapon_id)
        return item.raw_data if item else {}

    def _execute_attack(self, target):
        """たたかうコマンドの実行（全体武器対応）"""
        actor = self.allies[self.active_actor_index]

        accuracy_mult = self.status_manager.get_accuracy_multiplier(actor)
        if accuracy_mult < 1.0 and random.random() > accuracy_mult:
            self._push_message(f"{actor['name']}のこうげき！ しかしミスした！")
            self._end_actor_action()
            return

        weapon_data = self._get_actor_weapon_data(actor)

        if weapon_data.get("hits_all_enemies"):
            # 全体攻撃: 全ての生存敵に75%ダメージ
            alive_enemies = [e for e in self.enemies if e["alive"]]
            weapon_name = weapon_data.get("name", "ブーメラン")
            self._push_message(f"{actor['name']}の{weapon_name}！")
            for enemy in alive_enemies:
                damage, is_critical = calculate_physical_damage(actor, enemy)
                damage = max(1, int(damage * 0.75))
                reduction = self.status_manager.get_damage_reduction_rate(enemy)
                if reduction > 0:
                    damage = max(1, int(damage * (1.0 - reduction)))
                self._deal_damage(enemy, damage, side="enemy")
                if is_critical:
                    self._push_message(f"{enemy['name']}にかいしん！")
                self.status_manager.on_physical_attack(enemy)
        elif target is not None:
            # 通常単体攻撃（target が None の場合は何もしない安全ガード）
            damage, is_critical = calculate_physical_damage(actor, target)
            reduction = self.status_manager.get_damage_reduction_rate(target)
            if reduction > 0:
                damage = max(1, int(damage * (1.0 - reduction)))
            self._deal_damage(target, damage, side="enemy")
            self.status_manager.on_physical_attack(target)
            if is_critical:
                self._push_message(f"{actor['name']}のかいしん！")
            else:
                self._push_message(f"{actor['name']}のこうげき！")

        self._end_actor_action()

    # ------------------------------------------------------------------
    # アイテム使用（データ駆動）
    # ------------------------------------------------------------------
    def _use_item(self, index: int):
        """アイテムメニューからアイテムを選択"""
        usable = self._get_usable_items()
        if index < 0 or index >= len(usable):
            return

        entry = usable[index]
        if entry["count"] <= 0:
            self._push_message(f"{entry['name']}がない！")
            return

        # ターゲットが必要なアイテムは選択に入る
        target_type = entry.get("target", "single_ally")
        if target_type == "single_ally":
            self._enter_target_selection("ally", {"type": "item", "item_entry": entry})
        else:
            # 自分に使う
            self._execute_item_on_target(entry, self.allies[self.active_actor_index])

    def _execute_item_on_target(self, entry, target):
        """アイテム効果をターゲットに適用"""
        actor = self.allies[self.active_actor_index]
        item_id = entry["item_id"]
        effect = entry.get("effect")
        power = entry.get("power")

        # インベントリから消費
        inv = self.game.inventory
        if inv.get(item_id, 0) <= 0:
            self._push_message(f"{entry['name']}がない！")
            return
        inv[item_id] -= 1
        if inv[item_id] <= 0:
            del inv[item_id]

        if effect == "heal":
            if isinstance(power, (list, tuple)):
                spell_power = int((power[0] + power[1]) / 2)
            elif isinstance(power, (int, float)):
                spell_power = int(power)
            else:
                spell_power = 45
            heal = calculate_heal_amount(actor, spell_power=spell_power, variance=(0.9, 1.0))
            before = target["hp"]
            target["hp"] = min(target["max_hp"], target["hp"] + heal)
            actual = target["hp"] - before
            self._add_popup(target, f"+{actual}", GREEN)
            self._push_message(f"{actor['name']}は {entry['name']} を使った！")

        elif effect == "restore_mp":
            if isinstance(power, (list, tuple)):
                mp_heal = random.randint(power[0], power[1])
            elif isinstance(power, (int, float)):
                mp_heal = int(power)
            else:
                mp_heal = 20
            before = target["mp"]
            target["mp"] = min(target["max_mp"], target["mp"] + mp_heal)
            actual = target["mp"] - before
            self._add_popup(target, f"+{actual}MP", YELLOW)
            self._push_message(f"{actor['name']}は {entry['name']} を使った！")

        elif effect == "cure_poison":
            self.status_manager.remove_effect(target, "poison")
            self._push_message(f"{actor['name']}は {entry['name']} を使った！ 毒が治った！")

        elif effect == "cure_blind":
            self.status_manager.remove_effect(target, "blind")
            self._push_message(f"{actor['name']}は {entry['name']} を使った！ 暗闇が治った！")

        elif effect == "cure_sleep":
            self.status_manager.remove_effect(target, "sleep")
            self._push_message(f"{actor['name']}は {entry['name']} を使った！ 目が覚めた！")

        elif effect == "revive":
            if not target["alive"]:
                target["alive"] = True
                target["hp"] = target["max_hp"]
                self._add_popup(target, "復活！", GREEN)
                self._push_message(f"{actor['name']}は {entry['name']} を使った！ {target['name']}が復活した！")
            else:
                self._push_message(f"{target['name']}はまだ生きている！")

        else:
            self._push_message(f"{actor['name']}は {entry['name']} を使った！")

        self._end_actor_action()

    # ------------------------------------------------------------------
    # ジョブ技使用
    # ------------------------------------------------------------------
    def _use_job_ability(self, index: int):
        actor = self.allies[self.active_actor_index]
        abilities = get_available_abilities(actor, self.job_system)

        if index < 0 or index >= len(abilities):
            return

        ability = abilities[index]

        # MP確認
        if actor["mp"] < ability.mp_cost:
            self._push_message(f"{actor['name']}は MPがたりない！")
            return

        # ターゲットタイプに応じてターゲット選択に入るか直接実行
        if ability.target_type == "single_enemy":
            self._enter_target_selection("enemy", {"type": "ability", "ability": ability})
        elif ability.target_type == "single_ally":
            self._enter_target_selection("ally", {"type": "ability", "ability": ability})
        elif ability.target_type == "all_enemies":
            self._execute_ability_all_enemies(ability)
        elif ability.target_type == "self":
            self._execute_ability_self(ability)
        elif ability.target_type == "all_allies":
            self._execute_ability_all_allies(ability)

    def _execute_ability(self, ability, target):
        """単体対象アビリティの実行（ターゲット選択後）"""
        actor = self.allies[self.active_actor_index]

        # MP消費
        actor["mp"] -= ability.mp_cost

        power = int((ability.power[0] + ability.power[1]) / 2) if isinstance(ability.power, (list, tuple)) else ability.power

        if ability.target_type == "single_enemy":
            if ability.effect in ["physical_damage", "physical_damage_multi", "powered_attack", "armor_ignore_damage", "holy_damage"]:
                if ability.type == "attack" or ability.effect in ["powered_attack", "armor_ignore_damage", "holy_damage"]:
                    damage = calculate_physical_damage(actor, target)
                    if isinstance(damage, tuple):
                        damage = damage[0]
                    damage = int(damage * (power / 10.0))

                    # プロテスによるダメージ軽減
                    reduction = self.status_manager.get_damage_reduction_rate(target)
                    if reduction > 0:
                        damage = max(1, int(damage * (1.0 - reduction)))

                    self._deal_damage(target, damage, side="enemy")
                    # 物理攻撃による睡眠解除
                    self.status_manager.on_physical_attack(target)
                    self._push_message(f"{actor['name']}の{ability.name}！")
                else:
                    damage = calculate_magic_damage(actor, target, spell_power=power)
                    self._deal_damage(target, damage, side="enemy")
                    self._push_message(f"{actor['name']}の{ability.name}！")
            elif ability.effect in ["physical_damage_aoe", "physical_dance_aoe", "summon_fire", "summon_ice"]:
                for enemy in self.enemies:
                    if not enemy["alive"]:
                        continue
                    damage = calculate_magic_damage(actor, enemy, spell_power=power)
                    self._deal_damage(enemy, damage, side="enemy")
                self._push_message(f"{actor['name']}の{ability.name}！")
            else:
                # 未知のエフェクト -> 魔法ダメージとして処理
                damage = calculate_magic_damage(actor, target, spell_power=power)
                self._deal_damage(target, damage, side="enemy")
                self._push_message(f"{actor['name']}の{ability.name}！")

        elif ability.target_type == "single_ally":
            if ability.effect == "heal":
                heal = calculate_heal_amount(actor, spell_power=power)
                before = target["hp"]
                target["hp"] = min(target["max_hp"], target["hp"] + heal)
                actual = target["hp"] - before
                self._add_popup(target, f"+{actual}", GREEN)
                self._push_message(f"{actor['name']}の{ability.name}！ HPが{actual}回復")
            elif ability.effect == "full_heal":
                actual = target["max_hp"] - target["hp"]
                target["hp"] = target["max_hp"]
                self._add_popup(target, f"+{actual}", GREEN)
                self._push_message(f"{actor['name']}の{ability.name}！ HPが{actual}回復")
            elif ability.effect == "increase_defense":
                # プロテスを状態異常として付与
                self.status_manager.apply_effect(target, "protect", duration=ability.raw_data.get("duration", 5))
                self._push_message(f"{actor['name']}の{ability.name}！ {target['name']}のぼうぎょりょくアップ！")

        self._end_actor_action()

    def _execute_ability_all_enemies(self, ability):
        """全敵対象アビリティの実行"""
        actor = self.allies[self.active_actor_index]
        actor["mp"] -= ability.mp_cost
        power = int((ability.power[0] + ability.power[1]) / 2) if isinstance(ability.power, (list, tuple)) else ability.power
        for enemy in self.enemies:
            if not enemy["alive"]:
                continue
            damage = calculate_magic_damage(actor, enemy, spell_power=power)
            self._deal_damage(enemy, damage, side="enemy")
        self._push_message(f"{actor['name']}の{ability.name}！")
        self._end_actor_action()

    def _execute_ability_self(self, ability):
        """自身対象アビリティの実行"""
        actor = self.allies[self.active_actor_index]
        actor["mp"] -= ability.mp_cost
        if ability.effect == "shield_stance":
            actor["defending"] = True
            self._push_message(f"{actor['name']}の{ability.name}！")
        else:
            self._push_message(f"{actor['name']}の{ability.name}！")
        self._end_actor_action()

    def _execute_ability_all_allies(self, ability):
        """全味方対象アビリティの実行"""
        actor = self.allies[self.active_actor_index]
        actor["mp"] -= ability.mp_cost
        if ability.effect == "increase_evasion":
            self._push_message(f"{actor['name']}の{ability.name}！ 回避率アップ！")
        elif ability.effect == "holy_barrier":
            for ally in self.allies:
                if ally["alive"]:
                    self.status_manager.apply_effect(ally, "protect", duration=ability.raw_data.get("duration", 4))
            self._push_message(f"{actor['name']}の{ability.name}！ 防御力アップ！")
        else:
            self._push_message(f"{actor['name']}の{ability.name}！")
        self._end_actor_action()

    # ------------------------------------------------------------------
    # ダメージ処理
    # ------------------------------------------------------------------
    def _deal_damage(self, target: dict, damage: int, side: str):
        # Note: damage reduction (Protect/Shell) is applied by the caller
        # before invoking _deal_damage. Do NOT apply it again here.
        target["hp"] -= damage
        self._add_popup(target, str(damage), RED)

        if target["hp"] <= 0:
            target["hp"] = 0
            target["alive"] = False
            self._push_message(f"{target['name']}をたおした！")
            if side == "enemy":
                bestiary = getattr(self.game, "bestiary", None)
                if bestiary is not None:
                    name = target.get("name", "")
                    if name:
                        bestiary["enemies_defeated"][name] = bestiary["enemies_defeated"].get(name, 0) + 1

    def _add_popup(self, unit: dict, text: str, color: tuple):
        popup_x = unit["x"] + unit["w"] // 2
        popup_y = unit["y"] - scaled(10)
        self.damage_popups.append({"x": popup_x, "y": popup_y, "text": text, "color": color, "timer": 45})

    # ------------------------------------------------------------------
    # ターン管理
    # ------------------------------------------------------------------
    def _end_actor_action(self):
        if self.active_actor_index is None:
            return
        actor = self.allies[self.active_actor_index]
        actor["atb"] = 0.0

        if self.active_actor_index in self.ready_allies:
            self.ready_allies.remove(self.active_actor_index)

        self.active_actor_index = None
        self.menu_state = "none"
        self.menu_index = 0
        self._pending_action = None

    def _start_next_ready_ally(self):
        if self.active_actor_index is not None:
            return
        while self.ready_allies:
            idx = self.ready_allies.pop(0)
            ally = self.allies[idx]
            if not ally["alive"]:
                continue

            # ターン開始時の状態異常処理（毒ダメージ等）
            poison_dmg, status_msg = self.status_manager.on_turn_start(ally)
            if poison_dmg > 0:
                ally["hp"] = max(0, ally["hp"] - poison_dmg)
                self._add_popup(ally, str(poison_dmg), (128, 0, 128))
                if status_msg:
                    self._push_message(status_msg)
                if ally["hp"] <= 0:
                    ally["alive"] = False
                    self._push_message(f"{ally['name']}はたおれた！")
                    continue

            # 行動制限チェック（睡眠/石化/ストップ）
            restrictions = self.status_manager.get_action_restrictions(ally)
            if not restrictions["can_act"]:
                self._push_message(f"{ally['name']}は行動できない！")
                ally["atb"] = 0.0
                continue
            if not restrictions["can_choose_command"]:
                # 混乱チェック
                if self.status_manager.has_effect(ally, "confuse"):
                    self._execute_confusion_action(idx)
                else:
                    self._push_message(f"{ally['name']}は行動できない！")
                    ally["atb"] = 0.0
                continue

            self.active_actor_index = idx
            self.menu_state = "main"
            self.menu_index = 0
            return

    def _execute_confusion_action(self, ally_index):
        """混乱状態のランダム行動"""
        ally = self.allies[ally_index]
        action = get_random_action(ally)

        if action == "attack_enemy":
            alive_enemies = [e for e in self.enemies if e["alive"]]
            if alive_enemies:
                target = random.choice(alive_enemies)
                damage, _ = calculate_physical_damage(ally, target)
                self._deal_damage(target, damage, side="enemy")
                self.status_manager.on_physical_attack(target)
                self._push_message(f"{ally['name']}は混乱して敵をこうげき！")
        elif action == "attack_ally":
            alive_allies = [a for a in self.allies if a["alive"]]
            if alive_allies:
                target = random.choice(alive_allies)
                damage, _ = calculate_physical_damage(ally, target)
                if target["defending"]:
                    damage = max(1, damage // 2)
                    target["defending"] = False
                self._deal_damage(target, damage, side="ally")
                self.status_manager.on_physical_attack(target)
                self._push_message(f"{ally['name']}は混乱して味方をこうげき！")
        else:
            self._push_message(f"{ally['name']}は混乱している...")

        ally["atb"] = 0.0

    # ------------------------------------------------------------------
    # ATB更新（StatusEffectManager統合）
    # ------------------------------------------------------------------
    def _update_atb(self):
        for index, ally in enumerate(self.allies):
            if not ally["alive"]:
                continue
            if self.active_actor_index == index:
                continue

            # 行動制限チェック: ストップ中はATBも停止
            restrictions = self.status_manager.get_action_restrictions(ally)
            if not restrictions["can_act"]:
                continue

            # StatusEffectManagerからATB倍率を取得
            status_mult = self.status_manager.get_atb_multiplier(ally)

            increment = calculate_atb_increment(
                agility=ally["agility"],
                weight=ally["weight"],
                speed_coeff=ally["speed"],
                status_multiplier=status_mult,
            )
            ally["atb"] = advance_atb(ally["atb"], increment)
            if ally["atb"] >= 1.0 and index not in self.ready_allies:
                self.ready_allies.append(index)

        for enemy in self.enemies:
            if not enemy["alive"]:
                continue

            # 敵の行動制限チェック
            restrictions = self.status_manager.get_action_restrictions(enemy)
            if not restrictions["can_act"]:
                continue

            status_mult = self.status_manager.get_atb_multiplier(enemy)

            increment = calculate_atb_increment(
                agility=enemy["agility"],
                weight=enemy["weight"],
                speed_coeff=enemy["speed"],
                status_multiplier=status_mult,
            )
            enemy["atb"] = advance_atb(enemy["atb"], increment)
            if enemy["atb"] >= 1.0:
                # 敵ターン開始時の状態異常処理
                poison_dmg, status_msg = self.status_manager.on_turn_start(enemy)
                if poison_dmg > 0:
                    enemy["hp"] = max(0, enemy["hp"] - poison_dmg)
                    self._add_popup(enemy, str(poison_dmg), (128, 0, 128))
                    if status_msg:
                        self._push_message(status_msg)
                    if enemy["hp"] <= 0:
                        enemy["alive"] = False
                        self._push_message(f"{enemy['name']}をたおした！")
                        enemy["atb"] = 0.0
                        continue

                # 混乱チェック
                if self.status_manager.has_effect(enemy, "confuse"):
                    self._execute_enemy_confusion(enemy)
                else:
                    self._enemy_act(enemy)
                enemy["atb"] = 0.0

    # ------------------------------------------------------------------
    # 敵AI（能力使用対応）
    # ------------------------------------------------------------------
    def _enemy_act(self, enemy: dict):
        """敵の行動: 能力リストからランダム加重選択"""
        abilities = enemy.get("abilities", ["attack"])

        # 能力をランダムに選択（通常攻撃の重みを高くする）
        weights = []
        for ab in abilities:
            if ab == "attack":
                weights.append(3)  # 通常攻撃は重み3
            else:
                weights.append(1)  # 特殊技は重み1

        chosen = random.choices(abilities, weights=weights, k=1)[0]

        if chosen == "attack":
            self._enemy_physical_attack(enemy)
        else:
            self._enemy_use_ability(enemy, chosen)

    def _enemy_physical_attack(self, enemy: dict):
        """敵の通常物理攻撃"""
        alive_allies = [i for i, a in enumerate(self.allies) if a["alive"]]
        if not alive_allies:
            return
        target_index = random.choice(alive_allies)
        target = self.allies[target_index]

        # 暗闇による命中率低下
        accuracy_mult = self.status_manager.get_accuracy_multiplier(enemy)
        if accuracy_mult < 1.0 and random.random() > accuracy_mult:
            self._push_message(f"{enemy['name']}のこうげき！ しかしミスした！")
            return

        damage, _ = calculate_physical_damage(enemy, target)
        if target["defending"]:
            damage = max(1, damage // 2)
            target["defending"] = False

        # プロテスによるダメージ軽減
        reduction = self.status_manager.get_damage_reduction_rate(target)
        if reduction > 0:
            damage = max(1, int(damage * (1.0 - reduction)))

        self._deal_damage(target, damage, side="ally")
        # 物理攻撃による睡眠解除
        self.status_manager.on_physical_attack(target)
        self._push_message(f"{enemy['name']}のこうげき！")

    def _enemy_use_ability(self, enemy: dict, ability_id: str):
        """敵が特殊能力を使用"""
        # 能力名のマッピング（enemies.jsonのIDを日本語名に）
        ability_names = {
            "poison_spit": "どくの息",
            "slash": "斬撃",
            "power_attack": "パワーアタック",
            "wing_buffet": "つばさ打ち",
            "bite": "かみつき",
            "fire_breath": "火炎のいき",
            "tail_swing": "しっぽ",
            "bone_attack": "骨投げ",
            "curse_hand": "のろいの手",
            "scream": "おたけび",
            "life_drain": "吸収",
        }
        ability_name = ability_names.get(ability_id, ability_id)

        alive_allies = [i for i, a in enumerate(self.allies) if a["alive"]]
        if not alive_allies:
            return
        target_index = random.choice(alive_allies)
        target = self.allies[target_index]

        # 能力ごとの効果
        if ability_id == "poison_spit":
            # 毒の息: ダメージ + 毒付与
            damage = max(1, int(enemy["attack"] * 0.6))
            self._deal_damage(target, damage, side="ally")
            success, msg = self.status_manager.apply_effect(target, "poison")
            self._push_message(f"{enemy['name']}の{ability_name}！")
            if success and msg:
                self._push_message(msg)

        elif ability_id in ["slash", "power_attack", "bone_attack", "tail_swing", "wing_buffet", "bite"]:
            # 物理系能力: 通常攻撃の倍率変更版
            multiplier = {
                "slash": 1.0,
                "power_attack": 1.4,
                "bone_attack": 1.1,
                "tail_swing": 1.3,
                "wing_buffet": 0.8,
                "bite": 1.2,
            }.get(ability_id, 1.0)
            damage, _ = calculate_physical_damage(enemy, target)
            damage = max(1, int(damage * multiplier))
            if target["defending"]:
                damage = max(1, damage // 2)
                target["defending"] = False

            reduction = self.status_manager.get_damage_reduction_rate(target)
            if reduction > 0:
                damage = max(1, int(damage * (1.0 - reduction)))

            self._deal_damage(target, damage, side="ally")
            self.status_manager.on_physical_attack(target)
            self._push_message(f"{enemy['name']}の{ability_name}！")

        elif ability_id == "fire_breath":
            # 火炎のいき: 全体魔法ダメージ
            spell_power = max(1, int(enemy.get("magic", 10) * 1.5))
            for idx in alive_allies:
                ally = self.allies[idx]
                damage = calculate_magic_damage(enemy, ally, spell_power=spell_power)
                self._deal_damage(ally, damage, side="ally")
            self._push_message(f"{enemy['name']}の{ability_name}！")

        elif ability_id == "curse_hand":
            # のろいの手: ダメージ + スロウ付与
            damage = max(1, int(enemy["attack"] * 0.7))
            self._deal_damage(target, damage, side="ally")
            success, msg = self.status_manager.apply_effect(target, "slow")
            self._push_message(f"{enemy['name']}の{ability_name}！")
            if success and msg:
                self._push_message(msg)

        elif ability_id == "scream":
            # おたけび: 睡眠付与（ダメージなし）
            success, msg = self.status_manager.apply_effect(target, "sleep")
            self._push_message(f"{enemy['name']}の{ability_name}！")
            if msg:
                self._push_message(msg)

        elif ability_id == "life_drain":
            # 吸収: ダメージを与えてHP回復
            damage = max(1, int(enemy.get("magic", 10) * 1.2))
            self._deal_damage(target, damage, side="ally")
            heal = max(1, damage // 2)
            enemy["hp"] = min(enemy["max_hp"], enemy["hp"] + heal)
            self._add_popup(enemy, f"+{heal}", GREEN)
            self._push_message(f"{enemy['name']}の{ability_name}！ HPを吸収した！")

        else:
            # 未定義の能力 -> 通常攻撃にフォールバック
            self._enemy_physical_attack(enemy)

    def _execute_enemy_confusion(self, enemy: dict):
        """混乱した敵のランダム行動"""
        action = get_random_action(enemy)

        if action == "attack_enemy":
            # 敵が味方の敵（=プレイヤーパーティ）を攻撃 -> 通常通り
            self._enemy_physical_attack(enemy)
            self._push_message(f"{enemy['name']}は混乱している！")
        elif action == "attack_ally":
            # 敵が自分の味方（=他の敵）を攻撃
            alive_enemies = [e for e in self.enemies if e["alive"] and e is not enemy]
            if alive_enemies:
                target = random.choice(alive_enemies)
                damage, _ = calculate_physical_damage(enemy, target)
                self._deal_damage(target, damage, side="enemy")
                self.status_manager.on_physical_attack(target)
                self._push_message(f"{enemy['name']}は混乱して味方をこうげき！")
            else:
                self._push_message(f"{enemy['name']}は混乱している...")
        else:
            self._push_message(f"{enemy['name']}は混乱している...")

    # ------------------------------------------------------------------
    # ポップアップ / バトル結果
    # ------------------------------------------------------------------
    def _update_popups(self):
        for popup in self.damage_popups:
            popup["y"] -= 1.2
            popup["timer"] -= 1
        self.damage_popups = [popup for popup in self.damage_popups if popup["timer"] > 0]

    def _check_battle_result(self):
        if self.battle_state != "running":
            return

        if not any(enemy["alive"] for enemy in self.enemies):
            self.battle_state = "victory"
            if not self.victory_bgm_played:
                self.audio_manager.play_bgm("victory", loop=0, fade_in=200)
                self.victory_bgm_played = True
            self._process_victory_rewards()
            self._push_message("しょうり！ Enterでフィールドへ")
            return

        if not any(ally["alive"] for ally in self.allies):
            self.battle_state = "defeat"
            self._push_message("ぜんめつ... Enterでフィールドへ")

    def _process_victory_rewards(self):
        """バトル勝利時のEXP獲得・レベルアップ処理"""
        total_exp = None
        job_points_total = 0

        if self.encounter_rewards:
            total_exp = self.encounter_rewards.get("exp")
            job_points_total = self.encounter_rewards.get("job_points", 0)

        rewards = apply_battle_rewards(
            self.allies,
            self.enemies,
            self.leveling_system,
            total_exp_override=total_exp,
        )

        alive_allies = [ally for ally in self.allies if ally.get("alive")]
        jp_per_member = job_points_total // max(1, len(alive_allies))
        if jp_per_member > 0:
            for ally in alive_allies:
                ally["job_points"] = ally.get("job_points", 0) + jp_per_member

        reward_apply_result = self.encounter_manager.resolve_battle_rewards(
            self.game,
            rewards_data=self.encounter_rewards,
        )
        total_gold = reward_apply_result.get("gold", 0)
        obtained_drops = reward_apply_result.get("obtained_drops", [])

        self._sync_party_to_game()
        self.last_reward_result = {
            "exp_per_member": rewards.get("exp_per_member", 0),
            "gold": total_gold,
            "jp_per_member": jp_per_member,
            "drops": obtained_drops,
        }

        if rewards.get("exp_per_member", 0) > 0:
            self._push_message(f"EXP {rewards['exp_per_member']} を獲得！")
        if total_gold > 0:
            self._push_message(f"{total_gold}ギル を獲得！")
        if jp_per_member > 0:
            self._push_message(f"JP {jp_per_member} を獲得！")
        if obtained_drops:
            drop_labels = ", ".join(f"{drop['item_name']}x{drop['amount']}" for drop in obtained_drops)
            self._push_message(f"ドロップ: {drop_labels}")

        # レベルアップ情報をメッセージログに追加
        for level_up in rewards.get("level_ups", []):
            self._push_message(f"{level_up['name']}のレベルが{level_up['new_level']}になった！")

    def _sync_party_to_game(self):
        self.game.party = [
            {
                "name": ally["name"],
                "level": ally["level"],
                "current_exp": ally.get("current_exp", 0),
                "max_hp": ally["max_hp"],
                "hp": ally["hp"],
                "max_mp": ally["max_mp"],
                "mp": ally["mp"],
                "attack": ally["attack"],
                "defense": ally["defense"],
                "magic": ally.get("magic", 0),
                "job_points": ally.get("job_points", 0),
                "job_mastery": ally.get("job_mastery", 0),
                "current_job": ally.get("current_job", "freelancer"),
                "base_max_hp": ally.get("base_max_hp", ally["max_hp"]),
                "base_max_mp": ally.get("base_max_mp", ally["max_mp"]),
                "base_attack": ally.get("base_attack", ally["attack"]),
                "base_defense": ally.get("base_defense", ally["defense"]),
                "base_magic": ally.get("base_magic", ally.get("magic", 0)),
                "equipment": ally.get("equipment", {"weapon": None, "head": None, "body": None, "accessory1": None, "accessory2": None}),
            }
            for ally in self.allies
        ]

    # ------------------------------------------------------------------
    # メインループ
    # ------------------------------------------------------------------
    def update(self):
        self._layout_units()

        if self.battle_state == "running":
            self._update_atb()
            self._start_next_ready_ally()
            self._check_battle_result()

        self._update_popups()

    # ------------------------------------------------------------------
    # 描画
    # ------------------------------------------------------------------
    def _draw_battle_bg(self, screen: pygame.Surface):
        screen.fill((10, 20, 62))
        field_rect = pygame.Rect(scaled(20), scaled(20), SCREEN_WIDTH - scaled(40), SCREEN_HEIGHT - scaled(260))
        pygame.draw.rect(screen, (18, 40, 98), field_rect, border_radius=scaled(7))
        pygame.draw.rect(screen, WHITE, field_rect, 2, border_radius=scaled(7))

    def _draw_units(self, screen: pygame.Surface):
        for enemy in self.enemies:
            if not enemy["alive"]:
                continue
            screen.blit(enemy["sprite"], (enemy["x"], enemy["y"]))

        for ally in self.allies:
            if not ally["alive"]:
                continue
            screen.blit(ally["sprite"], (ally["x"], ally["y"]))

        # ターゲット選択中のカーソル表示
        if self.menu_state == "target_selection":
            targets = self.enemies if self.target_side == "enemy" else self.allies
            if 0 <= self.target_index < len(targets):
                target = targets[self.target_index]
                if target["alive"]:
                    cursor_x = target["x"] + target["w"] // 2 - scaled(8)
                    cursor_y = target["y"] - scaled(20)
                    self._draw_cursor(screen, cursor_x, cursor_y)

    def _draw_enemy_status(self, screen: pygame.Surface):
        panel = pygame.Rect(scaled(26), SCREEN_HEIGHT - scaled(250), scaled(460), scaled(100))
        pygame.draw.rect(screen, (22, 32, 80), panel, border_radius=scaled(5))
        pygame.draw.rect(screen, WHITE, panel, 2, border_radius=scaled(5))

        y = panel.y + scaled(10)
        for enemy in self.enemies:
            if not enemy["alive"]:
                continue
            name_text = self.small_font.render(enemy["name"], True, WHITE)
            screen.blit(name_text, (panel.x + scaled(12), y))

            bar_x = panel.x + scaled(140)
            bar_y = y + scaled(4)
            bar_w = scaled(280)
            bar_h = scaled(14)
            ratio = enemy["hp"] / enemy["max_hp"]
            pygame.draw.rect(screen, (30, 30, 30), (bar_x, bar_y, bar_w, bar_h), border_radius=scaled(3))
            pygame.draw.rect(screen, RED, (bar_x, bar_y, int(bar_w * ratio), bar_h), border_radius=scaled(3))
            pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_w, bar_h), 1, border_radius=scaled(3))
            y += scaled(28)

    def _draw_party_status(self, screen: pygame.Surface):
        panel = pygame.Rect(scaled(500), SCREEN_HEIGHT - scaled(250), SCREEN_WIDTH - scaled(520), scaled(100))
        pygame.draw.rect(screen, (22, 32, 80), panel, border_radius=scaled(5))
        pygame.draw.rect(screen, WHITE, panel, 2, border_radius=scaled(5))

        row_h = scaled(30)
        for i, ally in enumerate(self.allies):
            y = panel.y + scaled(8) + i * row_h
            color = YELLOW if i == self.active_actor_index else WHITE
            if not ally["alive"]:
                color = (130, 130, 130)

            line = f"{ally['name']}  HP {ally['hp']:>3}/{ally['max_hp']:<3}  MP {ally['mp']:>2}/{ally['max_mp']:<2}"
            text = self.small_font.render(line, True, color)
            screen.blit(text, (panel.x + scaled(10), y))

            atb_x = panel.x + panel.w - scaled(170)
            atb_y = y + scaled(6)
            atb_w = scaled(150)
            atb_h = scaled(12)
            pygame.draw.rect(screen, (28, 28, 28), (atb_x, atb_y, atb_w, atb_h), border_radius=scaled(3))
            pygame.draw.rect(screen, GREEN, (atb_x, atb_y, int(atb_w * ally["atb"]), atb_h), border_radius=scaled(3))
            pygame.draw.rect(screen, WHITE, (atb_x, atb_y, atb_w, atb_h), 1, border_radius=scaled(3))

    def _draw_message_window(self, screen: pygame.Surface):
        msg_rect = pygame.Rect(scaled(20), SCREEN_HEIGHT - scaled(145), SCREEN_WIDTH - scaled(40), scaled(70))
        pygame.draw.rect(screen, (20, 30, 78), msg_rect, border_radius=scaled(5))
        pygame.draw.rect(screen, WHITE, msg_rect, 2, border_radius=scaled(5))

        for i, message in enumerate(self.message_log[-2:]):
            text = self.small_font.render(message, True, WHITE)
            screen.blit(text, (msg_rect.x + scaled(14), msg_rect.y + scaled(10) + i * scaled(24)))

    def _draw_command_window(self, screen: pygame.Surface):
        if self.menu_state == "none" or self.active_actor_index is None:
            return
        if self.menu_state == "target_selection":
            # ターゲット選択中はコマンドウィンドウにターゲット名を表示
            cmd_rect = pygame.Rect(SCREEN_WIDTH - scaled(360), SCREEN_HEIGHT - scaled(145), scaled(340), scaled(135))
            pygame.draw.rect(screen, (20, 30, 78), cmd_rect, border_radius=scaled(5))
            pygame.draw.rect(screen, WHITE, cmd_rect, 2, border_radius=scaled(5))

            targets = self.enemies if self.target_side == "enemy" else self.allies
            alive_targets = [(i, t) for i, t in enumerate(targets) if t["alive"]]
            for draw_i, (idx, target) in enumerate(alive_targets):
                color = YELLOW if idx == self.target_index else WHITE
                x = cmd_rect.x + scaled(16)
                y = cmd_rect.y + scaled(10) + draw_i * scaled(24)
                label = self.small_font.render(target["name"], True, color)
                screen.blit(label, (x, y))
                if idx == self.target_index:
                    self._draw_cursor(screen, x - scaled(14), y + scaled(2))
            return

        cmd_rect = pygame.Rect(SCREEN_WIDTH - scaled(360), SCREEN_HEIGHT - scaled(145), scaled(340), scaled(135))
        pygame.draw.rect(screen, (20, 30, 78), cmd_rect, border_radius=scaled(5))
        pygame.draw.rect(screen, WHITE, cmd_rect, 2, border_radius=scaled(5))

        options = self._current_options()
        for i, option in enumerate(options):
            color = YELLOW if i == self.menu_index else WHITE
            x = cmd_rect.x + scaled(16)
            y = cmd_rect.y + scaled(10) + i * scaled(24)
            label = self.small_font.render(option, True, color)
            screen.blit(label, (x, y))
            if i == self.menu_index:
                self._draw_cursor(screen, x - scaled(14), y + scaled(2))

    def _draw_popups(self, screen: pygame.Surface):
        for popup in self.damage_popups:
            text = self.font.render(popup["text"], True, popup["color"])
            screen.blit(text, (popup["x"] - text.get_width() // 2, int(popup["y"])))

    def draw(self, screen: pygame.Surface):
        self._draw_battle_bg(screen)
        self._draw_units(screen)
        self._draw_enemy_status(screen)
        self._draw_party_status(screen)
        self._draw_message_window(screen)
        self._draw_command_window(screen)
        self._draw_popups(screen)

        if self.battle_state == "victory":
            text = self.font.render("Victory! Enterでフィールドへ", True, YELLOW)
            screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, scaled(70)))
        elif self.battle_state == "defeat":
            text = self.font.render("Defeat... Enterでフィールドへ", True, RED)
            screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, scaled(70)))

    def start_battle_with_group(self, enemy_group, rewards_data=None):
        """
        敵グループを使用して戦闘を開始

        Args:
            enemy_group (EnemyGroup): 敵グループオブジェクト
            rewards_data (dict | None): 事前計算済み報酬データ
        """
        self.pending_encounter_group = enemy_group
        self.encounter_rewards = rewards_data or self.encounter_manager.build_encounter_rewards(enemy_group)

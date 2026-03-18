"""
ゲームのメインクラス
"""

import logging
import pygame
from src.entities.character_data import CharacterDataManager
from src.scenes.title_scene import TitleScene
from src.scenes.map_scene import MapScene
from src.scenes.battle_scene import BattleScene
from src.scenes.menu_scene import MenuScene
from src.constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GAME_TITLE
from src.scripting.engine import ScriptEngine
from src.scripting.api import ScriptAPI
from src.world.world_state_manager import WorldStateManager
from src.quest.quest_manager import QuestManager
from src.quest.quest_log_ui import QuestLogUI
from src.scenes.shop_scene import ShopScene
from src.world.treasure import TreasureManager
from src.world.gimmick_manager import GimmickManager
from src.world.door_manager import DoorManager

logger = logging.getLogger(__name__)


class Game:
    """ゲームのメインクラス"""

    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.character_data = CharacterDataManager()
        self.gold = 500
        self.inventory = {
            "potion": 5,
            "ether": 3,
            "sword_mythril": 1,
            "helmet_mythril": 1,
            "armor_white": 1,
            "ring_power": 1,
        }

        # スクリプトエンジン・ワールドステート・クエスト管理
        self.world_state_manager = WorldStateManager()
        self.script_engine = ScriptEngine()
        self.script_api = ScriptAPI(
            engine=self.script_engine,
            game=self,
            world_state_manager=self.world_state_manager,
        )
        self.quest_manager = QuestManager(
            world_state_manager=self.world_state_manager,
            script_engine=self.script_engine,
            script_api=self.script_api,
            game=self,
        )
        # Wire quest manager into script API
        self.script_api.quest_manager = self.quest_manager
        self.quest_log_ui = QuestLogUI(self.quest_manager)

        # 宝箱・ギミック・ドア管理
        self.treasure_manager = TreasureManager(self.world_state_manager, self)
        self.gimmick_manager = GimmickManager(self.world_state_manager, self)
        self.door_manager = DoorManager(self.world_state_manager)

        # シーン管理
        self.scenes = {
            "title": TitleScene(self),
            "map": MapScene(self),
            "battle": BattleScene(self),
            "menu": MenuScene(self),
            "shop": ShopScene(self),
        }
        self.current_scene = "title"
        self._scene_stack: list[str] = []

        # 共通Luaスクリプト（ワールドルール等）を読み込み
        self.script_api.load_common_scripts()

        # MapSceneにスクリプトエンジン・宝箱・ギミック・ドアを接続
        map_scene = self.scenes.get("map")
        if map_scene and hasattr(map_scene, "init_npc_system"):
            map_scene.init_npc_system(self.script_engine)
        if map_scene:
            map_scene.treasure_manager = self.treasure_manager
            map_scene.gimmick_manager = self.gimmick_manager
            map_scene.door_manager = self.door_manager

    @property
    def party(self):
        return self.character_data.get_party()

    @party.setter
    def party(self, value):
        self.character_data.replace_party(value)
    
    def push_scene(self, scene_name: str):
        """現在のシーンをスタックに退避し、新しいシーンに遷移"""
        if scene_name in self.scenes:
            self._scene_stack.append(self.current_scene)
            self.current_scene = scene_name
            self.scenes[scene_name].on_enter()

    def pop_scene(self):
        """スタックから前のシーンを復帰"""
        if self._scene_stack:
            self.current_scene = self._scene_stack.pop()
            self.scenes[self.current_scene].on_resume()

    def change_scene(self, scene_name: str):
        """シーンを切り替える（スタッククリア）"""
        if scene_name in self.scenes:
            self._scene_stack.clear()
            self.current_scene = scene_name
            self.scenes[scene_name].on_enter()
    
    def run(self):
        """ゲームのメインループ"""
        self.scenes[self.current_scene].on_enter()
        
        while self.running:
            # イベント処理
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
            
            # 現在のシーンを更新
            self.scenes[self.current_scene].handle_events(events)
            self.scenes[self.current_scene].update()
            
            # 描画
            self.screen.fill((0, 0, 0))
            self.scenes[self.current_scene].draw(self.screen)
            
            pygame.display.flip()
            self.clock.tick(FPS)

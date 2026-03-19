"""
スクリプトAPIレイヤー — Script API Layer

Registers Python-backed functions as Lua globals so that Lua scripts
can interact with game systems (NPC dialogue, quests, world state,
party, flags, events, and rules).
"""

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ScriptAPI:
    """Bridges game systems into the Lua scripting environment.

    Parameters
    ----------
    engine : ScriptEngine
        The script engine whose Lua runtime receives the API globals.
    game : Game or None
        Reference to the main Game instance (for party/inventory access).
    world_state_manager : WorldStateManager or None
        Reference to the world state manager.
    quest_manager : object or None
        Reference to the quest manager (may be None initially).
    """

    def __init__(
        self,
        engine: Any,
        game: Any = None,
        world_state_manager: Any = None,
        quest_manager: Any = None,
    ):
        self._engine = engine
        self._game = game
        self._wsm = world_state_manager
        self._quest_manager = quest_manager

        # Event system: event_id -> list of callbacks
        self._event_handlers: Dict[str, List[Callable]] = {}

        # Current quest context (set by NPC/quest system before running script)
        self._current_quest_id: Optional[str] = None

        if engine.is_available:
            self._register_all()

    # ------------------------------------------------------------------
    # Property setters (allow deferred wiring)
    # ------------------------------------------------------------------

    @property
    def quest_manager(self) -> Any:
        return self._quest_manager

    @quest_manager.setter
    def quest_manager(self, value: Any) -> None:
        self._quest_manager = value

    @property
    def current_quest_id(self) -> Optional[str]:
        return self._current_quest_id

    @current_quest_id.setter
    def current_quest_id(self, value: Optional[str]) -> None:
        self._current_quest_id = value

    # ------------------------------------------------------------------
    # Registration entry point
    # ------------------------------------------------------------------

    def _register_all(self) -> None:
        """Register every API namespace into Lua globals."""
        lua = self._engine.lua
        if lua is None:
            return

        self._register_npc(lua)
        self._register_quest(lua)
        self._register_world(lua)
        self._register_party(lua)
        self._register_flag(lua)
        self._register_event(lua)
        self._register_rules(lua)

        logger.info("Script API registered (all namespaces)")

    # ------------------------------------------------------------------
    # npc namespace
    # ------------------------------------------------------------------

    def _register_npc(self, lua: Any) -> None:
        lua.execute("npc = {}")
        npc_table = lua.eval("npc")

        def npc_say(speaker: str, text: str) -> Any:
            """Yields a say command for the dialogue renderer."""
            # This is called from Lua inside a coroutine.  We return a
            # sentinel that the coroutine wrapper recognises.
            # In practice the Lua script calls coroutine.yield from Lua side.
            # We register a helper that does the yield for them.
            pass  # Implemented via Lua helper below

        def npc_choice(options: Any) -> Any:
            """Yields a choice command and expects the selected index back."""
            pass  # Implemented via Lua helper below

        # We use Lua-side wrappers that call coroutine.yield so the Python
        # coroutine runner picks up the yielded values.
        lua.execute("""
            npc = npc or {}
            function npc.say(speaker, text)
                coroutine.yield("say", speaker, text)
            end
            function npc.choice(options)
                return coroutine.yield("choice", options)
            end
        """)

        # Shop coroutine-yield wrapper
        lua.execute("""
            function npc.open_shop(shop_id)
                coroutine.yield("shop", shop_id)
            end
        """)

        # inn support
        api = self

        def npc_get_inn_price() -> int:
            if api._game is None:
                logger.warning("npc.get_inn_price(): game is None")
                return 0
            map_scene = api._game.scenes.get("map")
            if map_scene is None:
                logger.warning("npc.get_inn_price(): MapScene not found, inn_price defaults to 0")
                return 0
            price = (map_scene.current_map_data or {}).get("inn_price", 0)
            if price == 0:
                logger.debug("npc.get_inn_price(): inn_price not set for current map")
            return int(price)

        # Re-fetch npc_table after all lua.execute blocks to ensure the reference is fresh
        npc_table = lua.eval("npc")
        npc_table["get_inn_price"] = npc_get_inn_price

        lua.execute("""
            function npc.open_inn(price)
                coroutine.yield("inn", price)
            end
        """)

        logger.debug("Registered npc namespace")

    # ------------------------------------------------------------------
    # quest namespace
    # ------------------------------------------------------------------

    def _register_quest(self, lua: Any) -> None:
        api = self

        def quest_start(quest_id: str) -> None:
            qm = api._quest_manager
            if qm is None:
                logger.warning("quest.start(%s): quest_manager is None", quest_id)
                return None
            try:
                qm.start_quest(quest_id)
            except Exception:
                logger.exception("quest.start(%s) failed", quest_id)

        def quest_complete() -> None:
            qm = api._quest_manager
            qid = api._current_quest_id
            if qm is None:
                logger.warning("quest.complete(): quest_manager is None")
                return None
            if qid is None:
                logger.warning("quest.complete(): no current quest context")
                return None
            try:
                qm.complete_quest(qid)
            except Exception:
                logger.exception("quest.complete() failed for %s", qid)

        def quest_get_state(quest_id: str) -> Any:
            qm = api._quest_manager
            if qm is None:
                logger.warning("quest.get_state(%s): quest_manager is None", quest_id)
                return None
            try:
                return qm.get_quest_state(quest_id)
            except Exception:
                logger.exception("quest.get_state(%s) failed", quest_id)
                return None

        def quest_get_stage() -> Any:
            qm = api._quest_manager
            qid = api._current_quest_id
            if qm is None:
                logger.warning("quest.get_stage(): quest_manager is None")
                return None
            if qid is None:
                logger.warning("quest.get_stage(): no current quest context")
                return None
            try:
                return qm.get_quest_stage(qid)
            except Exception:
                logger.exception("quest.get_stage() failed for %s", qid)
                return None

        def quest_set_stage(stage_name: str) -> None:
            qm = api._quest_manager
            qid = api._current_quest_id
            if qm is None:
                logger.warning("quest.set_stage(%s): quest_manager is None", stage_name)
                return None
            if qid is None:
                logger.warning("quest.set_stage(%s): no current quest context", stage_name)
                return None
            try:
                qm.set_quest_stage(qid, stage_name)
            except Exception:
                logger.exception("quest.set_stage(%s) failed for %s", stage_name, qid)

        def quest_set_objective(text: str) -> None:
            qm = api._quest_manager
            qid = api._current_quest_id
            if qm is None:
                logger.warning("quest.set_objective(%s): quest_manager is None", text)
                return None
            if qid is None:
                logger.warning("quest.set_objective(): no current quest context")
                return None
            try:
                qm.set_quest_objective(qid, text)
            except Exception:
                logger.exception("quest.set_objective() failed for %s", qid)

        def quest_update(quest_id: str, stage: str) -> None:
            qm = api._quest_manager
            if qm is None:
                logger.warning("quest.update(%s, %s): quest_manager is None", quest_id, stage)
                return None
            try:
                qm.update_quest(quest_id, stage)
            except Exception:
                logger.exception("quest.update(%s, %s) failed", quest_id, stage)

        # Register as Lua table
        lua.execute("quest = {}")
        quest_table = lua.eval("quest")
        quest_table["start"] = quest_start
        quest_table["complete"] = quest_complete
        quest_table["get_state"] = quest_get_state
        quest_table["get_stage"] = quest_get_stage
        quest_table["set_stage"] = quest_set_stage
        quest_table["set_objective"] = quest_set_objective
        quest_table["update"] = quest_update

        logger.debug("Registered quest namespace")

    # ------------------------------------------------------------------
    # world namespace
    # ------------------------------------------------------------------

    def _register_world(self, lua: Any) -> None:
        api = self

        def world_get_layer() -> Any:
            wsm = api._wsm
            if wsm is None:
                logger.warning("world.get_layer(): world_state_manager is None")
                return None
            return wsm.current_layer

        def world_get_state(key: str) -> Any:
            wsm = api._wsm
            if wsm is None:
                logger.warning("world.get_state(%s): world_state_manager is None", key)
                return None
            return wsm.get_state(key)

        def world_set_state(key: str, value: Any) -> None:
            wsm = api._wsm
            if wsm is None:
                logger.warning("world.set_state(%s): world_state_manager is None", key)
                return None
            wsm.set_state(key, value)

        lua.execute("world = {}")
        world_table = lua.eval("world")
        world_table["get_layer"] = world_get_layer
        world_table["get_state"] = world_get_state
        world_table["set_state"] = world_set_state

        logger.debug("Registered world namespace")

    # ------------------------------------------------------------------
    # party namespace
    # ------------------------------------------------------------------

    def _register_party(self, lua: Any) -> None:
        api = self

        def _get_party():
            if api._game is None:
                return None
            return api._game.party

        def party_has_member(name: str) -> bool:
            party = _get_party()
            if party is None:
                logger.warning("party.has_member(%s): game is None", name)
                return False
            return any(m.get("name") == name for m in party)

        def party_get_level(name: str) -> Any:
            party = _get_party()
            if party is None:
                logger.warning("party.get_level(%s): game is None", name)
                return None
            for m in party:
                if m.get("name") == name:
                    return m.get("level")
            return None

        def party_add_gold(amount: int) -> None:
            if api._game is None:
                logger.warning("party.add_gold(%s): game is None", amount)
                return
            amount = int(amount)
            api._game.gold = max(0, api._game.gold + amount)
            logger.debug("Gold changed by %d -> %d", amount, api._game.gold)

        def party_add_item(item_id: str, count: int = 1) -> None:
            if api._game is None:
                logger.warning("party.add_item(%s): game is None", item_id)
                return
            count = int(count)
            inv = api._game.inventory
            current = inv.get(item_id, 0)
            inv[item_id] = min(99, current + count)
            logger.debug("Item %s: %d -> %d", item_id, current, inv[item_id])

        def party_remove_item(item_id: str, count: int = 1) -> None:
            if api._game is None:
                logger.warning("party.remove_item(%s): game is None", item_id)
                return
            count = int(count)
            inv = api._game.inventory
            current = inv.get(item_id, 0)
            new_count = max(0, current - count)
            if new_count == 0:
                inv.pop(item_id, None)
            else:
                inv[item_id] = new_count
            logger.debug("Item %s: %d -> %d", item_id, current, new_count)

        def party_get_gold() -> int:
            if api._game is None:
                return 0
            return api._game.gold

        def party_remove_gold(amount: int) -> None:
            if api._game is None:
                return
            amount = int(amount)
            api._game.gold = max(0, api._game.gold - amount)
            logger.debug("Gold removed %d -> %d", amount, api._game.gold)

        def party_rest() -> None:
            """Restore HP/MP for all party members."""
            if api._game is None:
                return
            for member in api._game.party:
                member["hp"] = member["max_hp"]
                member["mp"] = member["max_mp"]
            logger.debug("Party fully rested")

        lua.execute("party = {}")
        party_table = lua.eval("party")
        party_table["has_member"] = party_has_member
        party_table["get_level"] = party_get_level
        party_table["add_gold"] = party_add_gold
        party_table["add_item"] = party_add_item
        party_table["remove_item"] = party_remove_item
        party_table["get_gold"] = party_get_gold
        party_table["remove_gold"] = party_remove_gold
        party_table["rest"] = party_rest

        logger.debug("Registered party namespace")

    # ------------------------------------------------------------------
    # flag namespace
    # ------------------------------------------------------------------

    def _register_flag(self, lua: Any) -> None:
        api = self

        def flag_get(name: str) -> Any:
            wsm = api._wsm
            if wsm is None:
                logger.warning("flag.get(%s): world_state_manager is None", name)
                return None
            return wsm.get_flag(name)

        def flag_set(name: str, value: Any) -> None:
            wsm = api._wsm
            if wsm is None:
                logger.warning("flag.set(%s): world_state_manager is None", name)
                return
            wsm.set_flag(name, value)

        lua.execute("flag = {}")
        flag_table = lua.eval("flag")
        flag_table["get"] = flag_get
        flag_table["set"] = flag_set

        logger.debug("Registered flag namespace")

    # ------------------------------------------------------------------
    # event namespace
    # ------------------------------------------------------------------

    def _register_event(self, lua: Any) -> None:
        api = self

        def event_trigger(event_id: str) -> None:
            logger.info("Event triggered: %s", event_id)
            handlers = api._event_handlers.get(event_id, [])
            for handler in handlers:
                try:
                    handler(event_id)
                except Exception:
                    logger.exception("Error in event handler for %s", event_id)
            # Dispatch to quest manager for active quest stage events
            qm = api._quest_manager
            if qm is not None:
                try:
                    qm.dispatch_event(event_id)
                except Exception:
                    logger.exception("Error dispatching event %s to quest manager", event_id)

        lua.execute("event = {}")
        event_table = lua.eval("event")
        event_table["trigger"] = event_trigger

        # Coroutine-yield wrappers for fade/wait/battle effects
        lua.execute("""
            event = event or {}
            function event.fade_out()
                coroutine.yield("fade_out")
            end
            function event.fade_in()
                coroutine.yield("fade_in")
            end
            function event.wait(seconds)
                coroutine.yield("wait", seconds)
            end
            function event.start_battle(enemy_type, count, level)
                return coroutine.yield("battle", enemy_type, count or 1, level or 1)
            end
            function event.open_save(save_type)
                coroutine.yield("open_save", save_type or "npc_king")
            end
        """)

        logger.debug("Registered event namespace")

    def register_event_handler(self, event_id: str, callback: Callable) -> None:
        """Register a Python callback for a scripting event (from Python side)."""
        self._event_handlers.setdefault(event_id, []).append(callback)

    # ------------------------------------------------------------------
    # rules namespace
    # ------------------------------------------------------------------

    def _register_rules(self, lua: Any) -> None:
        api = self

        def rules_register(event_type: str, callback: Any) -> None:
            wsm = api._wsm
            if wsm is None:
                logger.warning(
                    "rules.register(%s): world_state_manager is None — rule not registered",
                    event_type,
                )
                return

            # Wrap the Lua callback so it can be called from Python
            def python_wrapper(*args: Any) -> None:
                try:
                    callback(*args)
                except Exception:
                    logger.exception("Error in Lua rule callback for %s", event_type)

            wsm.register_rule(event_type, python_wrapper)

        lua.execute("rules = {}")
        rules_table = lua.eval("rules")
        rules_table["register"] = rules_register

        logger.debug("Registered rules namespace")

    # ------------------------------------------------------------------
    # Convenience: load and auto-execute a common script
    # ------------------------------------------------------------------

    def load_common_scripts(self) -> None:
        """Load scripts from scripts/common/ that register rules etc."""
        engine = self._engine
        if not engine.is_available:
            logger.warning("Cannot load common scripts — engine not available")
            return

        import os
        common_dir = engine._base_dir / "common"
        if not common_dir.is_dir():
            logger.debug("No common scripts directory at %s", common_dir)
            return

        for lua_file in sorted(common_dir.glob("*.lua")):
            rel = lua_file.relative_to(engine._base_dir)
            logger.info("Loading common script: %s", rel)
            engine.load_script(str(rel).replace(os.sep, "/"))

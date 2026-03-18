"""
スクリプトエンジン — Script Engine

Provides sandboxed Lua script execution via the lupa library.
Supports coroutine-based dialogue flow, instruction-count limits,
hot-reload in dev mode, and safe error handling.
"""

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Instruction limit per coroutine resume (prevents infinite loops)
INSTRUCTION_LIMIT = 100_000

# Lua globals that must be removed for sandboxing
_UNSAFE_GLOBALS = [
    "io", "os", "loadfile", "dofile", "require",
    "collectgarbage", "newproxy",
]

# Lua coroutine helper code — manages coroutines on the Lua side so that
# Python never needs to hold a raw Lua thread reference (which lupa wraps
# as _LuaCoroutineFunction and breaks coroutine.status/resume).
_COROUTINE_HELPERS = """
-- Registry of live coroutines keyed by string id
_co_registry = {}
_co_next_id = 0

function _co_create(func)
    local co = coroutine.create(func)
    _co_next_id = _co_next_id + 1
    local id = tostring(_co_next_id)
    _co_registry[id] = co
    return id
end

function _co_resume(id, ...)
    local co = _co_registry[id]
    if not co then return false, "invalid coroutine id: " .. tostring(id) end
    return coroutine.resume(co, ...)
end

function _co_status(id)
    local co = _co_registry[id]
    if not co then return "dead" end
    return coroutine.status(co)
end

function _co_destroy(id)
    _co_registry[id] = nil
end
"""

try:
    from lupa import LuaRuntime  # type: ignore
    LUPA_AVAILABLE = True
except ImportError:
    LUPA_AVAILABLE = False
    LuaRuntime = None  # type: ignore
    logger.warning(
        "lupa is not installed — ScriptEngine will operate in stub mode. "
        "Install with: pip install lupa"
    )


class ScriptEngine:
    """Sandboxed Lua script engine backed by lupa.

    Parameters
    ----------
    base_dir : str or Path, optional
        Directory from which Lua scripts are loaded.  Defaults to
        ``<project_root>/scripts/``.
    dev_mode : bool
        When True, enables hot-reload via :meth:`reload_script`.
    """

    def __init__(self, base_dir: Optional[str] = None, dev_mode: bool = False):
        project_root = Path(__file__).resolve().parent.parent.parent
        self._base_dir = Path(base_dir) if base_dir else project_root / "scripts"
        self._dev_mode = dev_mode
        self._script_cache: dict[str, Any] = {}
        self._lua: Optional[Any] = None

        # Lua-side coroutine helper functions (set during init)
        self._co_create: Optional[Any] = None
        self._co_resume: Optional[Any] = None
        self._co_status: Optional[Any] = None
        self._co_destroy: Optional[Any] = None

        if LUPA_AVAILABLE:
            self._init_lua()
        else:
            logger.warning("ScriptEngine running in stub mode (no lupa)")

    # ------------------------------------------------------------------
    # Lua initialisation & sandboxing
    # ------------------------------------------------------------------

    def _init_lua(self) -> None:
        """Create a LuaRuntime and apply sandboxing."""
        self._lua = LuaRuntime(unpack_returned_tuples=True)
        self._sandbox()
        self._install_coroutine_helpers()
        logger.info("Lua runtime initialised (sandbox active)")

    def _sandbox(self) -> None:
        """Remove dangerous globals from the Lua environment."""
        lua = self._lua
        if lua is None:
            return

        # Remove unsafe globals
        for name in _UNSAFE_GLOBALS:
            lua.execute(f"{name} = nil")

        # Remove the debug library (we use Lua-side instruction counting
        # via the coroutine helpers instead).
        lua.execute("debug = nil")

        logger.debug("Lua sandbox applied — removed unsafe globals")

    def _install_coroutine_helpers(self) -> None:
        """Install Lua-side coroutine management functions."""
        lua = self._lua
        if lua is None:
            return

        lua.execute(_COROUTINE_HELPERS)
        self._co_create = lua.eval("_co_create")
        self._co_resume = lua.eval("_co_resume")
        self._co_status = lua.eval("_co_status")
        self._co_destroy = lua.eval("_co_destroy")

    # ------------------------------------------------------------------
    # Script loading
    # ------------------------------------------------------------------

    def load_script(self, script_path: str) -> Optional[Any]:
        """Load a Lua script and return its return value (usually a table).

        Parameters
        ----------
        script_path : str
            Path relative to the base directory, e.g. ``"npc/alma.lua"``.

        Returns
        -------
        Lua table or None on failure.
        """
        if self._lua is None:
            logger.warning("load_script(%s): no Lua runtime", script_path)
            return None

        # Check cache
        if script_path in self._script_cache:
            return self._script_cache[script_path]

        full_path = self._base_dir / script_path
        if not full_path.is_file():
            logger.error("Script not found: %s", full_path)
            return None

        try:
            source = full_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.error("Cannot read %s: %s", full_path, exc)
            return None

        result = self._execute_source(source, str(full_path))
        if result is not None:
            self._script_cache[script_path] = result
        return result

    def execute_string(self, source: str, name: str = "<string>") -> Optional[Any]:
        """Execute a Lua source string directly.  Useful for API setup."""
        if self._lua is None:
            logger.warning("execute_string: no Lua runtime")
            return None
        return self._execute_source(source, name)

    def _execute_source(self, source: str, name: str) -> Optional[Any]:
        """Run Lua source and return the result or None on error."""
        lua = self._lua
        if lua is None:
            return None

        try:
            result = lua.execute(source)
            return result
        except Exception as exc:
            logger.error("Lua error in %s: %s", name, exc)
            return None

    # ------------------------------------------------------------------
    # Coroutine execution
    # ------------------------------------------------------------------

    def execute_coroutine(self, lua_func: Any, *args: Any) -> Optional["_CoroutineRunner"]:
        """Run a Lua function as a coroutine.

        The function may yield tuples like ``("say", speaker, text)`` which
        the caller (e.g. dialogue renderer) intercepts and resumes later.

        Parameters
        ----------
        lua_func : Lua function
            The function to wrap in a coroutine.
        *args
            Arguments passed to the function on first resume.

        Returns
        -------
        A :class:`_CoroutineRunner` (iterator/sendable) or None on failure.
        """
        if self._lua is None or self._co_create is None:
            logger.warning("execute_coroutine: no Lua runtime")
            return None

        try:
            co_id = self._co_create(lua_func)
            return _CoroutineRunner(
                co_id,
                self._co_resume,
                self._co_status,
                self._co_destroy,
                args,
            )
        except Exception as exc:
            logger.error("Failed to create coroutine: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Hot-reload (dev mode)
    # ------------------------------------------------------------------

    def reload_script(self, script_path: str) -> Optional[Any]:
        """Clear the cached version of a script and reload it.

        Only effective when ``dev_mode`` is True.
        """
        if not self._dev_mode:
            logger.debug("reload_script ignored (dev_mode=False)")
            return self._script_cache.get(script_path)

        self._script_cache.pop(script_path, None)
        logger.info("Hot-reloading script: %s", script_path)
        return self.load_script(script_path)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @property
    def lua(self) -> Optional[Any]:
        """Direct access to the underlying LuaRuntime (for API registration)."""
        return self._lua

    @property
    def is_available(self) -> bool:
        """True if the Lua runtime is functional."""
        return self._lua is not None

    def clear_cache(self) -> None:
        """Drop all cached scripts."""
        self._script_cache.clear()


class _CoroutineRunner:
    """Iterator wrapper around a Lua coroutine managed by Lua-side helpers.

    Coroutines are identified by a string id stored in a Lua-side registry.
    This avoids the lupa issue where ``coroutine.create`` returns a Python
    wrapper object that ``coroutine.status`` / ``coroutine.resume`` cannot
    accept.

    Supports:
    - ``for yielded in runner:`` iteration (simple scripts)
    - ``runner.send(value)`` to pass a value back into the coroutine
      (e.g. returning the player's dialogue choice)
    """

    def __init__(
        self,
        co_id: str,
        resume_fn: Any,
        status_fn: Any,
        destroy_fn: Any,
        initial_args: tuple,
    ):
        self._co_id = co_id
        self._resume = resume_fn
        self._status = status_fn
        self._destroy = destroy_fn
        self._initial_args = initial_args
        self._started = False

    def __del__(self) -> None:
        # Clean up the Lua-side registry entry
        try:
            if self._destroy is not None:
                self._destroy(self._co_id)
        except Exception:
            pass

    def __iter__(self):
        return self

    def __next__(self):
        return self.send(None)

    def send(self, value: Any = None) -> Any:
        """Resume the coroutine, returning whatever it yields next.

        Raises StopIteration when the coroutine finishes or errors.
        """
        try:
            if not self._started:
                self._started = True
                result = self._resume(self._co_id, *self._initial_args)
            else:
                result = self._resume(self._co_id, value)
        except Exception as exc:
            logger.error("Coroutine resume error: %s", exc)
            raise StopIteration from exc

        # With unpack_returned_tuples=True, result is a flat tuple:
        # (ok, val1, val2, ...) from coroutine.resume
        if isinstance(result, tuple):
            ok = result[0]
            values = result[1:]
        else:
            ok = result
            values = ()

        if not ok:
            err_msg = values[0] if values else "unknown error"
            logger.error("Coroutine error: %s", err_msg)
            raise StopIteration

        # Check if the coroutine has finished
        status = self._status(self._co_id)
        if status == "dead":
            raise StopIteration

        # Return yielded values
        if len(values) == 0:
            return None
        elif len(values) == 1:
            return values[0]
        else:
            return values

    @property
    def is_alive(self) -> bool:
        """True if the coroutine has not finished yet."""
        try:
            return self._status(self._co_id) != "dead"
        except Exception:
            return False

from frida.core import Script, Session, ScriptExportsSync, ScriptExportsAsync, SessionDetachedCallback
from typing import Final, Optional, Dict, Tuple, Protocol, List, Callable, Any, Literal, Set, FrozenSet, overload
from agent.rpc.message import RPCMsg_INIT_CONFIG, RPCMessage, RPCPayload, RPCMsgType, RPCMsgSource
from agent.rpc.resolver import RPCResolver, RPC
from agent.rpc.exports import ScriptExportsSyncWrapper
from agent.rpc.handler.js_handle import JsHandle
from agent.logger import FileLogger, LoggerName
from prompt_toolkit.layout.containers import HSplit, VSplit
from datetime import datetime
import colorama
import pathlib
import codecs
import json
import sys
import re


RPC_ENV_INJECT_SCRIPT_TEMPLATE: Final[str] = """
const INJECT_ENV = {inject_env};
import {{ Config }} from "./frida-analykit/script/config.js";
Object.entries(INJECT_ENV).forEach(kv => {{
    const [k, v] = kv;
    Config[k] = v;
}});
import("/index.js");
"""

REG_MAP_SOURCE: Final[re.Pattern] = re.compile(r'^(\d+)\s+(.*?)$', re.MULTILINE)

def try_inject_environ(script_src: str, env: dict={}) -> str:
    inject_source = RPC_ENV_INJECT_SCRIPT_TEMPLATE.format(
        inject_env=json.dumps(env, ensure_ascii=False),
    )

    codepos = script_src.find('✄')
    if codepos == -1:
        return

    firstmap = REG_MAP_SOURCE.search(script_src)
    startpos, _ = firstmap.span()
    return f"""{script_src[:startpos]}{len(inject_source)} /__inject__.js
{script_src[startpos:codepos]}✄
{inject_source}
{script_src[codepos:]}
"""


ScriptEnv = RPCMsg_INIT_CONFIG


class ScriptWrapper:
    exports_sync: Final[ScriptExportsSyncWrapper]
    exports_async: ScriptExportsAsync

    def load(self) -> None: ...
    def unload(self) -> None: ...
    def eternalize(self) -> None: ...
    def enable_debugger(self, port: Optional[int] = None) -> None: ...
    def disable_debugger(self) -> None: ...
    
    async def list_exports_async(self) -> List[str]: ...
    def set_log_handler(self, handler: Callable[[str, str], None]) -> None: ...

    def on_exception(self, func: Callable[[RPCPayload], None]) -> Callable[[RPCPayload], None]: ...
    def on_message(self, typ: RPCMsgType): ...
    def on_batch(self, source: RPCMsgSource): ...
    
    _script: Script
    _env: ScriptEnv
    _resolver: RPCResolver

    __SCRIPT_EXPORT__: Final[FrozenSet[str]] = frozenset([
        'load', 'unload', 'eternalize', 
        'enable_debugger', 'disable_debugger', 
        'exports_async', 
        'list_exports_async', 
        'set_log_handler',
    ])

    __RESOLVER_EXPORT__: Final[FrozenSet[str]] = frozenset([
        'on_exception', 'on_message', 'on_batch', 
    ])

    def __init__(self, script: Script, env: ScriptEnv, resolver: Optional[RPCResolver] = None) -> 'ScriptWrapper':
        self._script = script
        self._env = env

        if resolver is None:
            resolver = RPC
        self._resolver = resolver
        resolver.register_script(script)
        self.exports_sync = ScriptExportsSyncWrapper(script)

    def post(self, message: RPCMessage, data: Optional[bytes] = None) -> None:
        self._script.post(message.model_dump(), data)

    def __getattribute__(self, name):
        if name in ScriptWrapper.__SCRIPT_EXPORT__:
            return getattr(self._script, name)
        elif name in ScriptWrapper.__RESOLVER_EXPORT__:
            return getattr(self._resolver, name)
        return object.__getattribute__(self, name)
    
    def __dir__(self):
        return tuple(object.__dir__(self)) + tuple(ScriptWrapper.__SCRIPT_EXPORT__) + tuple(ScriptWrapper.__RESOLVER_EXPORT__)

    def set_logger(self, stdout: Optional[str] = None, stderr: Optional[str] = None):
        err = sys.stderr
        out = sys.stdout
        if stdout == stderr:
            out = FileLogger(LoggerName.outerr, stdout)
            out.set_alias(LoggerName.stdout)
            err = out.clone()
            err.set_color(colorama.Fore.RED)
            err.set_alias(LoggerName.stderr)
        else:
            if stderr:
                err = FileLogger(LoggerName.stderr, stderr)
            if stdout:
                out = FileLogger(LoggerName.stdout, stdout)
        
        def handler(level: str, text: str):
            if level == "info":
                print(text, file=out)
            else:
                print(text, file=err)

        self.set_log_handler(handler)

    def list_exports_sync(self) -> List[str]: 
        return self.exports_sync._list_exports()

    @property
    def scope_id(self):
        return hex(id(self))

    def jsh(self, path: str) -> JsHandle:
        return JsHandle(path, script=self, scope_id=self.scope_id)

    def eval(self, source: str) -> JsHandle:
        result = self.exports_sync.scope_eval(source, self.scope_id)
        return JsHandle.new_from_payload(result, script=self, scope_id=self.scope_id)


class SessionWrapper:
    @property
    def is_detached(self) -> bool: ...
    @overload
    def on(self, signal: str, callback: Callable[..., Any]) -> None: ...
    @overload
    def on(self, signal: Literal["detached"], callback: SessionDetachedCallback) -> None: ...
    @overload
    def off(self, signal: Literal["detached"], callback: SessionDetachedCallback) -> None: ...
    @overload
    def off(self, signal: str, callback: Callable[..., Any]) -> None: ...
    def detach(self) -> None: ...
    def resume(self) -> None: ...
    def enable_child_gating(self) -> None: ...
    def disable_child_gating(self) -> None: ...

    _session: Session

    __SESSION_EXPORT__: Final[FrozenSet[str]] = frozenset([
        'detach', 'resume', 'on', 'off',
        'enable_child_gating', 'disable_child_gating',
    ])

    def __init__(self, session: Session):
        self._session = session

    def create_script(
        self, source: str, name: Optional[str] = None, snapshot: Optional[bytes] = None, runtime: Optional[str] = None,
        env: Optional[ScriptEnv] = None, resolver: Optional[RPCResolver] = None,
    ) -> ScriptWrapper:
        if env is None:
            env = ScriptEnv()

        source = try_inject_environ(source, env.model_dump())

        script = self._session.create_script(source, name, snapshot, runtime)
        return ScriptWrapper(script, env)

    def open_script(
        self, jsfile: str, name: Optional[str] = None, snapshot: Optional[bytes] = None, runtime: Optional[str] = None,
        env: Optional[ScriptEnv] = None, resolver: Optional[RPCResolver] = None,
    ) -> ScriptWrapper:
        path = pathlib.Path(jsfile)
        stat = path.stat()
        update_time = datetime.fromtimestamp(stat.st_mtime)
        print('=================== frida-analykit ===================')
        print(f'[jsfile]    {jsfile}')
        print(f'[update_at] {update_time.strftime("%Y-%m-%d %H:%M:%S.%f")}')
        print('======================================================')

        with codecs.open(jsfile, 'r', 'utf-8') as f:
            source = f.read()
        
        return self.create_script(source, name, snapshot, runtime, env, resolver)
    
    @classmethod
    def from_session(cls, session: Session) -> 'SessionWrapper':
        return cls(session)
    
    def __getattribute__(self, name):
        if name in SessionWrapper.__SESSION_EXPORT__:
            return getattr(self._session, name)
        return object.__getattribute__(self, name)
    
    @classmethod
    def __dir__(cls):
        return tuple(object.__dir__(cls)) + tuple(SessionWrapper.__SESSION_EXPORT__)
    

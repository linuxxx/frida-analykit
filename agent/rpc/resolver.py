
import functools
from typing import Final, List, Optional, Set, Mapping, MutableMapping, Callable, Any
from frida.core import Script, ScriptMessage, ScriptErrorMessage
from agent.rpc.message import (
    RPCMsgData, RPCMsgType, RPCMessage, 
    RPCMsgSource, RPCPayload, unpack_batch_payload, 
    register_payload_on_batch_default_handler, 
    register_payload_on_message_default_handler)
from agent.config import Config
from datetime import datetime
from enum import Enum
import colorama
import json
import sys
import os


class RPCResolver:
    _scripts: Set[Script]
    _typ_handler: MutableMapping[str, Callable[[RPCPayload], None]]
    _batch_source_handler: MutableMapping[str, Callable[[List[RPCPayload]], None]]
    _exc_handler: Optional[Callable[[ScriptErrorMessage, Optional[bytes]], None]]
    _global: bool = False

    def __init__(self):
        self._scripts = set()
        self._typ_handler = {}
        self._batch_source_handler = {}
        self._exc_handler = None

    def register_script(self, script: Script):
        if script not in self._scripts:
            script.on('message', self._on_message_handler)
            self._scripts.add(script)

    def _on_message_handler(self, message: ScriptMessage, data: Optional[bytes]):
        if message['type'] == 'send':
            msg = RPCMessage.model_validate(message.get('payload', {}))
            
            handler = None
            if msg.type == RPCMsgType.BATCH:
                handler = self._batch_source_handler.get(msg.source, None)
                payload = RPCPayload(message, data)
                if handler is None:
                    handler = self._default_batch_handler
                handler(payload)
            else:
                handler = self._get_handler(msg.type)
                if handler:
                    handler(RPCPayload(message=msg, data=data))

        elif message['type'] == 'error':
            if self._exc_handler:
                self._exc_handler(message, data)
            else:
                print(json.dumps(message, ensure_ascii=False), file=sys.stderr)
        
    def _get_handler(self, typ: str) -> Callable[[RPCPayload], None]:
        handler = self._typ_handler.get(typ, None)
        if handler is None:
            handler = self._default_type_handler
        return handler


    def _default_type_handler(self, payload: RPCPayload) -> None:
        conf = Config.get()
        suffix = datetime.now().strftime('%Y%m%d%f')
        if payload.message:
            print(f'{colorama.Fore.MAGENTA}[{payload.message.type}]{suffix} {payload.message.data.model_dump_json()}{colorama.Fore.RESET}')
        
        filename = f'{payload.message.type}_{suffix}'
        if conf.agent.datadir and payload.data:
            filepath = os.path.join(conf.agent.datadir, filename)
            with open(filepath, 'wb') as f:
                f.write(payload.data)
            print(f'{colorama.Fore.GREEN}[{filepath}] {len(payload.data) if payload.data is not None else 0}{colorama.Fore.RESET}')
        elif payload.data and len(payload.data) > 0:
            print(f'{colorama.Fore.MAGENTA}[{filename}] {len(payload.data) if payload.data is not None else 0}<drop>{colorama.Fore.RESET}')

    def _default_batch_handler(self, payload: RPCPayload):
        payload_list = unpack_batch_payload(payload)
        for payload in payload_list:
            msg, data = payload.message, payload.data
            handler = self._get_handler(msg.type)
            if handler:
                handler(msg, data)

    def on_exception(self, func: Callable[[RPCPayload], None]) -> Callable[[RPCPayload], None]:
        self._exc_handler = func
        return func

    def on_message(self, typ: RPCMsgType):
        def wrapper(func: Callable[[RPCPayload], None]) -> Callable[[RPCPayload], None]:
            real_typ = typ
            if isinstance(real_typ, Enum):
                real_typ = real_typ.value
            self._typ_handler[real_typ] = func
            if self._global:
                register_payload_on_message_default_handler(real_typ, func)
            return func
        return wrapper

    def on_batch(self, source: RPCMsgSource):
        def wrapper(func: Callable[[RPCPayload], None]) -> Callable[[RPCPayload], None]:
            real_source = source
            if isinstance(real_source, Enum):
                real_source = real_source.value
            self._batch_source_handler[real_source] = func
            if self._global:
                register_payload_on_batch_default_handler(real_source, func)
            return func
        return wrapper


__GLOBAL_RPC_HANDLER: Final[RPCResolver] = RPCResolver()
__GLOBAL_RPC_HANDLER._global = True

RPC: Final[RPCResolver] = __GLOBAL_RPC_HANDLER

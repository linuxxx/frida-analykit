from typing import List, Final, Optional, Union, Tuple, FrozenSet, TYPE_CHECKING
from agent.rpc.message import RPCMessage, RPCPayload
from pydantic import ValidationError
from frida.core import Script
import re

CAMEL_TO_SNAKE: Final[re.Pattern] = re.compile(r'([A-Z])')


def make_rpc_response(rsp: Union[Tuple[RPCMessage, Optional[bytes]], RPCMessage]) -> RPCPayload:
    if isinstance(rsp, (List, Tuple)) and len(rsp) > 1 and isinstance(rsp[1], bytes):
        return RPCPayload(
            message=rsp[0],
            data=rsp[1]
        )
    try:
        return RPCPayload(message=rsp)
    except ValidationError:
        return rsp


class ScriptExportsSyncWrapper:
    __script: Script

    __EXPORT__: Final[FrozenSet[str]] = frozenset([
        '_list_exports',
        '__dir__',
        '_ScriptExportsSyncWrapper__script', 
        '_ScriptExportsSyncWrapper__jsname2pyname',
        '_ScriptExportsSyncWrapper__EXPORT__', 
    ])

    def __init__(self, script: Script):
        self.__script = script

    def _list_exports(self) -> List[str]:
        exports = self.__script.list_exports_sync()
        return [self.__jsname2pyname(n) for n in exports]

    @staticmethod
    def __jsname2pyname(name):
        return CAMEL_TO_SNAKE.sub(lambda match: '_' + match.group(1).lower(), name)
    
    def __getattribute__(self, name):
        if name in ScriptExportsSyncWrapper.__EXPORT__:
            return object.__getattribute__(self, name)
        return ScriptCallWrapper(self.__script, name)

    def __dir__(self):
        return self._list_exports()



class ScriptCallWrapper:
    __name: str
    __script: Script

    def __init__(self, script: Script, name: str):
        self.__script = script
        self.__name = name

    def __call__(self, *args, **kwds):
        return make_rpc_response(getattr(self.__script.exports_sync, self.__name)(*args, **kwds))


# TODO
class ScriptExportsAsyncWrapper:
    pass
from enum import Enum, unique
from dataclasses import dataclass
from typing import Union, List, Optional, Dict, Any, Tuple, Callable
from pydantic import BaseModel
from pydantic_core import core_schema
from pydantic import GetCoreSchemaHandler


@unique
class RPCMsgType(Enum):
    SCOPE_CALL: str = 'SCOPE_CALL'
    SCOPE_EVAL: str = 'SCOPE_EVAL'
    SCOPE_GET: str = 'SCOPE_GET'
    ENUMERATE_OBJ_PROPS: str = 'ENUMERATE_OBJ_PROPS'
    BATCH: str = 'BATCH'
    INIT_CONFIG: str = 'INIT_CONFIG'
    SAVE_FILE: str = 'SAVE_FILE'
    SSL_SECRET: str = 'SSL_SECRET'
    PROGRESSING: str = 'PROGRESSING'

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type[BaseModel], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.str_schema()


@unique
class RPCMsgSource(Enum):

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type[BaseModel], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.str_schema()


class NativePointer(str):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type[BaseModel], handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.str_schema()


class RPCMsg_INIT_CONFIG(BaseModel):
    OnRPC: bool = True
    LogCollapse: bool = False
    

class RPCMsg_ERROR(BaseModel):
    pass


class RPCMsg_SCOPE_CALL(BaseModel):
    id: str
    type: str
    result: Optional[Any] = None


class RPCMsg_SCOPE_EVAL(BaseModel):
    id: str
    type: str
    result: Optional[Any] = None


class RPCMsg_SCOPE_GET(BaseModel):
    value: Optional[Any] = None


class RPCMsg_ENUMERATE_OBJ_PROPS(BaseModel):
    props: List[Dict[str, Any]] = [{}]


class RPCMsg_BATCH(BaseModel):
    message_list: List['RPCMessage']
    data_sizes: List[int]


class RPCMsg_SAVE_FILE(BaseModel):
    source: str
    filepath: str
    mode: str


class RPCMsg_SSL_SECRET(BaseModel):
    tag: str
    label: str
    client_random: str
    secret: str


class RPC_ErrorMsg(BaseModel):
    message: Optional[str]
    stack: Optional[str]


class RPCMsg_PROGRESSING(BaseModel):
    tag: str
    id: int
    step: int
    time: int
    extra: Dict[str, Any]
    error: Optional[RPC_ErrorMsg] = None



RPCMsgData = Union[
    RPCMsg_ERROR,
    RPCMsg_SCOPE_EVAL,
    RPCMsg_SCOPE_GET,
    RPCMsg_SCOPE_CALL,
    RPCMsg_ENUMERATE_OBJ_PROPS,
    RPCMsg_INIT_CONFIG,
    RPCMsg_BATCH,
    RPCMsg_SAVE_FILE,
    RPCMsg_SSL_SECRET,
    RPCMsg_PROGRESSING,
]


class RPCMessage(BaseModel):
    type: RPCMsgType
    tid: Optional[int] = None
    source: Optional[RPCMsgSource] = None
    data: RPCMsgData = RPCMsg_ERROR()


class RPCPayload(BaseModel):
    message: RPCMessage
    data: Optional[bytes] = None

    def __str__(self):
        if self.message.type == RPCMsgType.BATCH.value:
            return f"""<{self.message.type}({self.message.source})[{len(self.message.data.message_list)}]: {len(self.data) if self.data else 0}>"""
        else:
            if self.message.source:
                return f"""<{self.message.type}({self.message.source}): {len(self.data) if self.data else 0}>"""
            return f"""<{self.message.type}: {len(self.data) if self.data else 0}>"""
    
    def __repr__(self):
        return self.__str__()

    def do_handle(self):
        global _PAYLOAD_DEFAULT_HANDLER
        if self.message.type == RPCMsgType.BATCH.value:
            handler = _PAYLOAD_DEFAULT_HANDLER.get((None, self.message.source), None)
        else:
            handler = _PAYLOAD_DEFAULT_HANDLER.get((self.message.type, None), None)
        if handler is None:
            raise Exception(f'type[{self.message.type}], source[{self.message.source}] 的默认处理器不存在.')
        return handler(self)


_PAYLOAD_DEFAULT_HANDLER: Dict[
    Tuple[Optional[str], Optional[str]], 
    Callable[[RPCPayload], None],
] = {}


def register_payload_on_batch_default_handler(source: str, fn: Callable[[RPCPayload], None]):
    global _PAYLOAD_DEFAULT_HANDLER
    _PAYLOAD_DEFAULT_HANDLER[(None, source)] = fn


def register_payload_on_message_default_handler(typ: str, fn: Callable[[RPCPayload], None]):
    global _PAYLOAD_DEFAULT_HANDLER
    _PAYLOAD_DEFAULT_HANDLER[(typ, None)] = fn


def unpack_batch_payload(payload: RPCPayload) -> List[RPCPayload]:
    message, data = payload.message, payload.data
    batch_list: List[RPCPayload] = []
    inc = 0
    for i, msg_data_size in enumerate(zip(message.data.message_list, message.data.data_sizes)):
        msg, data_size = msg_data_size
        d = None
        if data_size > 0 and data is not None:
            d = data[inc: inc+data_size]
            inc += data_size
        batch_list.append(RPCPayload(message=msg, data=d))
    return batch_list    
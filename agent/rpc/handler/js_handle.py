from typing import Final, FrozenSet, MutableMapping, Optional, Union, List, Tuple, Any, Callable, Dict, TYPE_CHECKING
from agent.rpc.message import RPCPayload
import os
import functools 
import weakref
import json
from threading import Lock


# patch
_default_jsonenc = json.JSONEncoder.default
def _patched(self, o):
    if isinstance(o, JsHandle):
        return str(o)
    return _default_jsonenc(self, o)
json.JSONEncoder.default = _patched


if TYPE_CHECKING:
    from agent.session import ScriptWrapper


REPL = os.environ.get('REPL', False)


class Unset:
    name: str
    def __init__(self, name: str):
        self.name = name


_SCOPE_GET_PREFIX = '__get__$$'


class JsHandle:
    __parent: 'JsHandle'
    __path: str
    __script: 'ScriptWrapper'
    __props: MutableMapping[str, Optional['JsHandle']] = {}
    __typ: str = 'unknown'
    __scope_id: str = ''
    __inst_id: Union[str, bool, None] = None
    __value: Any = Unset('any')

    __lock: Lock = Lock()

    __INTERNAL_PROP__: Final[FrozenSet[str]] = frozenset(['_JsHandle' + v for v in [
        '__path',
        '__parent',
        '__script',
        '__props',
        '__typ',
        '__scope_id',
        '__inst_id',
        '__value',
        '__lock',
    ]])

    __LATER_PROP__: Final[FrozenSet[str]] = frozenset([
        'value',
        'type',
    ])


    def __init__(self, 
        path: str, parent: 'JsHandle' = None, *, 
        script: 'ScriptWrapper', typ: str = 'unknown', scope_id: str = '', inst_id: Union[str, bool, None] = None,
        props: Optional[MutableMapping[str, Optional['JsHandle']]] = None, value: Any = Unset('any'),
    ):
        self.__parent = parent
        self.__path = path
        self.__script = script
        self.__typ = typ
        self.__scope_id = scope_id
        self.__value = value
        if type(inst_id) is str:
            pass
        elif inst_id is True:
            inst_id = f'{_SCOPE_GET_PREFIX}{hex(id(self))}'
        elif inst_id is None:
            inst_id = str(self)
        else:
            raise TypeError(f'unexpected type of {type(inst_id)}')
        self.__inst_id = inst_id
        self.__props = props if props is not None else {
            name: Unset(typ) 
            for name, typ in self.__script.exports_sync.enumerate_obj_props(inst_id, scope_id).message.data.props[0].items()
        }

        weakref.finalize(self, functools.partial(self.__script.exports_sync.scope_del, inst_id, scope_id))

    def __repr__(self):
        return f'<JsHandle: [{self.__typ}] {str(self)}>'

    def __str__(self):
        if self.__parent is None:
            return self.__path
        if self.__inst_id is not None and self.__inst_id.startswith(_SCOPE_GET_PREFIX):
            return self.__inst_id
        return str(self.__parent) + '/' + self.__path

    def __dir__(self):
        return tuple(self.__props) + tuple(JsHandle.__LATER_PROP__)

    def __call__(self, *args):
        if len(args) > 0:
            args_list = []
            for a in args:
                if type(a) is JsHandle:
                    a = a._JsHandle__inst_id
                    if not a.startswith(_SCOPE_GET_PREFIX):
                        a = _SCOPE_GET_PREFIX + a
                args_list.append(a)
        else:
            args_list = []
        message = self.__script.exports_sync.scope_call(self.__inst_id, args_list, self.__scope_id).message
        data = message.data
        inst_id = data.id
        typ = data.type
        result = data.result
        return JsHandle(inst_id, self, script=self.__script, typ=typ, scope_id=self.__scope_id, inst_id=inst_id, value=result)

    def __format__(self, format_spec):
        inst_id = self.__inst_id
        if not inst_id.startswith(_SCOPE_GET_PREFIX):
            inst_id = _SCOPE_GET_PREFIX + inst_id
        return inst_id

    @classmethod
    def new_from_payload(cls, payload: RPCPayload, script: 'ScriptWrapper', scope_id: str):
        data = payload.message.data
        inst_id = data.id
        typ = data.type
        result = data.result
        return cls(inst_id, None, script=script, scope_id=scope_id, typ=typ, inst_id=inst_id, value=result)

    @property
    def value(self):
        if type(self.__value) is Unset:
            result = self.__script.exports_sync.scope_get(self.__inst_id, self.__scope_id)
            self.__value = result.message.data.value
        return self.__value

    @property
    def type(self):
        return self.__typ

    def __getattribute__(self, name):
        if name.startswith('__') or name in JsHandle.__INTERNAL_PROP__:
            return object.__getattribute__(self, name)
        props = self.__props
        val = props.get(name, None)
        if val is None:
            if name in JsHandle.__LATER_PROP__:
                return object.__getattribute__(self, name)
            val = JsHandle(name, self, script=self.__script, typ='unknown', scope_id=self.__scope_id, inst_id=None)
            props[name] = val
        if type(val) is Unset:
            if REPL:
                self.__lock.acquire()
                unset_childs: Dict[str, JsHandle] = {}
                unset_props: Dict[str, Dict] = {}
                order_inst_ids = []
                for k, v in props.items():
                    if type(v) is not Unset:
                        continue
                    later_update_props = {}
                    handle = JsHandle(k, self, script=self.__script, typ=v.name, scope_id=self.__scope_id, inst_id=None, props=later_update_props)
                    props[k] = handle
                    key = handle._JsHandle__inst_id
                    unset_childs[key] = handle
                    unset_props[key] = later_update_props
                    order_inst_ids.append(key)

                self.__lock.release()
                
                batch_result = self.__script.exports_sync.enumerate_obj_props(order_inst_ids, self.__scope_id)
                for i, p in enumerate(batch_result.message.data.props):
                    key = order_inst_ids[i]
                    unset_props[key].update({
                        k: Unset(v)
                        for k, v in p.items()
                    })
                val = props[name]
            else:
                val = JsHandle(name, self, script=self.__script, typ=val.name, scope_id=self.__scope_id, inst_id=None)
                props[name] = val

        return val

    def __getitem__(self, key):
        return self.__getattribute__(str(key))


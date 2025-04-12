
from agent.rpc.resolver import RPC
from agent.rpc.message import RPCMsgType, RPCPayload
from agent.logger import FileLogger, LoggerName
from agent.config import Config
from typing import MutableMapping
from pathlib import Path
from threading import Lock


_SSL_SECRET_FILELOGGER: MutableMapping[str, FileLogger] = {}
_SSL_SECRET_FILELOGGER_LOCK: Lock = Lock()

def __get_secret_logger(tag: str) -> FileLogger:
    global _SSL_SECRET_FILELOGGER, _SSL_SECRET_FILELOGGER_LOCK

    tag = tag or 'sslkey.log'

    logger = _SSL_SECRET_FILELOGGER.get(tag, None)
    if logger is None:
        with _SSL_SECRET_FILELOGGER_LOCK:
            if tag not in _SSL_SECRET_FILELOGGER:
                conf = Config.get()
                logfile = Path(conf.script.nettools.ssl_log_secret) / tag
                logger = FileLogger(f'{LoggerName.ssl_secret_log.value}@{tag}', str(logfile))
                _SSL_SECRET_FILELOGGER[tag] = logger
    return logger



@RPC.on_message(RPCMsgType.SSL_SECRET)
def ssl_log_secret(payload: RPCPayload):
    tag = Path(payload.message.data.tag)
    logger = __get_secret_logger(tag.name)
    data = payload.message.data
    print(f'{data.label} {data.client_random} {data.secret}', file=logger)
from datetime import datetime
from typing import Optional, BinaryIO, MutableMapping, Final, Union, TypeVar
from pydantic import BaseModel
from enum import Enum
from agent.utils import ensure_filepath
import colorama
import atexit
import sys
import io


class ColoredStderr:
    @property
    def buffer(self) -> BinaryIO:
        return sys.__stderr__.buffer

    def write(self, message):
        sys.__stderr__.write(colorama.Fore.RED + message + colorama.Fore.RESET)

    def flush(self):
        sys.__stderr__.flush()

sys.stderr = ColoredStderr()



_FILE_LOGGERS: Final[MutableMapping[str, 'FileLogger']] = {}

T = TypeVar('T')

def get_logger(channel: Union[str, Enum], default: T = None) -> Union['FileLogger', T]:
    global _FILE_LOGGERS
    if isinstance(channel, Enum):
        channel = channel.value
    
    return _FILE_LOGGERS.get(channel, default)


class FileLogger:
    channel: Final[str]
    filepath: Final[str]
    _file: Optional[io.TextIOWrapper] = None
    _color: Optional[str] = None

    def __init__(self, channel: Union[str, Enum], filepath: str, file: Optional[io.TextIOWrapper] = None, auto_flush: bool = True):
        if isinstance(channel, Enum):
            channel = channel.value
        self.channel = channel
        self.filepath = filepath
        if file is None:
            _FILE_LOGGERS[channel] = self
        self._file = file
        self._auto_flush = auto_flush
        self._open_logfile()

    def _open_logfile(self):
        if self._file is None:
            ensure_filepath(self.filepath)
            self._file = open(self.filepath, 'w', buffering=1)
            atexit.register(self._close_file)
        
    def _close_file(self):
        if self._file is not None:
            self._file.close()
            self._file = None
    
    def write(self, message: str):
        if self._color:
            self._file.write(self._color + message + colorama.Fore.RESET)
        else:
            self._file.write(message)
        if self._auto_flush:
            self.flush()

    def flush(self):
        self._file.flush()

    def set_color(self, color: str):
        self._color = color

    def reset_color(self):
        self._color = None

    @classmethod
    def new_copy(cls, logger: 'FileLogger') -> 'FileLogger':
        return FileLogger(logger.channel, logger.filepath, logger._file)
    
    def clone(self) -> 'FileLogger':
        return FileLogger.new_copy(self)

    def set_alias(self, channel: Union[str, Enum]):
        global _FILE_LOGGERS
        if isinstance(channel, Enum):
            channel = channel.value
        old = _FILE_LOGGERS.get(channel, None)
        if old is not None and old is not self:
            raise NameError(f'channel[{channel}] exists already')
        _FILE_LOGGERS[channel] = self



class LoggerName(Enum):
    outerr: str = 'outerr'
    stdout: str = 'stdout'
    stderr: str = 'stderr'
    ssl_secret_log: str = 'ssl_secret_log'
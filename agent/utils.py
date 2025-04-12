from datetime import datetime
from typing import Optional, BinaryIO, MutableMapping, Final, Union, Literal, Any
from contextlib import contextmanager
from pathlib import Path
import shutil
import atexit
import io
import os
import sys


def ensure_filepath(filepath: str):
    fp = Path(filepath).absolute()
    try:
        stat = os.stat(filepath)
        create_time = stat.st_mtime
        dt = datetime.fromtimestamp(create_time)
        mv_filepath = fp.parent / f"{dt.strftime('%Y%m%d%f')}_{fp.name}"
        shutil.copyfile(filepath, mv_filepath)
    except (FileNotFoundError, NotADirectoryError):
        pass
    fp.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def ensure_filepath_open(
    file: str,
    mode: str,
    buffering: int = -1,
    encoding: Optional[str] = None,
    errors: Optional[str] = None,
    newline: Optional[str] = None,
    closefd: bool = True,
    opener: Optional[Any] = None,
):
    ensure_filepath(file)
    with open(file, mode, buffering, encoding, errors, newline, closefd, opener) as f:
        yield f
            
    

from enum import Enum
from pydantic import BaseModel
from typing import Optional
from ruamel.yaml import YAML
import codecs



class Config(BaseModel):
    app: Optional[str]
    jsfile: str

    server: 'Server'
    agent: 'Agent'
    script: 'Script'


    @classmethod
    def load_from_yaml(cls, filepath: str) -> 'Config':
        yaml = YAML(typ='safe')
        with codecs.open(filepath, 'r', 'utf-8') as f:
            data = yaml.load(f)
        cls.__inst = cls.model_validate(data)
        return cls.__inst


    @staticmethod
    def get() -> 'Config':
        if Config.__inst is None:
            raise Exception('配置未加载')
        
        return Config.__inst

    __inst: Optional['Config'] = None




class Server(BaseModel):
    device: Optional[str] = None
    servername: str = 'frida-server'
    host: str



class Agent(BaseModel):
    datadir: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None



class ScriptNetTools(BaseModel):
    ssl_log_secret: Optional[str] = None
    

class Script(BaseModel):
    nettools: ScriptNetTools

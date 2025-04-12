from agent.rpc.handler.js_handle import JsHandle
from agent.config import Config
from agent.rpc.resolver import RPC
from agent.session import SessionWrapper
from typing import Optional
from frida_tools import ps
import subprocess
import pexpect
import atexit
import click
import frida
import time
import sys
import os


def find_app_pid(device: frida.core.Device, app_id: str):
    scope = 'minimal'
    apps = device.enumerate_applications(scope=scope)
    for app in apps:
        if app.identifier.strip() == app_id:
            return app.pid

    return None



def on_session_detached(reason: str, crash: Optional[frida._frida.Crash]) -> None:
    print(reason, file=sys.stderr)
    if crash:
        print(crash.report, file=sys.stderr)
    time.sleep(1)
    if os.environ.get('REPL', False):
        print('脚本已中止，可自行退出REPL')
    


@click.group()
def cli():
    pass


@cli.command()
@click.option('-c', '--config', default='config.yml', prompt=False, help='输入配置文件路径')
def bootup_server(config: str = 'config.yml'):
    Config.load_from_yaml(config)
    conf = Config.get()
    device_arg = "-s " + conf.server.device if conf.server.device else ""
    
    _, port = conf.server.host.rsplit(':', 1)
    subprocess.run(f'adb {device_arg} forward tcp:{port} tcp:{port}', shell=True)

    adbsh = pexpect.spawn(f'adb {device_arg} shell', logfile=sys.stdout.buffer)
    # {brand}:/ $
    adbsh.expect(r'.*:\s*\/\s*[$#]')
    adbsh.sendline('su')
    # {brand}:/ #
    adbsh.expect(r'.*:\s*\/\s*[$#]')
    adbsh.sendline(f'{conf.server.servername} --version')
    adbsh.expect(r'.*:\s*\/\s*[$#]')
    adbsh.sendline(f'{conf.server.servername} -l 0.0.0.0:{port}')
    adbsh.expect([pexpect.EOF, 'Unable to start', r'.*:\s*\/\s*[$#]'], timeout=None)


@cli.command()
@click.option('-c', '--config', default='config.yml', prompt=False, help='输入配置文件路径')
def spawn(config: str = 'config.yml'):
    Config.load_from_yaml(config)
    conf = Config.get()

    if not conf.app:
        raise AttributeError('未指定目标app')

    device = frida.get_device_manager().add_remote_device(conf.server.host)
    pid = device.spawn([conf.app])
    session = SessionWrapper.from_session(device.attach(pid))
    session.on('detached', on_session_detached)

    script = session.open_script(conf.jsfile)
    script.set_logger(conf.agent.stdout, conf.agent.stderr)
    script.load()
    device.resume(pid)
    
    def on_exit():
        session.detach()

    atexit.register(on_exit)

    from ptpython.repl import embed
    os.environ['REPL'] = '1'
    embed(globals(), locals())


@cli.command()
@click.option('-p', '--pid', default=None, help='指定PID')
@click.option('-c', '--config', default='config.yml', prompt=False, help='输入配置文件路径')
def attach(pid: Optional[int] = None, config: str = 'config.yml'):
    Config.load_from_yaml(config)
    conf = Config.get()


    device = frida.get_device_manager().add_remote_device(conf.server.host)
    if pid is None and conf.app:
        pid = find_app_pid(device, conf.app)
    if pid is None:
        raise FileNotFoundError(f'找不到[{conf.app}]的app来进行attach，请指定pid')

    session = SessionWrapper.from_session(device.attach(pid))
    session.on('detached', on_session_detached)

    script = session.open_script(conf.jsfile)
    script.set_logger(conf.agent.stdout, conf.agent.stderr)
    script.load()

    def on_exit():
        session.detach()

    atexit.register(on_exit)

    from ptpython.repl import embed
    os.environ['REPL'] = '1'
    embed(globals(), locals())


if __name__ == '__main__':
    cli()
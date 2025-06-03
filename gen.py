from pathlib import Path
from typing import Final
import pexpect
from pexpect import popen_spawn
import shutil
import click
import sys
import os


ANALYKIT_RELPATH: Final[str] = './frida-analykit'


@click.group()
def cli():
    pass


@cli.command()
@click.option('-w', '--work-dir', default='./', prompt=False, help='输入要生成环境的路径')
@click.option('-k', '--kit-dir', default=ANALYKIT_RELPATH, prompt=False, help='输入分析工具所在路径')
@click.option('-r', '--npm-registry', default='', prompt=False, help='指定npm源')
def dev(work_dir: str = './', kit_dir: str = ANALYKIT_RELPATH, npm_registry: str = ''):
    work_dir: Path = Path(work_dir).absolute()
    if not work_dir.is_dir():
        raise FileExistsError(f'工作目录[{work_dir}]是文件或者不存在')

    kit_dir: Path = Path(kit_dir).absolute()
    
    if not kit_dir.exists():
        raise FileNotFoundError(f'找不到分析工具: {kit_dir}')
    ak_path: Path = Path(ANALYKIT_RELPATH).absolute()
    if not ak_path.exists():
        os.symlink(kit_dir, ak_path, target_is_directory=True)
    
    dev_tmpl_dir: Path = Path(ak_path) / 'templates' / 'dev'

    for src_path in dev_tmpl_dir.rglob('*'):
        target: Path = work_dir / src_path.name
        if target.exists():
            print(f'dst[{target}] 已存在，跳过生成.')
            continue

        if target.is_dir():
            shutil.copytree(src_path, target)
        else:
            shutil.copy(src_path, target)

    os.chdir(work_dir)
    cmd_prefix = 'cmd.exe /c ' if sys.platform == 'win32' else ''
    cmd = f'{cmd_prefix}npm install {"--registry=" + npm_registry if npm_registry else ""}'
    print(cmd)
    npmsh = popen_spawn.PopenSpawn(cmd, logfile=sys.stdout.buffer)
    npmsh.expect([pexpect.EOF, pexpect.TIMEOUT], timeout=60)


if __name__ == '__main__':
    cli()
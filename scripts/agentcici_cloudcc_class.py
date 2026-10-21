#!/usr/bin/env python3
"""共用根目录CRM配置，在应用目录维护CloudCC类；不复制凭据或源码。"""
import argparse
from pathlib import Path
import re
import subprocess
import sys


def run_class(cli, root, app_code, action, name, format_flag=None):
    root = Path(root).expanduser().resolve()
    cli = Path(cli).expanduser().resolve()
    if not cli.is_file():
        raise RuntimeError('请指定已安装CloudCC技能的tools/bin/cloudcc绝对路径')
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', app_code) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,79}', name):
        raise RuntimeError('应用标识或类名无效')
    app = (root / 'applications' / app_code).resolve()
    if not app.is_dir() or not app.is_relative_to(root / 'applications'):
        raise RuntimeError('应用目录不存在或位于项目范围外')
    if not (root / 'cloudcc-cli.config.json').is_file():
        raise RuntimeError('请先在项目根目录配置cloudcc-cli.config.json')
    if action not in ('create', 'format', 'validate', 'publish'):
        raise RuntimeError('不支持的类操作')
    if format_flag not in (None, '--write', '--check') or (format_flag and action != 'format'):
        raise RuntimeError('格式参数仅用于format操作')
    source = app / 'backend' / 'classes' / name
    if action == 'create':
        if source.exists() or source.is_symlink():
            raise RuntimeError('类目录已存在，不覆盖现有源码')
        # 当前CLI的create使用工作目录，不读取位置参数projectPath。
        return subprocess.run([str(cli), 'create', 'classes', name], cwd=app).returncode
    if not source.is_dir() or not source.resolve().is_relative_to(app):
        raise RuntimeError('应用内类目录不存在或位于应用范围外')
    java_file = source / (name + '.java')
    if java_file.is_symlink() or not java_file.is_file():
        raise RuntimeError('应用内缺少类源码')
    projection = root / 'backend' / 'classes' / name
    # 拒绝覆盖任何既有资源或其他操作持有的映射。
    if projection.exists() or projection.is_symlink():
        raise RuntimeError('根目录已有同名类路径或正在执行该类操作，请先核对，不覆盖')
    created_dirs = []
    linked = False
    try:
        for directory in (root / 'backend', root / 'backend' / 'classes'):
            if directory.is_symlink():
                raise RuntimeError('根目录类映射的父目录不能是符号链接')
            if not directory.exists():
                directory.mkdir()
                created_dirs.append(directory)
        projection.symlink_to(source, target_is_directory=True)
        linked = True
        command = [str(cli), action, 'classes', name, str(root)]
        if action == 'format':
            command.append(format_flag or '--check')
        return subprocess.run(command, cwd=root).returncode
    finally:
        if linked and projection.is_symlink() and projection.resolve() == source.resolve():
            projection.unlink()
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError:
                pass  # 不删除其他进程或用户创建的内容。


def main():
    parser = argparse.ArgumentParser(description='根目录共享CRM配置，应用内保存类源码')
    parser.add_argument('--cli', required=True, help='已安装CloudCC技能的tools/bin/cloudcc绝对路径')
    parser.add_argument('--root', required=True, help='共用配置所在的项目根目录')
    parser.add_argument('--app', required=True, help='applications下的应用标识')
    parser.add_argument('action', choices=['create', 'format', 'validate', 'publish'])
    parser.add_argument('name')
    formatting = parser.add_mutually_exclusive_group()
    formatting.add_argument('--write', action='store_true')
    formatting.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        return run_class(args.cli, args.root, args.app, args.action, args.name,
                         '--write' if args.write else '--check' if args.check else None)
    except (RuntimeError, OSError) as error:
        print(str(error) if isinstance(error, RuntimeError) else 'CloudCC类操作失败，请检查目录及执行权限', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

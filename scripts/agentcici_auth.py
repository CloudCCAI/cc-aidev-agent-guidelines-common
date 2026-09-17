#!/usr/bin/env python3
"""Base64 login and macOS Keychain persistence. Never execute decoded text."""
import argparse
import base64
import binascii
import getpass
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import uuid
from urllib.parse import urlsplit

NAMES = ('AGENTCICI_BASE_URL', 'AGENTCICI_CLIENT_ID', 'AGENTCICI_CLIENT_SECRET')
SERVICE = 'AgentCiCi Developer Login'


def config_path():
    return Path.home() / '.config' / 'agentcici' / 'login.json'


def decode_login(encoded):
    try:
        text = base64.b64decode(''.join(encoded.split()), validate=True).decode('utf-8')
        tokens = shlex.split(text, comments=False, posix=True)
        values = {}
        if len(tokens) != 6:
            raise ValueError()
        for i in range(0, len(tokens), 2):
            name, separator, value = tokens[i + 1].partition('=')
            if tokens[i] != 'export' or not separator or name not in NAMES or name in values or not value or '\x00' in value:
                raise ValueError()
            values[name] = value
        url = urlsplit(values[NAMES[0]])
        if (not url.hostname or url.username or url.password or url.query or url.fragment
                or url.path not in ('', '/') or (url.scheme != 'https' and not
                    (url.scheme == 'http' and url.hostname in ('localhost', '127.0.0.1', '::1')))):
            raise ValueError()
        values[NAMES[0]] = values[NAMES[0]].rstrip('/')
        return values
    except (ValueError, KeyError, UnicodeError, binascii.Error):
        raise RuntimeError('登录信息无效，请复制完整 Base64 信息；地址必须为 HTTPS 或本机开发地址') from None


def keychain(action, account, secret=None):
    if sys.platform != 'darwin':
        raise RuntimeError('持久登录目前支持 macOS 钥匙串；其他系统请使用三项环境变量')
    args = ['/usr/bin/security', action, '-s', SERVICE, '-a', account]
    if action == 'add-generic-password':
        args += ['-U', '-w', secret]
    elif action == 'find-generic-password':
        args += ['-w']
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('无法访问 AgentCiCi 钥匙串项，请检查系统钥匙串授权')
    return result.stdout[:-1] if result.stdout.endswith('\n') else result.stdout


def read_config():
    try:
        return json.loads(config_path().read_text())
    except FileNotFoundError:
        return None
    except (ValueError, OSError):
        raise RuntimeError('本地登录配置无法读取，请重新登录') from None


def credentials():
    if any(os.environ.get(name) for name in NAMES):
        if not all(os.environ.get(name) for name in NAMES):
            raise RuntimeError('环境变量登录必须同时提供地址、Client ID 和 Client Secret；不与已保存身份混用')
        return {name: os.environ[name] for name in NAMES}
    saved = read_config()
    if not saved:
        raise RuntimeError('尚未登录，请运行 agentcici_auth.py login 并输入 Base64 登录信息')
    return {NAMES[0]: saved['baseUrl'], NAMES[1]: saved['clientId'], NAMES[2]: keychain('find-generic-password', saved['account'])}


def login(encoded):
    from agentcici_manage import Client
    values = decode_login(encoded)
    if sys.platform != 'darwin':
        raise RuntimeError('持久登录目前支持 macOS 钥匙串')
    client = Client(values)
    try:
        client.exchange()
    except Exception:
        raise RuntimeError('登录验证失败；请检查地址、凭据状态与网络，原登录配置保持不变') from None
    old = read_config()
    account = uuid.uuid4().hex
    keychain('add-generic-password', account, values[NAMES[2]])
    path = config_path()
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            os.chmod(temporary, 0o600)
            json.dump({'baseUrl': values[NAMES[0]], 'clientId': values[NAMES[1]], 'account': account}, stream)
        os.replace(temporary, path)
    except Exception:
        if temporary:
            temporary.unlink(missing_ok=True)
        keychain('delete-generic-password', account)
        raise RuntimeError('无法保存登录配置') from None
    if old:
        try:
            keychain('delete-generic-password', old['account'])
        except RuntimeError:
            print('新登录已保存；旧钥匙串项未清理，可在钥匙串访问中移除', file=sys.stderr)
    return {'status': 'logged_in', 'baseUrl': values[NAMES[0]], 'clientId': values[NAMES[1]]}


def main():
    parser = argparse.ArgumentParser(description='使用复制的 Base64 信息登录并保存到 macOS 钥匙串')
    parser.add_argument('command', choices=['login', 'status', 'logout'])
    args = parser.parse_args()
    try:
        if args.command == 'login':
            encoded = getpass.getpass('Base64 登录信息（输入不回显）：') if sys.stdin.isatty() else sys.stdin.read()
            result = login(encoded)
        else:
            saved = read_config()
            if args.command == 'logout' and saved:
                keychain('delete-generic-password', saved['account'])
                config_path().unlink()
                saved = None
            result = {'status': 'saved' if saved else 'not_logged_in'}
            if saved:
                result.update(baseUrl=saved['baseUrl'], clientId=saved['clientId'])
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (RuntimeError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

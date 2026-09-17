#!/usr/bin/env python3
"""Build and validate application request archives; never execute archived code."""
import argparse
import hashlib
import io
from application_manifest import compile_manifest, missing
import json
import pathlib
import re
import stat
import sys
import zipfile
import urllib.request
import urllib.error
import uuid
from agentcici_manage import Client

LIMIT = 100 * 1024 * 1024
FORMAT = 'agentcici-application-request'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_zip(data):
    require(len(data) <= LIMIT, 'ZIP 超过 100 MiB')
    result = {}
    names = set()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        require(len(entries) <= 10000, 'ZIP 条目过多')
        require(sum(i.file_size for i in entries) <= LIMIT, 'ZIP 解压大小超过 100 MiB')
        for item in entries:
            name = item.filename
            path = pathlib.PurePosixPath(name)
            require(not name.startswith('/') and '\\' not in name and ':' not in name
                    and '..' not in path.parts and name not in names, 'ZIP 路径非法或重复')
            names.add(name)
            require(not stat.S_ISLNK(item.external_attr >> 16), '不支持符号链接')
            if not item.is_dir():
                result[name] = archive.read(item)
    return result


def zip_bytes(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    return buffer.getvalue()


def encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2).encode()


def refs(items):
    require(isinstance(items, list), '资源必须为数组')
    result = {}
    for item in items:
        ref = item.get('ref', '')
        require(re.fullmatch(r'[a-z][a-z0-9-]{0,63}', ref), '资源 ref 非法')
        require(ref not in result, '资源 ref 重复')
        result[ref] = item
    return result


def validate(files):
    manifest = json.loads(files['application.json'])
    require(manifest.get('format') == FORMAT and manifest.get('formatVersion') == 1, '应用包格式不支持')
    require(re.fullmatch(r'[a-z][a-z0-9-]{1,63}', manifest.get('appCode', '')), '应用代码非法')
    require(re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', manifest.get('version', '')), '版本非法')
    require(isinstance(manifest.get('name'), str) and bool(manifest['name'].strip()), '缺少应用名称')
    if 'installationManifest' in manifest:
        installation = manifest['installationManifest']
        require(isinstance(installation, dict) and installation.get('schemaVersion') == 1 and isinstance(installation.get('steps'), list) and 1 <= len(installation['steps']) <= 30, '安装清单需要 schemaVersion=1 和 1 至 30 个步骤')
        render = installation.get('renderConfig')
        require(isinstance(render, dict) and render.get('renderer') in ['iframe', 'shadow-dom'], '渲染方式无效')
        positions = render.get('positions', [])
        require(isinstance(positions, list) and 1 <= len(positions) <= 7 and all(isinstance(p, str) and p in ['float', 'right', 'fullscreen', 'detail-right', 'list-right', 'dialog', 'home'] for p in positions) and len(set(positions)) == len(positions), '展示位置无效或重复')
        from urllib.parse import urlsplit
        entry = render.get('entryUrl', '')
        require(isinstance(entry, str), '加载地址必须是字符串')
        if entry.strip():
            url = urlsplit(entry.strip())
            require(url.scheme in ['http', 'https'] and url.hostname and not url.username and not url.password, '加载地址必须为 HTTP(S)')
        else:
            require(render['renderer'] == 'iframe' or render.get('entryPath'), 'Shadow DOM 必须提供 JS 地址或包内入口')
        require(render.get('closeBehavior') in ['hide', 'confirm-destroy'], '关闭方式无效')
        require(render.get('hostLayer') in ['content', 'assistant'], '宿主层级无效')
        authentication = render.get('authentication')
        if authentication is not None:
            require(isinstance(authentication, dict), '宿主认证配置无效')
            query = authentication.get('query')
            require(authentication.get('type') == 'cloudcc-sso-ticket'
                    and isinstance(query, dict) and 1 <= len(query) <= 8
                    and all(re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,31}', key) and isinstance(value, str) and len(value) <= 256 for key, value in query.items())
                    and isinstance(authentication.get('targetPath'), str) and authentication['targetPath'].startswith('/') and not authentication['targetPath'].startswith('//')
                    and re.fullmatch(r'[a-z][a-z0-9_]{1,31}', authentication.get('ticketPrefix', ''))
                    and (not authentication.get('localeParam') or re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,31}', authentication['localeParam'])), '宿主认证配置无效')
        agent_runtime = installation.get('agentRuntime')
        if agent_runtime is not None:
            require(isinstance(agent_runtime, dict)
                    and re.fullmatch(r'[a-z][a-z0-9-]{0,63}', agent_runtime.get('agentId', ''))
                    and agent_runtime.get('keyType') in ['cloudcc', 'standard'], '智能体运行配置无效')
    checksums = manifest['sha256']
    require(set(checksums) == set(files) - {'application.json'}, '文件清单不匹配')
    require(all(digest(files[k]) == v for k, v in checksums.items()), '文件摘要不匹配')
    require(manifest['web'] == {'file': 'site.zip', 'entry': 'index.html'}, '站点入口非法')
    site = read_zip(files['site.zip'])
    require('index.html' in site, '站点缺少根层 index.html')
    for name in site:
        path = pathlib.PurePosixPath(name)
        require(not any(p.startswith('.') or p == 'node_modules' for p in path.parts)
                and path.suffix not in {'.map', '.pem', '.key'}, '站点包含禁止发布的文件')
    skills = refs(manifest['skills'])
    agents = refs(manifest['agents'])
    knowledge = refs(manifest.get('knowledgeBases', []))
    require(len(agents) + int('platformAgent' in manifest) <= 1, '应用包只能包含一个智能体')
    if 'platformAgent' in manifest:
        require(re.fullmatch(r'[a-z][a-z0-9-]{0,63}', manifest['platformAgent'].get('ref', '')), '平台智能体引用无效')
        require(not skills and not knowledge, '平台智能体复用已有组织依赖')
        require(manifest.get('installationManifest', {}).get('agentRuntime', {}).get('agentId') == manifest['platformAgent']['ref'], '平台智能体运行引用不一致')
    elif agents and 'agentRuntime' in manifest.get('installationManifest', {}):
        require(manifest.get('installationManifest', {}).get('agentRuntime', {}).get('agentId') == next(iter(agents)), '自定义智能体运行引用不一致')
    render = manifest.get('installationManifest', {}).get('renderConfig', {})
    if 'entryPath' in render:
        require(re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*(?:\.[A-Za-z0-9_-]+)+', render['entryPath']) and render['entryPath'] in site, '包内入口不存在或路径无效')
        require(not render.get('entryUrl'), '包内入口与外部地址不能同时配置')
    expected = {'application.json', 'site.zip'}
    if 'cloudcc/menu.json' in files: expected.add('cloudcc/menu.json')
    else: require(bool(manifest.get('installationManifest', {}).get('steps')), '需要安装入口')
    for ref, skill in skills.items():
        require(skill['file'] == f'skills/{ref}.zip', '技能文件路径非法')
        expected.add(skill['file'])
        package = read_zip(files[skill['file']])
        sm = json.loads(package['manifest.json'])
        require(sm.get('format') == 'universal-skill-package' and sm.get('formatVersion') == '1.0'
                and 'SKILL.md' in package, '技能需为平台标准导出包')
    for ref, agent in agents.items():
        require(agent['file'] == f'agents/{ref}.ciciagent', '智能体文件路径非法')
        expected.add(agent['file'])
        require(len(files[agent['file']]) <= 5 * 1024 * 1024, '智能体包超过 5 MiB')
        package = read_zip(files[agent['file']])
        require(set(package) == {'manifest.json', 'agent.json'}, '智能体包文件不匹配')
        am = json.loads(package['manifest.json'])
        require(am.get('format') == 'agentcici-agent-package' and am.get('formatVersion') == 1
                and am.get('snapshot') == 'SAVED_DRAFT', '智能体需为原生导出包')
        require(am.get('sha256') == digest(package['agent.json']), '智能体包摘要错误')
        payload = json.loads(package['agent.json'])
        require(not payload.get('tools') and not payload.get('agentToolRefs'), '本期不支持工具依赖打包')
        for field, dependencies, targets in [('skillBindings', 'skills', skills), ('knowledgeBindings', 'knowledge', knowledge)]:
            bindings = agent.get(field, {})
            require(set(bindings) == {d['ref'] for d in payload.get(dependencies, [])}, f'{field} 未完整映射')
            require(all(v in targets for v in bindings.values()), f'{field} 目标不存在')
    require(set(files) == expected, '包含未声明文件')
    if 'cloudcc/menu.json' in files:
        menu = json.loads(files['cloudcc/menu.json'])
        require(menu.get('type') == 'script' and menu.get('tabName') and menu.get('pname'), '需要脚本菜单')
        require('__AGENTCICI_SITE_URL__' in menu.get('functioncode', ''), '菜单缺少安装时站点地址占位符')
    return manifest


def package(source, output):
    source = pathlib.Path(source).resolve()
    config = json.loads(source.read_text())
    root = source.parent
    if config.get("schemaVersion") == 2:
        config = compile_manifest(config, root)
    def local(name):
        candidate = root / name
        require(not candidate.is_symlink(), '不支持符号链接')
        resolved = candidate.resolve()
        require(resolved.is_relative_to(root), '输入路径必须位于项目目录内')
        return resolved
    directory = local(config['web']['directory'])
    require(directory.is_dir(), '构建目录不存在')
    site = {}
    size = 0
    for path in sorted(directory.rglob('*')):
        require(not path.is_symlink(), '构建目录不能包含符号链接')
        if path.is_file():
            relative = path.relative_to(directory)
            require(not any(p.startswith('.') or p == 'node_modules' for p in relative.parts)
                    and path.suffix not in {'.map', '.pem', '.key'}, '构建目录包含禁止发布的文件')
            size += path.stat().st_size
            require(size <= LIMIT, '站点产物超过 100 MiB')
            site[relative.as_posix()] = path.read_bytes()
    files = {'site.zip': zip_bytes(site)}
    manifest = {k: config[k] for k in ['appCode', 'name', 'version']}
    manifest.update(format=FORMAT, formatVersion=1, summary=config.get('summary', ''),
                    web={'file': 'site.zip', 'entry': 'index.html'}, knowledgeBases=config.get('knowledgeBases', []))
    if 'appType' in config: manifest['appType'] = config['appType']
    if 'platformAgent' in config: manifest['platformAgent'] = config['platformAgent']
    if 'installationManifest' in config:
        manifest['installationManifest'] = config['installationManifest']
    for kind, extension in [('agents', 'ciciagent'), ('skills', 'zip')]:
        manifest[kind] = []
        for ref, item in refs(config.get(kind, [])).items():
            path = local(item['file'])
            require(path.stat().st_size <= LIMIT, '资源包过大')
            name = f'{kind}/{ref}.{extension}'
            files[name] = path.read_bytes()
            entry = {'ref': ref, 'file': name}
            if kind == 'agents':
                entry.update(skillBindings=item.get('skillBindings', {}), knowledgeBindings=item.get('knowledgeBindings', {}))
            manifest[kind].append(entry)
    if 'menu' in config:
        menu = config['menu']
        require(menu.get('type') == 'script', '菜单必须为 script')
        files['cloudcc/menu.json'] = encode({'tabName': menu['tabName'], 'pname': menu['pname'], 'type': 'script',
            'functioncode': menu.get('functioncode') or (pathlib.Path(__file__).resolve().parent.parent / 'assets/application-menu.js').read_text(encoding='utf-8').replace('__APP_CODE__', json.dumps(config['appCode'])).replace('__SDK_URL__', json.dumps(menu.get('sdkUrl', 'https://uat.agentcici.com/sdk/agentcici-app@1.1.0.js')))})
    manifest['sha256'] = {name: digest(data) for name, data in files.items()}
    files['application.json'] = encode(manifest)
    validate(files)
    data = zip_bytes(files)
    read_zip(data)
    output = pathlib.Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        stream.write(data)
    return {'status': 'prepared', 'path': str(output.resolve()), 'sha256': digest(data)}


def main():
    parser = argparse.ArgumentParser(description='AI 应用发布申请包：准备、校验、提交与查询')
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('package')
    build.add_argument('--manifest', required=True)
    build.add_argument('--output', required=True)
    preflight = commands.add_parser('check', help='列出源清单缺失必填项，供发布前问答')
    preflight.add_argument('--manifest', required=True)
    submit = commands.add_parser('submit', help='提交待审核申请，不直接发布')
    submit.add_argument('file')
    draft = commands.add_parser('draft', help='从本组织上传申请创建市场草稿，不上架')
    draft.add_argument('request_id')
    status = commands.add_parser('status')
    status.add_argument('request_id')
    check = commands.add_parser('validate')
    check.add_argument('file')
    args = parser.parse_args()
    try:
        if args.command == 'check':
            source = pathlib.Path(args.manifest).resolve()
            config = json.loads(source.read_text())
            absent = missing(config)
            result = {'status': 'incomplete' if absent else 'complete', 'missing': absent}
            if not absent: compile_manifest(config, source.parent)
        elif args.command == 'draft':
            uuid.UUID(args.request_id)
            result = Client().request('POST', '/openapi/v1/management/application-requests/' + args.request_id + '/draft', {})
        elif args.command == 'status':
            uuid.UUID(args.request_id)
            result = Client().request('GET', '/openapi/v1/management/application-requests/' + args.request_id)
        elif args.command == 'package':
            result = package(args.manifest, args.output)
        else:
            path = pathlib.Path(args.file)
            require(path.stat().st_size <= LIMIT, '包过大')
            data = path.read_bytes()
            manifest = validate(read_zip(data))
            result = {'status': 'valid', 'appCode': manifest['appCode'], 'sha256': digest(data)}
            if args.command == 'submit':
                client = Client()
                boundary = 'cici-' + uuid.uuid4().hex
                body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="application.zip"\r\nContent-Type: application/zip\r\n\r\n'.encode()
                        + data + f'\r\n--{boundary}--\r\n'.encode())
                request = urllib.request.Request(client.base_url + '/openapi/v1/management/application-requests',
                    data=body, method='POST', headers={'Authorization': 'Bearer ' + client.exchange(),
                    'Content-Type': 'multipart/form-data; boundary=' + boundary, 'Accept': 'application/json'})
                try:
                    with urllib.request.urlopen(request, timeout=120) as response:
                        envelope = json.load(response)
                except urllib.error.HTTPError as error:
                    raise RuntimeError(f'申请提交返回 HTTP {error.code}；核对服务端版本与 application.submit 权限') from None
                except (urllib.error.URLError, TimeoutError):
                    raise RuntimeError('申请提交结果未知；可重交同一原包，服务端按 org + SHA-256 去重') from None
                require(envelope.get('success'), '申请接收失败')
                result = envelope['data']
                request_id = result['id']
                try:
                    result['draft'] = client.request('POST', '/openapi/v1/management/application-requests/' + request_id + '/draft', {})
                except (RuntimeError, OSError) as error:
                    raise RuntimeError(f'上传已成功，申请 ID={request_id}；草稿未确认创建：{error}。可用 draft {request_id} 重试') from None
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, AttributeError, OSError, zipfile.BadZipFile, RuntimeError) as error:
        print(f'申请包处理失败：{error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

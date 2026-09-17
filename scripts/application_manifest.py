"""Compile the developer-facing resource manifest to the package/CRM contract."""
import copy
import hashlib
import json
import pathlib
import re
from urllib.parse import urlsplit

POSITIONS = {'global-floating': 'float', 'global-right': 'right', 'detail-right': 'detail-right',
             'list-right': 'list-right', 'dialog': 'dialog', 'page-content': 'home', 'fullscreen': 'fullscreen'}
TRIGGERS = {'global-floating': 'clientScript', 'create-button': 'clientScript',
            'edit-button': 'clientScript', 'menu': 'menu', 'detail-button': 'button', 'list-button': 'button'}


def default_launchers(config):
    app_code = config.get('appCode', '')
    name = config.get('name', '')
    if config.get('appType') != 'web' or not app_code or not name:
        return None
    pname = app_code.replace('-', '_')
    if len(pname) > 20:
        pname = f'{pname[:13]}_{hashlib.sha256(app_code.encode()).hexdigest()[:6]}'
    return [{'id': 'default-menu', 'name': name, 'trigger': 'menu',
             'positions': ['page-content'], 'payload': {'pname': pname}}]


def missing(config):
    fields = [key for key in ('appCode', 'name', 'version', 'summary', 'appType', 'outputDir', 'entry', 'renderer')
              if not isinstance(config.get(key), str) or not config[key].strip()]
    if 'connectedApplications' in config and not isinstance(config.get('connectedApplications'), bool):
        fields.append('connectedApplications')
    if not isinstance(config.get('host'), dict):
        fields.append('host')
    launchers = config.get('launchers') if 'launchers' in config else default_launchers(config)
    if not isinstance(launchers, list) or not launchers:
        fields.append('launchers')
    else:
        for i, launcher in enumerate(launchers):
            if not isinstance(launcher, dict):
                fields.append(f'launchers[{i}]')
                continue
            for key in ('id', 'name', 'trigger', 'positions', 'payload'):
                if not launcher.get(key): fields.append(f'launchers[{i}].{key}')
    agent = config.get('agent')
    if agent is not None:
        if not isinstance(agent, dict): fields.append('agent')
        else:
            for key in ('type', 'ref'):
                if not agent.get(key): fields.append('agent.' + key)
            if agent.get('type') == 'custom' and not agent.get('file'): fields.append('agent.file')
    return fields


def compile_manifest(config, root):
    absent = missing(config)
    if absent: raise ValueError('请通过问答补齐必填项：' + ', '.join(absent))
    config = copy.deepcopy(config)
    if 'launchers' not in config:
        config['launchers'] = default_launchers(config)
    if config.get('schemaVersion') != 2 or config['appType'] != 'web':
        raise ValueError('源清单需要 schemaVersion=2、appType=web')
    if not re.fullmatch(r'[0-9]\.[0-9]\.[0-9]', config['version']):
        raise ValueError('版本需要三位0–9数字，逢9进位')
    renderer = config['renderer']
    if renderer not in ('iframe', 'shadow-dom'): raise ValueError('渲染方式无效')
    entry = config['entry']
    render = {'renderer': renderer, 'positions': []}
    url = urlsplit(entry)
    if url.scheme:
        if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password:
            raise ValueError('应用地址必须为HTTP(S)，不含凭据')
        render['entryUrl'] = entry
    else:
        if not re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*(?:\.[A-Za-z0-9_-]+)+', entry):
            raise ValueError('包内入口必须是安全相对文件路径')
        render['entryPath'] = entry
    host = config['host']
    close_behavior = host.get('closeBehavior')
    host_layer = host.get('hostLayer')
    if close_behavior not in ('hide', 'confirm-destroy'): raise ValueError('关闭方式无效')
    if host_layer not in ('content', 'assistant'): raise ValueError('宿主层级无效')
    render.update(closeBehavior=close_behavior, hostLayer=host_layer)
    authentication = host.get('authentication')
    if authentication is not None:
        if not isinstance(authentication, dict) or authentication.get('type') != 'cloudcc-sso-ticket':
            raise ValueError('宿主认证配置无效')
        query = authentication.get('query')
        if (not isinstance(query, dict) or not query or len(query) > 8
                or any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,31}', key) or not isinstance(value, str) or len(value) > 256 for key, value in query.items())):
            raise ValueError('宿主认证查询参数无效')
        target_path = authentication.get('targetPath', '')
        ticket_prefix = authentication.get('ticketPrefix', '')
        locale_param = authentication.get('localeParam', '')
        if (not isinstance(target_path, str) or not target_path.startswith('/') or target_path.startswith('//') or len(target_path) > 512
                or not isinstance(ticket_prefix, str) or not re.fullmatch(r'[a-z][a-z0-9_]{1,31}', ticket_prefix)
                or locale_param and (not isinstance(locale_param, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,31}', locale_param))):
            raise ValueError('宿主认证路径或票据前缀无效')
        render['authentication'] = copy.deepcopy(authentication)
    result = {k: config[k] for k in ('appCode', 'name', 'version', 'summary', 'appType')}
    result.update(web={'directory': config['outputDir']}, agents=[], skills=[], knowledgeBases=[])
    agent = config.get('agent')
    if agent:
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', agent['ref']): raise ValueError('智能体ref无效')
        key_type = agent.get('keyType', 'cloudcc')
        if key_type not in ('cloudcc', 'standard'): raise ValueError('智能体密钥类型只能是cloudcc/standard')
        if agent['type'] == 'platform':
            if any(agent.get(k) for k in ('file', 'skills', 'knowledges')):
                raise ValueError('平台智能体复用当前org实例和关联，不导出或重绑依赖')
            result['platformAgent'] = {'ref': agent['ref']}
        elif agent['type'] == 'custom':
            result['skills'] = agent.get('skills', [])
            result['knowledgeBases'] = agent.get('knowledges', [])
            result['agents'] = [{'ref': agent['ref'], 'file': agent['file'],
                'skillBindings': {s['bindingRef']: s['ref'] for s in result['skills']},
                'knowledgeBindings': {k['bindingRef']: k['ref'] for k in result['knowledgeBases']}}]
        else: raise ValueError('智能体类型只能是platform/custom')
    steps, ids, triggers = [], set(), set()
    for launcher in sorted(config['launchers'], key=lambda item: item.get('order', 0)):
        key, trigger = launcher['id'], launcher['trigger']
        if not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_-]{0,63}', key) or key in ids: raise ValueError('入口id无效或重复')
        ids.add(key)
        if trigger not in TRIGGERS: raise ValueError('触发方式无效')
        if trigger in triggers: raise ValueError('同一应用每种trigger只能配置一项')
        triggers.add(trigger)
        if trigger in ('create-button', 'edit-button') and not launcher.get('file'):
            raise ValueError('新建/编辑页底部按钮需提供已对接CRM页生命周期的业务脚本file，不能在页面加载时直接打开应用')
        positions = launcher['positions']
        if not isinstance(positions, list) or not positions or any(not isinstance(p, str) or p not in POSITIONS for p in positions) or len(set(positions)) != len(positions):
            raise ValueError('展示位置无效')
        for position in positions:
            if POSITIONS[position] not in render['positions']: render['positions'].append(POSITIONS[position])
        # The bootstrap contains only the application identity. Display metadata lives in the manifest.
        method = 'start' if trigger == 'global-floating' else 'mount'
        script = """(async function () {
  const appCode = %s;
  if (!window.AgentCiCiApp) {
    const src = '__AGENTCICI_SDK_URL__';
    window.__agentCiCiAppSdkLoad ||= new Promise((resolve, reject) => {
      const script = document.createElement('script');
      const url = new URL(src, document.baseURI);
      url.searchParams.set('_t', new Date().getTime());
      script.src = url.href;
      script.onload = () => { script.remove(); resolve(); };
      script.onerror = () => { script.remove(); delete window.__agentCiCiAppSdkLoad; reject(new Error('AI 应用 SDK 加载失败，请重试。')); };
      document.head.append(script);
    });
    await window.__agentCiCiAppSdkLoad;
  }
  await window.AgentCiCiApp.%s({ appCode });
})().catch(error => window.alert(error.message || '应用打开失败。'));""" % (json.dumps(config['appCode'], ensure_ascii=False), method)
        if launcher.get('file'):
            file = root / launcher['file']
            if file.is_symlink() or not file.resolve().is_relative_to(root): raise ValueError('脚本必须位于应用目录内')
            script = file.read_text(encoding='utf-8')
        payload = copy.deepcopy(launcher['payload'])
        kind = TRIGGERS[trigger]
        if trigger in ('create-button', 'edit-button', 'detail-button', 'list-button') and not launcher.get('objects'):
            raise ValueError('请通过CloudCC开发技能查询对象并让客户选择入口对象范围')
        if kind == 'clientScript':
            payload.update(scriptName=launcher['name'], scriptContent=script)
        elif kind == 'menu':
            payload.update(tabName=launcher['name'], type='script', functioncode=script)
        else:
            if not payload.get('objid') or not isinstance(payload.get('tpSysButtonVO'), dict):
                raise ValueError('按钮需要查询确认的objid和tpSysButtonVO')
            payload['tpSysButtonVO'].pop('functioncode', None)
            payload['tpSysButtonVO']['functionCode'] = script
        step = {'key': key, 'type': kind, 'label': launcher['name'], 'payload': payload}
        if launcher.get('placement'): step['placement'] = launcher['placement']
        steps.append(step)
    installation = {'schemaVersion': 1, 'steps': steps, 'requiresConnectedApplication': config.get('connectedApplications', True), 'renderConfig': render,
                    'application': {k: config[k] for k in ('appCode', 'name', 'summary')},
                    'launchers': [{k: value for k, value in launcher.items() if k in ('id', 'name', 'icon', 'trigger', 'positions', 'objects', 'order')}
                                  for launcher in config['launchers']]}
    if agent: installation['agentRuntime'] = {'agentId': agent['ref'], 'keyType': key_type}
    result['installationManifest'] = installation
    return result

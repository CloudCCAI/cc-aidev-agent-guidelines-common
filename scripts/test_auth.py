import base64
import json
import os
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch
import agentcici_auth as auth
from agentcici_manage import Client


def encoded(secret="test'中文$HOME"):
    values = ('https://cici.example.test', 'client', secret)
    return base64.b64encode('\n'.join('export '+k+'='+shlex.quote(v) for k,v in zip(auth.NAMES, values)).encode()).decode()


class AuthTest(unittest.TestCase):
    def test_decode_without_shell_execution(self):
        self.assertEqual(auth.decode_login(encoded())[auth.NAMES[2]], "test'中文$HOME")

    def test_reject_invalid_and_extra_commands(self):
        for text in ['invalid!', base64.b64encode(b'export X=y; whoami').decode()]:
            with self.assertRaises(RuntimeError): auth.decode_login(text)

    def test_reject_remote_http(self):
        text = base64.b64decode(encoded()).decode().replace('https:', 'http:')
        with self.assertRaises(RuntimeError): auth.decode_login(base64.b64encode(text.encode()).decode())

    def test_save_only_after_verification_and_reload(self):
        with tempfile.TemporaryDirectory() as d, patch.object(auth, 'config_path', return_value=Path(d)/'login.json'), patch.object(auth.sys, 'platform', 'darwin'), patch.object(Client, 'exchange', return_value='ephemeral-token'), patch.object(auth, 'keychain', return_value='stored-secret') as keychain, patch.dict(os.environ, {}, clear=True):
            auth.login(encoded())
            saved = json.loads((Path(d)/'login.json').read_text())
            self.assertEqual(set(saved), {'baseUrl', 'clientId', 'account'})
            self.assertEqual((Path(d)/'login.json').stat().st_mode & 0o777, 0o600)
            client = Client()
            self.assertEqual(client.client_secret, 'stored-secret')
            self.assertEqual(client.token, '')
            keychain.assert_any_call('find-generic-password', saved['account'])

    def test_failed_login_keeps_existing_configuration(self):
        with tempfile.TemporaryDirectory() as d, patch.object(auth, 'config_path', return_value=Path(d)/'login.json'), patch.object(auth.sys, 'platform', 'darwin'), patch.object(Client, 'exchange', side_effect=RuntimeError('secret error')), patch.object(auth, 'keychain') as keychain:
            (Path(d)/'login.json').write_text('{"previous":true}')
            with self.assertRaisesRegex(RuntimeError, '登录验证失败'): auth.login(encoded())
            self.assertEqual((Path(d)/'login.json').read_text(), '{"previous":true}')
            keychain.assert_not_called()

    def test_partial_environment_does_not_mix_identities(self):
        with patch.dict(os.environ, {auth.NAMES[0]:'https://other.example.test'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, '不与已保存身份混用'): Client()

    def test_full_environment_needs_no_keychain(self):
        with patch.dict(os.environ, dict(zip(auth.NAMES, ['https://cici.example.test','client','secret'])), clear=True), patch.object(auth, 'keychain') as keychain:
            self.assertEqual(Client().client_id, 'client')
            keychain.assert_not_called()


if __name__ == '__main__': unittest.main()

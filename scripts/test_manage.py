import unittest
from unittest.mock import Mock
from agentcici_manage import parser, execute

class ManagementTests(unittest.TestCase):
    def run_command(self, *args, client=None):
        client = client or Mock()
        execute(client, parser().parse_args(args))
        return client

    def test_skill_partial_update_preserves_definition(self):
        client = Mock()
        client.request.return_value = {'id': 9, 'skillCode': 'birthday', 'name': 'Old', 'runtimeApis': [], 'enabled': True}
        self.run_command('skills', 'update', '9', '--json', '{"name":"New"}', client=client)
        client.request.assert_called_with('PUT', '/openapi/v1/management/skills/9',
            {'skillCode': 'birthday', 'name': 'New', 'runtimeApis': [], 'enabled': True})

    def test_mcp_update_preserves_other_fields(self):
        client = Mock()
        client.request.return_value = {'id': 3, 'name': 'Existing', 'url': 'https://example.com/mcp',
                                       'transportType': 'streamableHttp', 'enabled': True,
                                       'clientSecretConfigured': True}
        self.run_command('mcp', 'update', '3', '--json', '{"name":"New"}', client=client)
        client.request.assert_called_with('PUT', '/openapi/v1/management/mcp-servers/3',
            {'name': 'New', 'url': 'https://example.com/mcp', 'transportType': 'streamableHttp', 'enabled': True})

    def test_mcp_tool_discovery_and_cached_read(self):
        c = self.run_command('mcp', 'discover', '3')
        c.request.assert_called_once_with('POST', '/openapi/v1/management/mcp-servers/3/discover')
        c = self.run_command('mcp', 'tools', '3')
        c.request.assert_called_once_with('GET', '/openapi/v1/management/mcp-servers/3/tools')

    def test_existing_tool_catalog_is_read_only(self):
        import contextlib
        import io
        c = self.run_command('tools', 'list')
        c.request.assert_called_once_with('GET', '/openapi/v1/management/tools')
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser().parse_args(('tools', 'create'))

    def test_compile_and_publish_use_explicit_version(self):
        c = self.run_command('agents', 'publish', 'a', '--version-no', '7')
        c.request.assert_called_once_with('POST', '/openapi/v1/management/agents/a/publish', {'versionNo': 7})
        c = self.run_command('skills', 'compile', '9')
        c.request.assert_called_once_with('POST', '/openapi/v1/management/skills/9/compile', {})

    def test_binding_isolated_and_explicit_clear(self):
        c = self.run_command('agents', 'bind-knowledge', 'a', '--json', '{"knowledgeBaseIds":[]}')
        c.request.assert_called_once_with('PATCH', '/openapi/v1/management/agents/a', {'knowledgeBaseIds': []})
        with self.assertRaises(RuntimeError):
            self.run_command('agents', 'bind-tools', 'a', '--json', '{"toolIds":[],"channels":[]}')
        with self.assertRaises(RuntimeError):
            self.run_command('agents', 'bind-skills', 'a', '--json', '{}')

    def test_delete_requires_matching_id(self):
        c = Mock()
        with self.assertRaises(RuntimeError):
            self.run_command('skills', 'delete', '9', '--confirm-id', '8', client=c)
        c.request.assert_not_called()

    def test_invalid_version_never_sent(self):
        c = Mock()
        with self.assertRaises(RuntimeError):
            self.run_command('agents', 'publish', 'a', '--version-no', '0', client=c)
        c.request.assert_not_called()

    def test_export_writes_native_bytes_and_never_overwrites(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'agent.ciciagent'
            client = Mock()
            client.download.return_value = b'native-package-bytes'
            self.run_command('agents', 'export', 'mail', '--output', str(output), client=client)
            self.assertEqual(output.read_bytes(), b'native-package-bytes')
            client.download.assert_called_once_with('GET', '/openapi/v1/management/agents/mail/package', None)
            with self.assertRaises(RuntimeError):
                self.run_command('agents', 'export', 'mail', '--output', str(output), client=client)
            self.assertEqual(client.download.call_count, 1)

    def test_skill_export_explicit_draft(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            client = Mock()
            client.download.return_value = b'zip'
            self.run_command('skills', 'export', '36', '--allow-draft', '--output', str(Path(directory) / 'skill.zip'), client=client)
            client.download.assert_called_once_with('POST', '/openapi/v1/management/skills/36/package', {'allowDraft': True})

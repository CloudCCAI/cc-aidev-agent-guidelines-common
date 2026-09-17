import contextlib
import io
import json
import unittest
from unittest.mock import patch
import agentcici_application as app

class DraftCommandTest(unittest.TestCase):
    def test_draft_retries_existing_request_without_upload(self):
        request_id = '11111111-1111-4111-8111-111111111111'
        with patch.object(app, 'Client') as factory, patch('sys.argv', ['app', 'draft', request_id]):
            factory.return_value.request.return_value = {'status': 'DRAFT', 'requestId': request_id}
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(app.main(), 0)
            factory.return_value.request.assert_called_once_with('POST', '/openapi/v1/management/application-requests/' + request_id + '/draft', {})
            self.assertEqual(json.loads(output.getvalue())['status'], 'DRAFT')

    def test_invalid_request_id_does_not_call_server(self):
        with patch.object(app, 'Client') as factory, patch('sys.argv', ['app', 'draft', '../publish']):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(app.main(), 1)
            factory.assert_not_called()

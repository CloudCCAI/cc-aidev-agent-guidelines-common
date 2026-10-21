import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import agentcici_cloudcc_class as shared


class SharedCloudccConfigTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.cli = self.root / 'cloudcc'
        self.cli.touch()
        (self.root / 'cloudcc-cli.config.json').write_text('{}')
        (self.root / '.cloudcc-cache.json').write_text('{"test":"shared-cache"}')
        for name in ('app-a', 'app-b'):
            (self.root / 'applications' / name).mkdir(parents=True)

    def source(self, app='app-a'):
        directory = self.root / 'applications' / app / 'backend/classes/AppService'
        directory.mkdir(parents=True)
        (directory / 'AppService.java').write_text('public class AppService {}')
        return directory

    def test_create_runs_in_application_without_creating_config_copy(self):
        def create(command, cwd):
            self.assertEqual(Path(cwd), self.root / 'applications/app-a')
            self.assertEqual(command[1:], ['create', 'classes', 'AppService'])
            self.source()
            return subprocess.CompletedProcess(command, 0)
        with patch.object(shared.subprocess, 'run', side_effect=create):
            self.assertEqual(shared.run_class(self.cli, self.root, 'app-a', 'create', 'AppService'), 0)
        self.assertFalse((self.root / 'backend').exists())
        self.assertFalse((self.root / 'applications/app-a/cloudcc-cli.config.json').exists())

    def test_validate_and_publish_share_root_cache_but_keep_each_app_source(self):
        for app in ('app-a', 'app-b'):
            source = self.source(app)
            def execute(command, cwd):
                projection = self.root / 'backend/classes/AppService'
                self.assertEqual(projection.resolve(), source)
                self.assertEqual(Path(command[-1]), self.root)
                self.assertEqual(Path(cwd), self.root)
                (projection / 'config.json').write_text('{"id":"remote-class-id"}')
                (Path(cwd) / '.cloudcc-cache.json').write_text('{"test":"refreshed-cache"}')
                return subprocess.CompletedProcess(command, 0)
            with patch.object(shared.subprocess, 'run', side_effect=execute):
                self.assertEqual(shared.run_class(self.cli, self.root, app, 'publish', 'AppService'), 0)
            self.assertEqual((source / 'config.json').read_text(), '{"id":"remote-class-id"}')
            self.assertFalse((self.root / 'backend').exists())
            self.assertFalse((self.root / 'applications' / app / '.cloudcc-cache.json').exists())
        self.assertIn('refreshed-cache', (self.root / '.cloudcc-cache.json').read_text())

    def test_failed_cli_and_process_error_both_cleanup_projection(self):
        self.source()
        for result in (subprocess.CompletedProcess([], 9), OSError('process failed')):
            with patch.object(shared.subprocess, 'run', **({'side_effect': result} if isinstance(result, Exception) else {'return_value': result})):
                if isinstance(result, Exception):
                    with self.assertRaises(OSError):
                        shared.run_class(self.cli, self.root, 'app-a', 'validate', 'AppService')
                else:
                    self.assertEqual(shared.run_class(self.cli, self.root, 'app-a', 'validate', 'AppService'), 9)
            self.assertFalse((self.root / 'backend').exists())

    def test_existing_root_class_and_existing_application_class_never_overwritten(self):
        self.source()
        existing = self.root / 'backend/classes/AppService'
        existing.mkdir(parents=True)
        (existing / 'keep.txt').write_text('keep')
        with patch.object(shared.subprocess, 'run') as run:
            with self.assertRaises(RuntimeError):
                shared.run_class(self.cli, self.root, 'app-a', 'validate', 'AppService')
            with self.assertRaises(RuntimeError):
                shared.run_class(self.cli, self.root, 'app-a', 'create', 'AppService')
            run.assert_not_called()
        self.assertEqual((existing / 'keep.txt').read_text(), 'keep')

    def test_external_source_file_symlink_cannot_escape_application(self):
        source = self.source()
        java = source / 'AppService.java'
        java.unlink()
        outside = self.root / 'outside.java'
        outside.write_text('public class AppService {}')
        java.symlink_to(outside)
        with patch.object(shared.subprocess, 'run') as run:
            with self.assertRaises(RuntimeError):
                shared.run_class(self.cli, self.root, 'app-a', 'validate', 'AppService')
            run.assert_not_called()
        self.assertFalse((self.root / 'backend').exists())

    def test_invalid_paths_and_missing_root_config_do_not_call_cli(self):
        with patch.object(shared.subprocess, 'run') as run:
            for app in ('../outside', 'missing'):
                with self.assertRaises(RuntimeError):
                    shared.run_class(self.cli, self.root, app, 'create', 'AppService')
            (self.root / 'cloudcc-cli.config.json').unlink()
            with self.assertRaises(RuntimeError):
                shared.run_class(self.cli, self.root, 'app-a', 'create', 'AppService')
            run.assert_not_called()

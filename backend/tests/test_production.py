import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_production


class TestProductionLauncher(unittest.TestCase):
    def test_missing_database_never_starts_server(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / 'missing.sqlite'
            with patch.object(sys, 'argv', ['music', '--database', str(missing)]):
                with patch.object(run_production.uvicorn, 'run') as run:
                    with self.assertRaises(SystemExit):
                        run_production.main()
                    run.assert_not_called()
                    self.assertFalse(missing.exists())

    def test_missing_build_never_starts_server(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'history.sqlite'
            database.touch()
            real_is_file = Path.is_file
            with patch.object(sys, 'argv', ['music', '--database', str(database)]):
                with patch.object(Path, 'is_file', lambda path: False if path.name == 'index.html' else real_is_file(path)):
                    with patch.object(run_production.uvicorn, 'run') as run:
                        with self.assertRaises(SystemExit):
                            run_production.main()
                        run.assert_not_called()

    def test_explicit_database_overrides_inherited_url(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / 'history.sqlite'
            database.touch()
            with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://example.invalid/other'}):
                with patch.object(sys, 'argv', ['music', '--database', str(database), '--port', '8741']):
                    with patch.object(Path, 'is_file', return_value=True):
                        with patch.object(run_production.uvicorn, 'run') as run:
                            run_production.main()
                            self.assertEqual(os.environ['DATABASE_URL'], '')
                            self.assertEqual(os.environ['DATABASE_PATH'], str(database.resolve()))
                            self.assertEqual(run.call_args.kwargs['host'], '127.0.0.1')
                            self.assertEqual(run.call_args.kwargs['port'], 8741)


if __name__ == '__main__':
    unittest.main()

"""Restore optional package preferences without removing an unbacked-up directory."""

import os
from pathlib import Path
import shutil
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock

from test_package_manager_state import load_method


class RestoreOptionsTests(unittest.TestCase):
    def exercise(self, source_kind, *, settings_only=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backup = root / "backup"
            backup.mkdir()
            (backup / "settingsBackup").write_text("")
            current = root / "current-options"
            current.mkdir()
            (current / "existing").write_text("operator preference")
            source = backup / "setupOptions"
            if source_kind == "directory":
                source.mkdir()
                (source / "restored").write_text("backed-up preference")
            elif source_kind == "file":
                source.write_text("not a preferences directory")

            def mapped(path):
                return current if path == "/data/setupOptions" else Path(path)

            # Map the sole device destination into the disposable test directory.
            filesystem = SimpleNamespace(
                path=SimpleNamespace(
                    exists=os.path.exists, isdir=lambda path: mapped(path).is_dir()
                )
            )
            copier = SimpleNamespace(
                rmtree=lambda path: shutil.rmtree(mapped(path)),
                copytree=lambda source, dest: shutil.copytree(mapped(source), mapped(dest)),
            )
            restore = load_method(
                "MediaScanClass", "settingsRestore", logging=Mock(), os=filesystem,
                shutil=copier, dbus=SimpleNamespace(SystemBus=Mock()),
            )
            restore(None, str(backup), settings_only)
            return {path.name: path.read_text() for path in current.iterdir()}

    def test_legacy_backup_without_options_preserves_current_preferences(self):
        self.assertEqual(self.exercise("absent"), {"existing": "operator preference"})

    def test_non_directory_options_backup_preserves_current_preferences(self):
        self.assertEqual(self.exercise("file"), {"existing": "operator preference"})

    def test_present_options_backup_replaces_previous_preferences(self):
        self.assertEqual(self.exercise("directory"), {"restored": "backed-up preference"})

    def test_settings_only_restore_leaves_preferences_untouched(self):
        self.assertEqual(
            self.exercise("directory", settings_only=True),
            {"existing": "operator preference"},
        )

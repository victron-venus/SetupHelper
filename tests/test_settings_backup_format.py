"""Round-trip settings through actual backup files without a D-Bus service."""

import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock

from test_package_manager_state import load_method


class Text(str):
    pass


class Integer(int):
    pass


class Decimal(float):
    pass


class SettingsBackupFormatTests(unittest.TestCase):
    def round_trip(self, value, default=""):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings_list = root / "settingsList"
            settings_list.write_text("/Settings/Test\n")
            item = Mock()
            item.GetValue.return_value = Text(value)
            item.GetAttributes.return_value = [default, "", "", "0"]
            bus = Mock()
            bus.get_object.return_value = item
            dbus = SimpleNamespace(SystemBus=lambda: bus, String=Text,
                                   Int32=Integer, Int64=Integer, Double=Decimal)
            log = Mock()

            def mapped_open(path, *args, **kwargs):
                if path == "/data/SetupHelper/settingsList":
                    path = settings_list
                return open(path, *args, **kwargs)

            path_api = SimpleNamespace(exists=lambda p: True if p == "/data/SetupHelper/settingsList" else os.path.exists(p))
            backup = load_method("MediaScanClass", "settingsBackup", logging=log,
                                 os=SimpleNamespace(path=path_api), open=mapped_open, dbus=dbus)
            backup(None, directory, True)
            saved = (root / "settingsBackup").read_text()
            restore = load_method("MediaScanClass", "settingsRestore", _read_settings_backup=load_method(None, "_read_settings_backup", logging=log), logging=log,
                                  os=os, dbus=dbus)
            restore(None, directory, True)
            return item, bus, log, saved

    def test_comma_in_setting_value_round_trips(self):
        item, _, log, _ = self.round_trip("battery, garage")
        item.SetValue.assert_called_once_with("battery, garage")
        log.error.assert_not_called()

    def test_embedded_newline_cannot_become_another_setting_record(self):
        value = "first\n/Settings/Unexpected,injected"
        item, bus, log, _ = self.round_trip(value)
        item.SetValue.assert_called_once_with(value)
        self.assertTrue(all(call.args[1] == "/Settings/Test" for call in bus.get_object.call_args_list))
        log.error.assert_not_called()

    def test_special_characters_in_default_do_not_corrupt_the_record(self):
        default = '  default,"quoted"\nnext  '
        item, _, log, saved = self.round_trip("current", default)
        self.assertEqual(json.loads(saved.splitlines()[1])[3], default)
        item.SetValue.assert_called_once_with("current")
        log.error.assert_not_called()

    def test_plain_empty_unicode_quotes_and_whitespace_values_round_trip(self):
        for value in ("plain", "", '"quoted"', "  café 🔋  ", "line\rreturn"):
            with self.subTest(value=value):
                item, _, log, _ = self.round_trip(value)
                item.SetValue.assert_called_once_with(value)
                log.error.assert_not_called()

    def records(self, text):
        log = Mock()
        read = load_method(None, "_read_settings_backup", logging=log)
        return list(read(io.StringIO(text))), log

    def test_legacy_records_keep_their_original_field_semantics(self):
        for newline in ("\n", "\r\n"):
            lines = [
                '/Settings/Two,"literal quotes"',
                '/Settings/Seven,  value  ,s,default,0,100,1',
                '/Settings/Empty,',
            ]
            records, log = self.records(newline.join(lines) + newline)
            self.assertEqual(records, [line.strip().split(',') for line in lines])
            log.error.assert_not_called()

    def test_malformed_json_records_are_skipped_without_logging_values(self):
        header = "# SetupHelper settingsBackup JSONL v1\n"
        secret = "sensitive-value"
        invalid = [
            '{"' + secret + '": 1}',
            json.dumps(["/Settings/Test", secret, 7, "", "", "", ""]),
            json.dumps(["/Settings/Test", secret, "extra"]),
            secret,
        ]
        valid = ["/Settings/Good", "retained"]
        records, log = self.records(header + "\n".join(invalid + [json.dumps(valid)]) + "\n")
        self.assertEqual(records, [valid])
        self.assertEqual(log.error.call_count, len(invalid))
        self.assertNotIn(secret, str(log.error.call_args_list))

    def test_unknown_version_is_not_interpreted_as_legacy_data(self):
        records, log = self.records("# SetupHelper settingsBackup JSONL v2\n/Settings/Test,wrong\n")
        self.assertEqual(records, [])
        log.error.assert_called_once_with("settingsRestore: unsupported settings backup format")

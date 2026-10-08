"""Backup, restore and RTC process boundaries without touching a device."""

import io
import os
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from test_package_manager_state import load_method


def process_api(run):
    return SimpleNamespace(
        run=run, PIPE=subprocess.PIPE, SubprocessError=subprocess.SubprocessError
    )


class BackupProcessTests(unittest.TestCase):
    def backup(self, run):
        log = Mock()
        backup = load_method(
            "MediaScanClass", "settingsBackup", logging=log,
            os=SimpleNamespace(path=SimpleNamespace(exists=lambda _: True, isdir=lambda _: False)),
            open=lambda *_args: io.StringIO(), dbus=SimpleNamespace(SystemBus=Mock()),
            subprocess=process_api(run),
        )
        backup(None, "/backup", False)
        return log

    def test_log_backup_waits_for_successful_archiver(self):
        run = Mock()
        log = self.backup(run)
        run.assert_called_once_with(
            ["zip", "-rq", "/backup/logs.zip", "/data/log"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
        self.assertTrue(log.info.call_args.args[0].endswith(", logs"))
        log.error.assert_not_called()

    def test_log_backup_failure_is_not_reported_as_success(self):
        log = self.backup(Mock(side_effect=subprocess.CalledProcessError(2, "zip")))
        self.assertTrue(log.info.call_args.args[0].endswith(", no logs"))
        log.error.assert_called_once_with("settings backup - log write failure")

    def test_backup_does_not_swallow_process_interrupts(self):
        with self.assertRaises(KeyboardInterrupt):
            self.backup(Mock(side_effect=KeyboardInterrupt))

    def restore(self, text, run, *, exists=True):
        with tempfile.TemporaryDirectory() as directory:
            if exists:
                (Path(directory) / "settingsBackup").write_text(text)
            item = Mock()
            item.GetValue.side_effect = RuntimeError("setting does not exist")
            bus = Mock()
            bus.get_object.return_value = item
            dbus = SimpleNamespace(SystemBus=Mock(return_value=bus))
            log = Mock()
            restore = load_method(
                "MediaScanClass", "settingsRestore", ReadSettingsBackup=load_method(None, "ReadSettingsBackup", logging=log), logging=log, os=os,
                dbus=dbus, subprocess=process_api(run),
            )
            restore(None, directory, True)
        return item, dbus, log

    def test_restore_creates_silent_setting_before_writing_value(self):
        run = Mock()
        item, _, log = self.restore("/Settings/Test,42,i,0,0,100,1\n", run)
        run.assert_called_once_with(
            ["dbus", "-y", "com.victronenergy.settings", "/", "AddSettingSilent", "",
             "/Settings/Test", "0", "i", "0", "100"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
        item.SetValue.assert_called_once_with("42")
        log.error.assert_not_called()

    def test_failed_setting_creation_does_not_write_value(self):
        run = Mock(side_effect=subprocess.CalledProcessError(1, "dbus"))
        item, _, log = self.restore("/Settings/Test,42,i,0,0,100,0\n", run)
        self.assertEqual(run.call_args.args[0][4], "AddSetting")
        item.SetValue.assert_not_called()
        log.error.assert_called_once_with("settingsRestore: settings create failed for /Settings/Test")

    def test_missing_backup_does_not_open_file_or_bus(self):
        run = Mock()
        _, dbus, log = self.restore("", run, exists=False)
        dbus.SystemBus.assert_not_called()
        run.assert_not_called()
        self.assertIn("does not exist", log.error.call_args.args[0])

    def test_missing_default_package_list_logs_the_actual_path(self):
        log = Mock()
        reader = load_method(
            "DbusIfClass", "ReadDefaultPackagelist", logging=log,
            open=Mock(side_effect=FileNotFoundError),
        )
        reader(SimpleNamespace(rawDefaultPackages=[]))
        log.error.assert_called_once_with("no defaultPackageList /data/SetupHelper/defaultPackageList")

    def test_rtc_save_waits_for_the_spawned_process_and_records_failures(self):
        class StopLoop(Exception):
            pass

        for failure in (None, subprocess.CalledProcessError(1, "save-rtc")):
            with self.subTest(failure=failure):
                run, log = Mock(side_effect=failure), Mock()
                main_loop = load_method(
                    None, "mainLoop", logging=log, subprocess=process_api(run),
                    os=SimpleNamespace(path=SimpleNamespace(exists=lambda _: True)),
                    time=SimpleNamespace(time=lambda: 100), lastTimeSync=0,
                    DeferredGuiEditAcknowledgement=None,
                    DbusIf=SimpleNamespace(GetAutoDownloadMode=Mock(side_effect=StopLoop)),
                )
                with self.assertRaises(StopLoop):
                    main_loop()
                run.assert_called_once_with(
                    ["/etc/init.d/save-rtc.sh"], timeout=10,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
                )
                self.assertEqual(main_loop.__globals__["lastTimeSync"], 100)
                self.assertEqual(log.exception.call_count, int(failure is not None))


if __name__ == "__main__":
    unittest.main()

"""Keep persistent file conflicts separate from dependency refresh state."""

import io
import logging
import os.path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from test_package_manager_state import load_method


class PackageConflictRefreshTests(unittest.TestCase):
    def setUp(self):
        self.read_errors = set()
        self.files = {
            "/data/demo/version": "v1.0\n",
            "/data/demo/FileSets/fileList": "/usr/bin/shared\n",
            "/usr/bin/shared.package": "other\n",
        }
        self.package = SimpleNamespace(
            PackageName="demo",
            DependencyErrors=[],
            FileConflicts=[],
            InstallPending=False,
            DownloadPending=False,
            lastScriptPrecheck=1.0,
            LastPatchErrorUpdate=0.0,
            SetInstalledVersion=Mock(),
            SetPackageVersion=Mock(),
            SetIncompatible=Mock(),
        )
        filesystem = SimpleNamespace(
            path=SimpleNamespace(
                isdir=lambda path: path == "/data/demo",
                exists=lambda path: path in self.files,
                getmtime=lambda path: 2.0,
                basename=os.path.basename,
            )
        )
        self.update = load_method(
            "PackageClass",
            "UpdateVersionsAndFlags",
            open=self.read_file,
            os=filesystem,
            logging=logging,
            VersionToNumber=load_method(None, "VersionToNumber", re=re),
            VenusVersion="v3.0",
            VenusVersionNumber=30000000090000,
            Platform="Raspberry Pi",
            time=SimpleNamespace(time=lambda: 100.0),
            PackageClass=SimpleNamespace(
                LocatePackage=lambda _: SimpleNamespace(
                    PackageVersion="v1.0", GitHubVersion="v1.0"
                )
            ),
            PushAction=Mock(),
        )

        helpers = {
            name: load_method(None, name, **self.update.__globals__)
            for name in (
                "_package_dependency_errors", "_package_path_conflicts",
                "_package_file_list_conflicts", "_package_file_conflicts",
                "_package_conflict_details",
            )
        }
        for helper in helpers.values():
            helper.__globals__.update(helpers)
        self.update.__globals__.update(helpers)

    def read_file(self, path, mode="r"):
        if path in self.read_errors:
            raise PermissionError(path)
        if path not in self.files:
            raise FileNotFoundError(path)
        return io.StringIO(self.files[path])

    def refresh(self):
        self.update(self.package, doConflictChecks=True, doScriptPreChecks=False)
        return self.package.SetIncompatible.call_args

    def test_unchanged_file_conflict_stays_visible_on_every_refresh(self):
        for _ in range(3):
            status = self.refresh()
            self.assertEqual(status.args[0], "package conflict")
            self.assertIn("other must not be installed", status.args[1])
            self.assertEqual(
                self.package.FileConflicts, [("other", "uninstalled", "shared")]
            )
        self.assertEqual(self.package.DependencyErrors, [])

    def test_refresh_keeps_dependency_and_file_conflicts_independent(self):
        self.files["/data/demo/packageDependencies"] = "required installed\n"
        for _ in range(3):
            status = self.refresh()
            self.assertEqual(status.args[0], "package conflict")
            self.assertIn("required must be installed", status.args[1])
            self.assertIn("other must not be installed", status.args[1])
            self.assertEqual(self.package.DependencyErrors, [("required", "installed")])

    def test_removing_file_conflict_clears_it_without_hiding_dependencies(self):
        self.files["/data/demo/packageDependencies"] = "required installed\n"
        self.refresh()
        self.files["/usr/bin/shared.package"] = "demo\n"
        status = self.refresh()
        self.assertEqual(status.args[0], "package conflict")
        self.assertIn("required must be installed", status.args[1])
        self.assertNotIn("other", status.args[1])
        self.assertEqual(self.package.FileConflicts, [])
        del self.files["/data/demo/packageDependencies"]
        self.assertEqual(self.refresh().args, ("",))


    def test_unreadable_owner_list_keeps_other_file_conflicts(self):
        self.read_errors.add("/usr/bin/shared.package")
        self.files["/data/demo/FileSets/fileList"] += "/usr/bin/second\n"
        self.files["/usr/bin/second.package"] = "second-owner\n"
        status = self.refresh()
        self.assertEqual(self.package.FileConflicts,
                         [("second-owner", "uninstalled", "second")])
        self.assertIn("second-owner must not be installed", status.args[1])

    def test_unreadable_file_list_does_not_skip_independent_list(self):
        self.read_errors.add("/data/demo/FileSets/fileList")
        self.files["/data/demo/FileSets/fileListVersionIndependent"] = "/usr/bin/shared\n"
        self.assertIn("other must not be installed", self.refresh().args[1])

    def test_invalid_dependency_line_does_not_skip_remaining_dependencies(self):
        self.files["/data/demo/packageDependencies"] = "incomplete\nz installed\na installed\n"
        self.refresh()
        self.assertEqual(self.package.DependencyErrors,
                         [("a", "installed"), ("z", "installed")])

    def test_recent_owner_list_still_schedules_script_check(self):
        self.files["/data/demo/setup"] = ""
        self.refresh()
        self.update.__globals__["PushAction"].assert_called_once_with(
            command="check:demo", source="AUTO")


if __name__ == "__main__":
    unittest.main()

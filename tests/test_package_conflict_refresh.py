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
            VersionToNumber=load_method(
                None,
                "VersionToNumber",
                re=re,
                _version_release_kind=load_method(None, "_version_release_kind"),
                _without_large_build_suffix=load_method(
                    None, "_without_large_build_suffix"
                ),
            ),
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

    def read_file(self, path, mode="r"):
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


if __name__ == "__main__":
    unittest.main()

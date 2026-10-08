"""Exercise real PackageManager methods without starting device services."""

import ast
import logging
from pathlib import Path
from types import CodeType, FunctionType, SimpleNamespace
import unittest
from unittest.mock import Mock

SOURCE = Path(__file__).resolve().parents[1] / "PackageManager.py"


def load_method(class_name, method_name, **environment):
    # Importing PackageManager starts device workers. Compile the original
    # method body alone and replace only its hardware/process dependencies.
    tree = ast.parse(SOURCE.read_text())
    cls = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    method = next(
        node
        for node in cls.body
        if isinstance(node, ast.FunctionDef) and node.name == method_name
    )
    module = ast.Module(body=[method], type_ignores=[])
    compiled = compile(module, str(SOURCE), "exec")
    code = next(value for value in compiled.co_consts if isinstance(value, CodeType))
    return FunctionType(code, environment, method_name)


class PackageManagerStateTests(unittest.TestCase):
    def test_backup_indicators_report_absence_and_presence(self):
        for method, key in (
            ("GetBackupMediaAvailable", "/BackupMediaAvailable"),
            ("GetBackupSettingsFileExist", "/BackupSettingsFileExist"),
        ):
            getter = load_method("DbusIfClass", method)
            for value, expected in ((0, False), (1, True)):
                with self.subTest(method=method, value=value):
                    self.assertIs(
                        getter(SimpleNamespace(DbusService={key: value})), expected
                    )

    def test_unavailable_dependency_does_not_enqueue_an_install(self):
        parent = SimpleNamespace(
            DependencyErrors=[("dependency", "installed")], FileConflicts=[]
        )
        missing = SimpleNamespace(
            InstalledVersion="", PackageVersion="", GitHubVersion=""
        )
        bus, actions = Mock(), Mock()
        resolver = load_method(
            "InstallPackagesClass",
            "ResolveConflicts",
            logging=logging,
            DbusIf=bus,
            PushAction=actions,
            WARNING=logging.WARNING,
            PackageClass=SimpleNamespace(
                LocatePackage=lambda name: parent if name == "parent" else missing
            ),
        )
        resolver(None, packageName="parent", source="GUI")
        actions.assert_not_called()
        self.assertIn("not available", bus.UpdateStatus.call_args.kwargs["message"])
        bus.UNLOCK.assert_called_once_with("ResolveConflicts")

    def test_available_dependency_selects_install_or_download(self):
        for stored, expected in (
            (True, "install:dependency"),
            (False, "download:dependency"),
        ):
            with self.subTest(stored=stored):
                parent = SimpleNamespace(
                    DependencyErrors=[("dependency", "installed")], FileConflicts=[]
                )
                dependency = SimpleNamespace(
                    InstalledVersion="",
                    PackageVersion="1" if stored else "",
                    GitHubVersion="1",
                )
                actions = Mock()
                resolver = load_method(
                    "InstallPackagesClass",
                    "ResolveConflicts",
                    logging=logging,
                    DbusIf=Mock(),
                    PushAction=actions,
                    WARNING=logging.WARNING,
                    PackageClass=SimpleNamespace(
                        LocatePackage=lambda name: (
                            parent if name == "parent" else dependency
                        )
                    ),
                )
                resolver(None, packageName="parent", source="GUI")
                actions.assert_called_once_with(command=expected, source="GUI")


if __name__ == "__main__":
    unittest.main()

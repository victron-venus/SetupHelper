"""Package lookup failures must neither escape the tree nor lose list locks."""

import logging
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from test_package_manager_state import load_method


class PackageLookupTests(unittest.TestCase):
    def locator(self):
        locate = load_method(None, "LocatePackagePath", os=os)
        locate.__globals__["LocatePackagePath"] = locate
        return locate

    def test_nested_archive_directory_is_located(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "wrapper" / "package"
            package.mkdir(parents=True)
            (package / "version").write_text("v1.2.3")
            self.assertEqual(self.locator()(str(root)), str(package))

    def test_empty_nested_archive_returns_none(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "wrapper" / "empty").mkdir(parents=True)
            self.assertIsNone(self.locator()(directory))

    def test_directory_symlinks_are_not_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "archive"
            archive.mkdir()
            outside = root / "outside"
            outside.mkdir()
            (outside / "version").write_text("v1.2.3")
            (archive / "escape").symlink_to(outside, target_is_directory=True)
            (archive / "loop").symlink_to(archive, target_is_directory=True)
            self.assertIsNone(self.locator()(str(archive)))

    def remover(self, packages):
        bus = Mock()
        owner = SimpleNamespace(PackageList=packages, SetAutoAddOk=Mock())
        remove = load_method(
            "PackageClass", "RemovePackage", PackageClass=owner, DbusIf=bus,
            logging=logging, ERROR=logging.ERROR, INFO=logging.INFO,
            CRITICAL=logging.CRITICAL, NONE=0,
        )
        return remove, owner, bus

    def test_missing_package_returns_failure_and_releases_list_lock(self):
        packages = [SimpleNamespace(PackageName="kept", InstalledVersion="")]
        remove, owner, bus = self.remover(packages)
        self.assertFalse(remove(owner, packageName="missing", packageIndex=None, isDuplicate=False))
        self.assertEqual(len(packages), 1)
        bus.LOCK.assert_called_once_with("RemovePackage")
        bus.UNLOCK.assert_called_once_with("RemovePackage")
        bus.AcknowledgeGuiEditAction.assert_called_once_with("ERROR")
        owner.SetAutoAddOk.assert_not_called()

    def test_invalid_index_cannot_select_another_package(self):
        for index in (-1, 1, 99, True, "0"):
            with self.subTest(index=index):
                packages = [SimpleNamespace(PackageName="kept", InstalledVersion="")]
                remove, owner, bus = self.remover(packages)
                self.assertFalse(remove(owner, packageName=None, packageIndex=index, isDuplicate=False))
                self.assertEqual(len(packages), 1)
                bus.LOCK.assert_not_called()
                owner.SetAutoAddOk.assert_not_called()

    def test_index_removal_blocks_the_matched_name_before_slots_move(self):
        for index, duplicate in ((0, False), (1, False), (0, True)):
            with self.subTest(index=index, duplicate=duplicate):
                packages = [
                    Mock(PackageName="first", InstalledVersion=""),
                    Mock(PackageName="second", InstalledVersion=""),
                ]
                removed_name = packages[index].PackageName
                first = packages[0]
                first.SetPackageName.side_effect = lambda name: setattr(first, "PackageName", name)
                remove, owner, bus = self.remover(packages)
                self.assertTrue(remove(owner, packageName=None, packageIndex=index, isDuplicate=duplicate))
                self.assertEqual(len(packages), 1)
                if duplicate:
                    owner.SetAutoAddOk.assert_not_called()
                else:
                    owner.SetAutoAddOk.assert_called_once_with(removed_name, False)
                if index == 0:
                    self.assertEqual(packages[0].PackageName, "second")
                bus.UNLOCK.assert_called_once_with("RemovePackage")

"""Missing packages and queue failures must not retain the package-list lock."""

import logging
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from test_package_manager_state import load_method


class ConflictLockTests(unittest.TestCase):
    def resolver(self, parent, dependency, actions=None):
        bus = Mock()
        actions = Mock() if actions is None else actions
        resolve = load_method(
            "InstallPackagesClass", "ResolveConflicts", logging=logging,
            DbusIf=bus, PushAction=actions, WARNING=logging.WARNING,
            PackageClass=SimpleNamespace(LocatePackage=lambda name: parent if name == "parent" else dependency),
        )
        return resolve, bus, actions

    def parent(self, requirement="installed"):
        return SimpleNamespace(DependencyErrors=[("dependency", requirement)], FileConflicts=[])

    def test_missing_parent_unlocks_without_queuing_actions(self):
        resolve, bus, actions = self.resolver(None, None)
        resolve(None, packageName="parent", source="GUI")
        actions.assert_not_called()
        bus.LOCK.assert_called_once_with("ResolveConflicts")
        bus.UNLOCK.assert_called_once_with("ResolveConflicts")

    def test_missing_required_dependency_reports_unavailable_and_unlocks(self):
        resolve, bus, actions = self.resolver(self.parent(), None)
        resolve(None, packageName="parent", source="GUI")
        actions.assert_not_called()
        self.assertIn("not available", bus.UpdateStatus.call_args.kwargs["message"])
        bus.UNLOCK.assert_called_once_with("ResolveConflicts")

    def test_missing_forbidden_dependency_requires_no_action(self):
        resolve, bus, actions = self.resolver(self.parent("uninstalled"), None)
        resolve(None, packageName="parent", source="GUI")
        actions.assert_not_called()
        bus.UpdateStatus.assert_not_called()
        bus.UNLOCK.assert_called_once_with("ResolveConflicts")

    def test_queue_failure_propagates_after_releasing_lock(self):
        dependency = SimpleNamespace(InstalledVersion="", PackageVersion="v1", GitHubVersion="")
        actions = Mock(side_effect=RuntimeError("queue failed"))
        resolve, bus, _ = self.resolver(self.parent(), dependency, actions)
        with self.assertRaisesRegex(RuntimeError, "queue failed"):
            resolve(None, packageName="parent", source="GUI")
        bus.UNLOCK.assert_called_once_with("ResolveConflicts")

    def test_interruption_propagates_after_releasing_lock(self):
        dependency = SimpleNamespace(InstalledVersion="", PackageVersion="v1", GitHubVersion="")
        actions = Mock(side_effect=KeyboardInterrupt)
        resolve, bus, _ = self.resolver(self.parent(), dependency, actions)
        with self.assertRaises(KeyboardInterrupt):
            resolve(None, packageName="parent", source="GUI")
        bus.UNLOCK.assert_called_once_with("ResolveConflicts")

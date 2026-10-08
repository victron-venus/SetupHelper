"""Keep normal and large image version ordering aligned across both runtimes."""

import re
import subprocess
from pathlib import Path
import unittest

from test_package_manager_state import load_method


class VersionOrderTests(unittest.TestCase):
    def setUp(self):
        self.parse = load_method(
            None,
            "VersionToNumber",
            re=re,
            _version_release_kind=load_method(None, "_version_release_kind"),
            _without_large_build_suffix=load_method(
                None, "_without_large_build_suffix"
            ),
        )

    def test_large_and_legacy_large_images_keep_the_normal_version(self):
        for version in ("v3.00", "v3.00~14", "v1.2.3d4", "v1.2.3a4", "v1.2.3b4"):
            for suffix in ("-large", "-large-0", "-large-1", "-large-999"):
                with self.subTest(version=version, suffix=suffix):
                    self.assertEqual(self.parse(version + suffix), self.parse(version))

    def test_large_prereleases_stay_below_stable_and_keep_release_priority(self):
        for suffix in ("", "-large", "-large-12"):
            versions = ["v1.2.3d4", "v1.2.3a4", "v1.2.3b4", "v1.2.3", "v1.2.4"]
            numbers = [self.parse(version + suffix) for version in versions]
            self.assertEqual(numbers, sorted(set(numbers)))
        self.assertLess(self.parse("v3.00~14-large"), self.parse("v3.00"))

    def test_only_recognized_trailing_large_build_suffix_is_removed(self):
        normalize = load_method(None, "_without_large_build_suffix")
        for version in (
            "v1-large-preview",
            "v1-large-",
            "v1-large-1x",
            "large1.2",
            "v1-large-١",
        ):
            with self.subTest(version=version):
                self.assertEqual(normalize(version), version)

    def test_shell_and_python_agree_and_shell_status_preserves_input(self):
        # Evaluate only the pure conversion function, never the installer body.
        resources = (
            Path(__file__).resolve().parents[1] / "HelperResources/EssentialResources"
        )
        source = resources.read_text()
        start = source.index("function versionStringToNumber ()")
        end = source.index("\n}", start) + 2
        script = (
            source[start:end]
            + """
for value in "$@"; do
    versionStringToNumber "$value" || exit 1
    printf '%s\t%s\n' "$versionNumber" "$versionStringToNumberStatus"
done
"""
        )
        versions = [
            version + suffix
            for version in ("v3.00", "v3.00~14", "v1.2.3d4", "v1.2.3a4", "v1.2.3b4")
            for suffix in ("", "-large", "-large-1")
        ]
        result = subprocess.run(
            ["bash", "-c", script, "version-order-test", *versions],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(len(result.stdout.splitlines()), len(versions))
        for version, line in zip(versions, result.stdout.splitlines()):
            number, status = line.split("\t", 1)
            with self.subTest(version=version):
                self.assertEqual(int(number), self.parse(version))
                self.assertTrue(status.startswith(version + ":"))


if __name__ == "__main__":
    unittest.main()

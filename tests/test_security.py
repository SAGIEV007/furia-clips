import os
import sys
import tempfile
import unittest

from modules.security import UnsafePathError, safe_filename, safe_workspace_path, unique_storage_name


class SecurityTests(unittest.TestCase):
    def test_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(UnsafePathError):
                safe_workspace_path(root, "../outside.txt")

    def test_rejects_absolute_path_outside_workspace(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(UnsafePathError):
                safe_workspace_path(root, "/tmp/outside.txt")

    def test_sanitizes_filename_without_directories(self):
        sanitized = safe_filename("../video: perigoso?.mp4")
        self.assertNotIn("/", sanitized)
        self.assertNotIn("\\", sanitized)
        self.assertNotIn("..", sanitized)
        self.assertTrue(sanitized.endswith(".mp4"))

    def test_generates_unique_storage_name(self):
        first = unique_storage_name("video original.mp4")
        second = unique_storage_name("video original.mp4")
        self.assertNotEqual(first, second)
        self.assertTrue(first.endswith(".mp4"))

    @unittest.skipUnless(hasattr(os, "symlink") and os.name == "posix", "Symlinks require admin on Windows")
    def test_rejects_symlink_pointing_outside(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            link = os.path.join(root, "link")
            os.symlink(outside, link)
            with self.assertRaises(UnsafePathError):
                safe_workspace_path(root, "link/file.mp4")


if __name__ == "__main__":
    unittest.main()

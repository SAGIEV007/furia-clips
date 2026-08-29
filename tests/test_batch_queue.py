import sys
import os
import tempfile
import unittest

from modules.batch_queue import build_manifest, scan_directory


class BatchQueueTests(unittest.TestCase):
    def test_scans_videos_and_deduplicates_by_content(self):
        with tempfile.TemporaryDirectory() as root:
            first = os.path.join(root, "first.mp4")
            second = os.path.join(root, "second.mp4")
            text = os.path.join(root, "notes.txt")
            with open(first, "wb") as handle:
                handle.write(b"same media")
            with open(second, "wb") as handle:
                handle.write(b"same media")
            with open(text, "wb") as handle:
                handle.write(b"ignore")

            items = scan_directory(root, {".mp4"})
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].relative_path, "first.mp4")
            self.assertEqual(len(items[0].content_hash), 64)

    def test_manifest_is_reproducible_and_skips_external_symlink(self):
    @unittest.skipUnless(hasattr(os, "symlink") and os.name == "posix", "Symlinks require admin on Windows")
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            video = os.path.join(root, "nested.mp4")
            external = os.path.join(outside, "external.mp4")
            with open(video, "wb") as handle:
                handle.write(b"nested")
            with open(external, "wb") as handle:
                handle.write(b"external")
            os.symlink(external, os.path.join(root, "link.mp4"))

            manifest = build_manifest(root, {".mp4"})
            self.assertEqual(manifest["total"], 1)
            self.assertEqual(manifest["items"][0]["relative_path"], "nested.mp4")


if __name__ == "__main__":
    unittest.main()

import contextlib
import io
from pathlib import Path
import unittest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "legacy"))

from blux_view import render_from_directory  # noqa: E402  (BLUX App 1.0 viewer, kept as `blux-app legacy-view`)


FIXTURE_DIRS = [
    Path(__file__).resolve().parent.parent / "fixtures" / "0.1",
    Path(__file__).resolve().parent.parent / "fixtures" / "0.6",
    Path(__file__).resolve().parent.parent / "fixtures" / "1.0-pro",
    Path(__file__).resolve().parent.parent / "fixtures" / "missing-optional",
]


class TestViewerSmoke(unittest.TestCase):
    def test_render_fixtures(self) -> None:
        for directory in FIXTURE_DIRS:
            with self.subTest(directory=directory):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    render_from_directory(directory)
                output = buffer.getvalue()
                self.assertIn("==", output)


if __name__ == "__main__":
    unittest.main()

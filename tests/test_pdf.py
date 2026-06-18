"""Offline tests for Markdown-to-PDF rendering (no API key needed)."""

import re
import tempfile
import unittest
from pathlib import Path

from history_agent import pdf

SAMPLE = """# This Day in History — 21st July

## Politics
- **1969** — Apollo 11 reached the Moon (source 1).

## Sports
- **1968** — A Test match at *Headingley*.

## Sources
1. [NASA](https://www.nasa.gov/)
"""


class InlineTests(unittest.TestCase):
    def test_bold_italic_link_code(self):
        out = pdf._inline("**b** *i* `c` [t](http://x)")
        self.assertIn("<b>b</b>", out)
        self.assertIn("<i>i</i>", out)
        self.assertIn('face="Courier"', out)
        self.assertIn('href="http://x"', out)

    def test_escapes_angle_brackets(self):
        self.assertIn("&lt;tag&gt;", pdf._inline("<tag>"))


class RenderTests(unittest.TestCase):
    def _pages(self, data: bytes) -> int:
        return len(re.findall(rb"/Type\s*/Page(?![s])", data))

    def test_writes_valid_pdf(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.pdf"
            pdf.render_markdown_to_pdf(SAMPLE, str(out), title="Test")
            data = out.read_bytes()
            self.assertTrue(data.startswith(b"%PDF-"))
            self.assertGreater(len(data), 500)

    def test_one_page_per_section(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "out.pdf"
            pdf.render_markdown_to_pdf(SAMPLE, str(out), title="Test")
            # Three "##" sections -> three pages (title rides with the first).
            self.assertEqual(self._pages(out.read_bytes()), 3)

    def test_creates_missing_parent_dir(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "nested" / "deep" / "out.pdf"
            pdf.render_markdown_to_pdf(SAMPLE, str(out), title="Test")
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()

# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

"""Decision #42 gap 5 — the WhatsApp-shareable Readiness Score card. The
card is served to GUESTS, so its two contracts are tested here without a
bench/site: it must be a self-contained SVG (no scripts, links, or external
assets), and its content must stay inside the public privacy allowlist
(first name, subject, score/band, month/year — nothing else).

Loaded by file path rather than package import on purpose, same as every
other test in this directory: readiness_card.py is deliberately frappe-free.
"""

import importlib.util
import os
import unittest
import xml.etree.ElementTree as ET

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "readiness_card.py")
_spec = importlib.util.spec_from_file_location("rlms_readiness_card", _MODULE_PATH)
readiness_card = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(readiness_card)


def _render(**overrides):
    values = {
        "first_name": "Thabo",
        "subject": "Mathematics",
        "score": 84,
        "band": "Exam Ready",
        "month_label": "August 2026",
    }
    values.update(overrides)
    return readiness_card.render_card_svg(**values)


class TestCardContent(unittest.TestCase):
    def test_is_wellformed_xml_svg(self):
        root = ET.fromstring(_render())
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")

    def test_shows_the_allowed_fields(self):
        svg = _render()
        for expected in ("Thabo", "Mathematics", ">84<", "Exam Ready", "August 2026"):
            self.assertIn(expected, svg)

    def test_score_is_clamped(self):
        self.assertIn(">100<", _render(score=250))
        self.assertIn(">0<", _render(score=-5))

    def test_band_colors_cover_every_band(self):
        for _minimum, label in (
            (80, "Exam Ready"),
            (60, "On Track"),
            (40, "Building"),
            (0, "Needs Focus"),
        ):
            self.assertIn(label, readiness_card._BAND_COLORS)
            self.assertIn(label, _render(band=label))


class TestCardSafety(unittest.TestCase):
    def test_hostile_name_is_escaped(self):
        svg = _render(first_name='<script>alert("x")</script>')
        self.assertNotIn("<script", svg)
        # And the document still parses.
        ET.fromstring(svg)

    def test_hostile_subject_is_escaped(self):
        svg = _render(subject='"><image href="https://evil.example/x.png"/>')
        self.assertNotIn("<image", svg)
        ET.fromstring(svg)

    def test_absurdly_long_name_is_clipped(self):
        svg = _render(first_name="A" * 500)
        self.assertNotIn("A" * (readiness_card.MAX_NAME_CHARS + 1), svg)

    def test_self_contained_no_scripts_links_or_external_assets(self):
        svg = _render()
        for banned in ("<script", "href", "<image", "<foreignObject", "url(http"):
            self.assertNotIn(banned, svg)
        # The only URL of any kind is the SVG namespace declaration.
        self.assertEqual(svg.count("http"), 1)
        self.assertIn('xmlns="http://www.w3.org/2000/svg"', svg)

    def test_privacy_allowlist_is_the_signature(self):
        # The renderer cannot leak what it is never given: its parameters
        # are exactly the public allowlist. A new parameter is a privacy
        # decision — this test is the tripwire that forces it to be one.
        import inspect

        params = list(
            inspect.signature(readiness_card.render_card_svg).parameters
        )
        self.assertEqual(
            params, ["first_name", "subject", "score", "band", "month_label"]
        )

    def test_no_input_no_leak(self):
        # Render with empty optional strings: nothing student-specific
        # beyond the score should remain.
        svg = _render(first_name="", band="", month_label="")
        ET.fromstring(svg)
        self.assertNotIn("Thabo", svg)


if __name__ == "__main__":
    unittest.main()

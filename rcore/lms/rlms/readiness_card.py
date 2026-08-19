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

"""Pure SVG renderer for the shareable Readiness Score card (decision #42
gap 5). Frappe-free by design, same split as readiness_rules.py: the API
module resolves the share token and passes plain values; this module only
turns them into markup, so the card — including its privacy surface — is
unit-testable without a bench/site.

PRIVACY IS THE CONTRACT HERE: the card is built for WhatsApp forwarding, so
its content is capped at exactly what the public verify endpoint exposes —
first name, subject, score (and its derived band), month/year. No email, no
phone, no school, no grade, nothing else. render_card_svg's signature IS the
allowlist; adding a parameter is a privacy decision, not a refactor.

The SVG is fully self-contained: inline styles only, system font stack, no
external assets/fonts/images, no scripts, no hyperlinks — safe to serve to
guests and to preview inside chat apps. All caller-provided text is
XML-escaped and length-capped before it reaches the markup.
"""

from xml.sax.saxutils import escape

#: 1.91:1, the link-preview aspect chat apps favour.
CARD_WIDTH = 800
CARD_HEIGHT = 418

#: Hard caps so a hostile/absurd value cannot distort the layout.
MAX_NAME_CHARS = 24
MAX_SUBJECT_CHARS = 32

#: Band accent colours (band label -> hex). Neutral defaults; the app's
#: theme does not reach a guest-served SVG, so these live here.
_BAND_COLORS = {
    "Exam Ready": "#1B9E4B",
    "On Track": "#2F80ED",
    "Building": "#F2994A",
    "Needs Focus": "#EB5757",
}
_FONT = (
    "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', "
    "Arial, sans-serif"
)


def _clip(text, limit):
    text = (text or "").strip()
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def render_card_svg(first_name, subject, score, band, month_label):
    """The shareable card as an SVG string.

    [first_name]  the student's first name ONLY — never a full name.
    [subject]     display subject, e.g. "Mathematics".
    [score]       integer 0..100 (the server-computed snapshot).
    [band]        readiness_rules.readiness_band label for [score].
    [month_label] e.g. "August 2026" — the score's as-of period.
    """
    score = int(min(max(int(score), 0), 100))
    name = escape(_clip(first_name, MAX_NAME_CHARS))
    subject_text = escape(_clip(subject, MAX_SUBJECT_CHARS))
    band_text = escape((band or "").strip())
    month_text = escape((month_label or "").strip())
    accent = _BAND_COLORS.get(band, "#2F80ED")

    # Score ring: radius 92, circumference ~578; dash length shows progress.
    circumference = 578.0
    dash = circumference * score / 100.0

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{CARD_HEIGHT}" viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}" role="img" aria-label="Supacharge Readiness Score">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#101828"/>
      <stop offset="1" stop-color="#1D2939"/>
    </linearGradient>
  </defs>
  <rect width="{CARD_WIDTH}" height="{CARD_HEIGHT}" rx="24" fill="url(#bg)"/>
  <rect x="1.5" y="1.5" width="{CARD_WIDTH - 3}" height="{CARD_HEIGHT - 3}" rx="22.5" fill="none" stroke="{accent}" stroke-opacity="0.55" stroke-width="3"/>
  <text x="56" y="88" font-family="{_FONT}" font-size="30" font-weight="700" fill="#FFFFFF">Supacharge</text>
  <text x="56" y="124" font-family="{_FONT}" font-size="20" fill="#98A2B3">Readiness Score</text>
  <text x="56" y="196" font-family="{_FONT}" font-size="40" font-weight="700" fill="#FFFFFF">{subject_text}</text>
  <text x="56" y="240" font-family="{_FONT}" font-size="24" fill="#D0D5DD">{name}</text>
  <text x="56" y="276" font-family="{_FONT}" font-size="20" fill="#98A2B3">{month_text}</text>
  <rect x="56" y="308" rx="17" width="220" height="34" fill="{accent}" fill-opacity="0.18"/>
  <text x="166" y="331" text-anchor="middle" font-family="{_FONT}" font-size="19" font-weight="600" fill="{accent}">{band_text}</text>
  <text x="56" y="386" font-family="{_FONT}" font-size="15" fill="#667085">Server-verified by Supacharge</text>
  <g transform="translate(614,209)">
    <circle r="92" fill="none" stroke="#344054" stroke-width="14"/>
    <circle r="92" fill="none" stroke="{accent}" stroke-width="14" stroke-linecap="round" stroke-dasharray="{dash:.1f} {circumference:.1f}" transform="rotate(-90)"/>
    <text y="14" text-anchor="middle" font-family="{_FONT}" font-size="64" font-weight="700" fill="#FFFFFF">{score}</text>
    <text y="46" text-anchor="middle" font-family="{_FONT}" font-size="18" fill="#98A2B3">out of 100</text>
  </g>
</svg>
"""

"""Deterministic visible-text extraction for the injection test pages.

Rules (fixed, so every consumer sees the same text):
* `html.parser` with `convert_charrefs=True`; tags are dropped, text nodes are kept.
* Text inside <head>, <script>, <style>, <template> is dropped (the pages contain no
  script or style; the rule exists so the extractor stays correct if one is added).
* Block elements end a line. Runs of ASCII whitespace collapse to one space; lines are
  stripped of ASCII whitespace only, empty lines dropped.
* Nothing else is normalised: zero-width characters (U+200B-U+200D, U+2060, U+FEFF), Unicode
  tag characters (U+E0000-U+E007F) and homoglyphs pass through unchanged. `invisible_counts`
  reports what survived, so a report can state whether the extractor preserved them.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

_SKIP = {"head", "script", "style", "template"}
_BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "ul", "ol", "tr", "td", "th",
          "table", "section", "article", "header", "footer", "main", "nav", "br", "hr",
          "blockquote", "pre", "form", "label", "button", "dt", "dd", "dl", "body", "html"}
_ASCII_WS = re.compile(r"[ \t\r\n\f\v]+")
ZERO_WIDTH = frozenset("​‌‍⁠﻿")


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP:
            self.skip += 1
        elif tag in _BLOCK:
            self.parts.append("\n")

    def handle_startendtag(self, tag, attrs):
        if tag in _BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in _BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def visible_text(html: str) -> str:
    parser = _Text()
    parser.feed(html)
    parser.close()
    lines = []
    for line in "".join(parser.parts).split("\n"):
        line = _ASCII_WS.sub(" ", line).strip(" \t\r\f\v")
        if line:
            lines.append(line)
    return "\n".join(lines)


def invisible_counts(text: str) -> dict[str, int]:
    return {"zero_width": sum(1 for c in text if c in ZERO_WIDTH),
            "tag_chars": sum(1 for c in text if 0xE0000 <= ord(c) <= 0xE007F),
            "non_ascii_letters": sum(1 for c in text if ord(c) > 127 and c.isalpha())}


def extract_file(path: Path) -> str:
    return visible_text(path.read_text(encoding="utf-8"))

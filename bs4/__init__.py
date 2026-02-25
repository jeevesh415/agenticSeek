"""Very small BeautifulSoup-compatible shim used for tests."""
from __future__ import annotations
import re

class _Node:
    def __init__(self, html: str, attrs: dict | None = None):
        self._html = html
        self._attrs = attrs or {}

    @property
    def text(self):
        text = re.sub(r"<[^>]+>", "", self._html)
        return text

    def find(self, tag: str, class_: str | None = None):
        attrs = ''
        if class_:
            attrs = rf'[^>]*class=["\'][^"\']*{re.escape(class_)}[^"\']*["\']'
        pattern = rf'<{tag}{attrs}[^>]*>(.*?)</{tag}>'
        m = re.search(pattern, self._html, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            # self-closing style
            pattern2 = rf'<{tag}{attrs}[^>]*>'
            m2 = re.search(pattern2, self._html, flags=re.IGNORECASE | re.DOTALL)
            if not m2:
                return None
            raw = m2.group(0)
            return _Node(raw, _extract_attrs(raw))
        raw = m.group(0)
        return _Node(raw, _extract_attrs(raw))

    def find_all(self, tag: str, class_: str | None = None):
        attrs = ''
        if class_:
            attrs = rf'[^>]*class=["\'][^"\']*{re.escape(class_)}[^"\']*["\']'
        pattern = rf'<{tag}{attrs}[^>]*>(.*?)</{tag}>'
        return [_Node(m.group(0), _extract_attrs(m.group(0))) for m in re.finditer(pattern, self._html, flags=re.IGNORECASE | re.DOTALL)]

    def __getitem__(self, key):
        return self._attrs[key]


def _extract_attrs(tag_html: str) -> dict:
    opening = re.search(r'<[^>]+>', tag_html)
    if not opening:
        return {}
    attrs = {}
    for k,v in re.findall(r'([a-zA-Z_:][-a-zA-Z0-9_:.]*)=["\']([^"\']+)["\']', opening.group(0)):
        attrs[k] = v
    return attrs


class BeautifulSoup(_Node):
    def __init__(self, html: str, _parser: str = 'html.parser'):
        super().__init__(html)

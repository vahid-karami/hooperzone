"""Clean the trust-badge code (Enamad, Samandehi) that staff paste into the shop settings.

The storefront puts this HTML into every page as it is, so anything beyond a linked picture
is dropped: a <script> or an onclick there would run in every visitor's browser, including a
signed-in administrator's, and could take over their session.
"""
import re
from html import escape
from html.parser import HTMLParser

ALLOWED_ATTRS = {
    "a": {"href", "target", "title", "referrerpolicy"},
    # Enamad's badge carries its verification code in a "code" attribute.
    "img": {"src", "alt", "title", "width", "height", "referrerpolicy", "id", "code"},
}
URL_ATTRS = {"href", "src"}
# Samandehi's badge opens its certificate from an onclick; the address is turned into a link.
ONCLICK_URL = re.compile(r"""window\.open\(\s*["'](https://[^"'\s]+)["']""")


def _safe_url(value):
    value = (value or "").strip()
    return value if re.match(r"https://[^\s\"'<>`\\]+$", value) else ""


class _BadgeCleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.open_links = 0

    def _tag(self, tag, attrs):
        parts = [tag]
        for name, value in attrs:
            if name not in ALLOWED_ATTRS[tag] or value is None:
                continue
            if name in URL_ATTRS:
                value = _safe_url(value)
                if not value:
                    continue
            parts.append(f'{name}="{escape(value, quote=True)}"')
        if tag == "a":
            parts.append('rel="noopener"')  # not noreferrer: Enamad checks which site the click came from
        return "<" + " ".join(parts) + ">"

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.out.append(self._tag("a", attrs))
            self.open_links += 1
        elif tag == "img":
            image = self._tag("img", attrs)
            if 'src="' not in image:
                return
            onclick = ONCLICK_URL.search(dict(attrs).get("onclick") or "")
            if onclick and not self.open_links:
                link = self._tag("a", [("href", onclick.group(1)), ("target", "_blank"), ("referrerpolicy", "origin")])
                image = f"{link}{image}</a>"
            self.out.append(image)

    def handle_startendtag(self, tag, attrs):
        if tag == "img":
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "a" and self.open_links:
            self.open_links -= 1
            self.out.append("</a>")

    def result(self):
        return "".join(self.out) + "</a>" * self.open_links


def clean_badge_html(value):
    """Only <a> and <img> with https addresses survive; text, scripts, styles and handlers do not."""
    if not value:
        return ""
    cleaner = _BadgeCleaner()
    cleaner.feed(str(value))
    cleaner.close()
    return cleaner.result()

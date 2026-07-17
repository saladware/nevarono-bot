import re
from html import escape
from html.parser import HTMLParser


class SummaryCleaner(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.ignore_content = False

    def handle_starttag(self, tag: str, attrs: "list[tuple[str, str | None]]") -> None:
        if tag.lower() == "script":
            self.ignore_content = True
            return

        if self.ignore_content:
            return

        if tag.lower() in ("br", "div", "p", "span"):
            return

        if tag.lower() == "a":
            href_attr = next(
                (
                    f'{key}="{escape(attr_val)}"'
                    for key, attr_val in attrs
                    if key.lower() == "href" and attr_val
                ),
                "",
            )
            self.parts.append(f"<a {href_attr}>" if href_attr else "<a>")
        else:
            self.parts.append(f"<{tag}>")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script":
            self.ignore_content = False
            return

        if self.ignore_content:
            return

        if tag.lower() in ("div", "p"):
            if self.parts[-1] != "\n":
                self.parts.append("\n")
            return

        if tag.lower() in ("br", "span"):
            return

        self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:  # noqa: WPS110
        if not self.ignore_content:
            self.parts.append(data)


def clean_summary(summary_html: str) -> str:
    if not summary_html.strip():
        return summary_html

    parser = SummaryCleaner()
    parser.feed(summary_html)
    cleaned = "".join(parser.parts)

    cleaned = cleaned.replace("&nbsp;", " ")
    return re.sub(r"[ \t]{2,}", " ", cleaned).rstrip()

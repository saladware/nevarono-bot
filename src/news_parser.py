import json
import re
from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
from urllib.request import urlopen
from xml.etree import ElementTree as ET

from src.exceptions import NewsParsingError
from src.news import Author, NewsItem

DOMAIN = "nevarono.spb.ru"


namespaces = {"atom": "http://www.w3.org/2005/Atom"}


def parse_news(
    page: int = 1, limit: int = 10, path: str = "novosti.html"
) -> "list[NewsItem]":
    path = path.lstrip("/")

    with urlopen(
        f"https://{DOMAIN}/{path}?format=json&limit={limit}&page={page}"
    ) as response:
        json_output = json.load(response)

    return [
        NewsItem(
            id=int(news_item["id"]),
            title=news_item["title"],
            url=f"{DOMAIN}{news_item['link']}",
            published_at=_parse_datetime(news_item["created"]),
            updated_at=(
                _parse_datetime(
                    news_item["created"]
                    if news_item["modified"] == "0000-00-00 00:00:00"
                    else news_item["modified"]
                )
            ),
            author=Author(name=news_item["author"]["name"], email=""),
            is_important=news_item["featured"] == "1",
            category=news_item["category"]["name"],
            summary=_clean_summary(news_item["introtext"]),
            keywords=[tag["name"] for tag in news_item["tags"]],
        )
        for news_item in json_output["items"]
    ]


def _parse_datetime(datetime_str: str) -> datetime:
    dt_format = "%Y-%m-%d %H:%M:%S"
    return datetime.strptime(datetime_str, dt_format).replace(tzinfo=timezone.utc)


def _get_text(element: ET.Element, path: str) -> str:
    text = element.findtext(path, namespaces=namespaces)
    if text is None:
        msg = f"Missing required element text: {path}"
        raise NewsParsingError(msg)
    return text


def _parse_author(entry: ET.Element) -> Author:  # pyright: ignore[reportUnusedFunction]
    author_elem = entry.find("atom:author", namespaces)
    if author_elem is None:
        msg = "Missing author element"
        raise NewsParsingError(msg)

    return Author(
        name=_get_text(author_elem, "atom:name"),
        email=_get_text(author_elem, "atom:email"),
    )


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

        no_gap = self.parts[-1] == "\n\n"
        if tag.lower() in ("div", "p") and no_gap:
            self.parts.append("\n\n")
            return

        if tag.lower() in ("br", "span"):
            return

        self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:  # noqa: WPS110
        if not self.ignore_content:
            self.parts.append(data)


def _clean_summary(summary_html: str) -> str:
    if not summary_html.strip():
        return summary_html

    parser = SummaryCleaner()
    parser.feed(summary_html)
    cleaned = "".join(parser.parts)

    cleaned = cleaned.replace("&nbsp;", " ")
    return re.sub(r"[ \t]{2,}", " ", cleaned)

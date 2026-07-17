import json
import re
from datetime import datetime, timezone
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


def _clean_summary(summary_html: str) -> str:
    if not summary_html.strip():
        return summary_html

    pattern = re.compile(
        r'\b(style|class)\s*=\s*(?:\'[^\']*\'|"[^"]*"|[^\s>]+)', re.IGNORECASE
    )

    # remove scripts
    cleaned = re.sub(
        r"<script\b[^>]*>([\s\S]*?)</script>", "", summary_html, flags=re.IGNORECASE
    )

    # remove br tag
    cleaned = re.sub(r"</?br\s*/?>", "", cleaned, flags=re.IGNORECASE)

    # remove style and class attrs
    cleaned = pattern.sub("", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+>", ">", cleaned)

    # remove div, p, span tags (without content)
    cleaned = re.sub(r"</?(div|p|span)(?:\s+[^>]*)?>", "", cleaned)

    # replace hard whitespace to soft
    cleaned = cleaned.replace("&nbsp;", " ")
    return re.sub(r"\n+", "\n\n", cleaned)

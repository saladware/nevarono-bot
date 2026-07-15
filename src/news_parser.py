import re
from datetime import datetime
from urllib.request import urlopen
from xml.etree import ElementTree as ET

from src.exceptions import NewsParsingError
from src.news import Author, NewsItem

DOMAIN = "nevarono.spb.ru"


namespaces = {"atom": "http://www.w3.org/2005/Atom"}


def parse_news(page: int = 0, path: str = "novosti.html") -> "list[NewsItem]":
    start = page * 10
    path = path.lstrip("/")

    with urlopen(
        f"https://{DOMAIN}/{path}?format=feed&type=atom&start={start}"
    ) as response:
        xml_data = response.read().decode("utf-8")

    root = ET.fromstring(xml_data)  # noqa: S314 trusted xml

    return [
        NewsItem(
            id=_parse_post_id(entry),
            title=_get_text(entry, "atom:title"),
            url=_get_text(entry, "atom:id"),
            published_at=_parse_datetime(_get_text(entry, "atom:published")),
            updated_at=_parse_datetime(_get_text(entry, "atom:updated")),
            author=_parse_author(entry),
            is_important=False,
            category=_get_category(entry),
            summary=_clean_summary(_get_text(entry, "atom:summary")),
        )
        for entry in root.findall("atom:entry", namespaces)
    ]


def _parse_post_id(entry: ET.Element) -> int:
    url = _get_text(entry, "atom:id")
    last = url.rstrip("/").split("/")[-1]

    match = re.match(r"^(\d+)", last)
    if not match:
        msg = f"cannot parse news id from string: {last}"
        raise NewsParsingError(msg)

    return int(match.group(1))


def _parse_datetime(datetime_str: str) -> datetime:
    published_str = re.sub(r"([+-]\d{2}):(\d{2})$", r"\1\2", datetime_str)
    return datetime.strptime(published_str, "%Y-%m-%dT%H:%M:%S%z")


def _get_text(element: ET.Element, path: str) -> str:
    text = element.findtext(path, namespaces=namespaces)
    if text is None:
        msg = f"Missing required element text: {path}"
        raise NewsParsingError(msg)
    return text


def _get_category(entry: ET.Element) -> str:
    category_el = entry.find("atom:category", namespaces)
    if category_el is None:
        msg = "Missing category element"
        raise NewsParsingError(msg)
    category = category_el.get("term")
    if category is None:
        msg = "Missing category term attribute"
        raise NewsParsingError(msg)
    return category


def _parse_author(entry: ET.Element) -> Author:
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
    cleaned = pattern.sub("", summary_html)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+>", ">", cleaned)
    cleaned = re.sub(r"</?(div|p|span)(?:\s+[^>]*)?>", "", cleaned)
    cleaned = cleaned.replace("&nbsp;", " ")
    return re.sub(r"\n+", "\n\n", cleaned)

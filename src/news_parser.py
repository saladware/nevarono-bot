import re
from datetime import datetime, timezone
from logging import getLogger
from typing import NamedTuple
from xml.etree import ElementTree as ET

from src.api import get_news_json, get_news_xml
from src.cleaner import clean_summary
from src.exceptions import NewsParsingError
from src.news import Attachment, Author, NewsItem

DOMAIN = "nevarono.spb.ru"


namespaces = {"atom": "http://www.w3.org/2005/Atom"}

logger = getLogger(__name__)


class XMLEntryPayload(NamedTuple):
    summary: str
    author_email: str


def parse_email_and_summary_from_entries(
    entries: "list[ET.Element]",
) -> "dict[int, XMLEntryPayload]":
    payload: dict[int, XMLEntryPayload] = {}
    for entry in entries:
        entry_url = _get_text(entry, "atom:id")
        entry_id = _parse_post_id_from_url(entry_url)
        payload[entry_id] = XMLEntryPayload(
            summary=_get_text(entry, "atom:summary"),
            author_email=_get_text(entry, "atom:author/atom:email"),
        )
    return payload


def parse_news(page: int = 1, path: str = "/novosti") -> "list[NewsItem]":  # noqa: WPS210
    news: list[NewsItem] = []
    xml_entries = get_news_xml(page, path)
    xml_entries_payload = parse_email_and_summary_from_entries(xml_entries)
    json_entries = get_news_json(page, len(xml_entries), path)

    for entry in json_entries:
        entry_id = int(entry["id"])
        xml_payload = xml_entries_payload.get(entry_id)
        if xml_payload is None:
            author_email = ""
            summary = entry["introtext"]
            logger.warning("no match betwean json and xml. fallback to json values")
        else:
            author_email = xml_payload.author_email
            summary = xml_payload.summary
        published_at = _parse_datetime(entry["created"])
        news_item = NewsItem(
            id=entry_id,
            title=entry["title"],
            url=f"https://{DOMAIN}{entry['link']}",
            published_at=published_at,
            updated_at=(
                published_at
                if entry["modified"] == "0000-00-00 00:00:00"
                else _parse_datetime(entry["modified"])
            ),
            author=Author(name=entry["author"]["name"], email=author_email),
            is_important=entry["featured"] == "1",
            category=entry["category"]["name"],
            summary=clean_summary(summary),
            keywords=[tag["name"] for tag in entry["tags"]],
            attachments=[
                Attachment(
                    filename=attachment["filename"],
                    link=f"https://{DOMAIN}{attachment['link']}",
                )
                for attachment in entry["attachments"]
            ],
        )
        news.append(news_item)
    return news


def _parse_post_id_from_url(url: str) -> int:
    last = url.rstrip("/").split("/")[-1]

    match = re.match(r"^(\d+)", last)
    if not match:
        msg = f"cannot parse news id from string: {last}"
        raise NewsParsingError(msg)

    return int(match.group(1))


def _parse_datetime(datetime_str: str) -> datetime:
    dt_format = "%Y-%m-%d %H:%M:%S"
    return datetime.strptime(datetime_str, dt_format).replace(tzinfo=timezone.utc)


def _get_text(element: ET.Element, path: str) -> str:
    text = element.findtext(path, namespaces=namespaces)
    if text is None:
        msg = f"Missing required element text: {path}"
        raise NewsParsingError(msg)
    return text

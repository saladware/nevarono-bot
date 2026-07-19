import json
from typing import Literal, TypedDict, cast
from xml.etree import ElementTree as ET

from src.fetch import fetch

DOMAIN = "nevarono.spb.ru"
namespaces = {"atom": "http://www.w3.org/2005/Atom"}


def get_news_xml(page: int = 1, path: str = "/novosti") -> "list[ET.Element]":
    start = (page - 1) * 10
    queries = {"format": "feed", "type": "atom", "start": str(start)}
    with fetch(f"https://{DOMAIN}/{path.lstrip('/')}", queries=queries) as response:
        return ET.parse(response).findall("atom:entry", namespaces)  # noqa: S314


class AuthorDict(TypedDict):
    name: str
    email: str


class CategoryDict(TypedDict):
    name: str


class TagDict(TypedDict):
    name: str


class AttachmentDict(TypedDict):
    filename: str
    link: str


class NewsDict(TypedDict):
    id: str
    title: str
    link: str
    created: str
    modified: str
    featured: "Literal['1', '0']"
    author: AuthorDict
    category: CategoryDict
    introtext: str
    tags: "list[TagDict]"
    attachments: "list[AttachmentDict]"


def get_news_json(
    page: int = 1, limit: int = 10, path: str = "/novosti"
) -> "list[NewsDict]":
    queries = {"format": "json", "limit": str(limit), "page": str(page)}
    with fetch(f"https://{DOMAIN}/{path.lstrip('/')}", queries=queries) as response:
        return cast("list[NewsDict]", json.load(response)["items"])

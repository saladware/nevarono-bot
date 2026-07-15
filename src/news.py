from datetime import datetime
from typing import NamedTuple


class Author(NamedTuple):
    name: str
    email: str


class NewsItem(NamedTuple):
    id: int
    title: str
    url: str
    is_important: bool
    published_at: datetime
    updated_at: datetime
    category: str
    author: Author
    summary: str

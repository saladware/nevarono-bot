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
    keywords: "list[str]" = []  # noqa: RUF012 temp

    def __str__(self) -> str:
        important_mark = "⚠️ " if self.is_important else ""
        keyword_hashtags = " ".join(map(_hashtag, self.keywords))
        published_str = self.published_at.strftime("%d.%m.%Y  %H:%M")
        return (
            f"{important_mark}"
            f'<b><a href="{self.url}">{self.title}</a></b>\n\n'
            f"{self.summary}\n\n"
            f"{published_str}\n\n"
            f"{_hashtag(self.category)} {keyword_hashtags}"
        )


def _hashtag(keyword: str) -> str:
    snaked_keyword = "_".join(keyword.split())
    return f"#{snaked_keyword}"

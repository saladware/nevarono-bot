import logging
import sys
from contextlib import ExitStack
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING

from src.bot import MediaGroupItem, SendMessageResult, TelegramBot
from src.config import get_config
from src.fetch import fetch
from src.news_parser import parse_news

if TYPE_CHECKING:
    from http.client import HTTPResponse

    from src.news import NewsItem


logger = logging.getLogger(__name__)

DB_FILE = Path("published_ids.txt")
MAX_IDS = 20


def load_published_ids(filepath: Path) -> "list[int]":
    if not filepath.exists():
        return []
    try:
        with filepath.open("r", encoding="utf-8") as file_obj:
            return [int(line.strip()) for line in file_obj if line.strip().isdigit()]
    except Exception:
        logger.exception("Error during reading IDs file")
        return []


def save_published_ids(
    filepath: Path, ids: "list[int]", max_size: int = MAX_IDS
) -> None:
    trimmed_ids = ids[-max_size:]
    try:
        with filepath.open("w", encoding="utf-8") as file_obj:
            for news_id in trimmed_ids:
                file_obj.write(f"{news_id}\n")
    except Exception:
        logger.exception("Error during writing IDs file")


def publish_news(bot: TelegramBot, chat_id: int, news: "NewsItem") -> bool:
    msg = publish_news_text(bot, chat_id, news)
    if msg is None:
        return False
    if not news.attachments:
        return True
    return publish_attachments(bot, chat_id, news, msg["message_id"])


def publish_news_text(
    bot: TelegramBot, chat_id: int, news: "NewsItem"
) -> "SendMessageResult | None":
    try:
        msg = bot.send_message(chat_id=chat_id, text=str(news), parse_mode="HTML")
    except Exception:
        logger.exception("Error sending message to Telegram %s", news.url)
        return None
    else:
        logger.info("News published with ID %s", news.id)
        return msg


def publish_attachments(
    bot: TelegramBot, chat_id: int, news: "NewsItem", reply_to_message_id: int
) -> bool:
    try:
        with ExitStack() as stack:
            files: list[HTTPResponse] = []
            for attach in news.attachments:
                resp = stack.enter_context(fetch(attach.link))
                resp.name = attach.filename  # type: ignore[misc]  # ty: ignore[invalid-assignment]
                files.append(resp)

            if len(files) == 1:
                bot.send_document(chat_id, files[0], reply_id=reply_to_message_id)
            else:
                media = [MediaGroupItem("document", file_obj) for file_obj in files]
                bot.send_media_group(chat_id, media, reply_id=reply_to_message_id)
    except Exception:
        logger.exception("Error sending attachments to Telegram %s", news.url)
        return False
    else:
        return True


def filter_new_news_items(
    news: "list[NewsItem]",
    published_ids: "list[int]",
) -> "list[NewsItem]":
    new_items = [new_item for new_item in news if new_item.id not in published_ids]
    new_items.sort(key=lambda new_item: new_item.published_at)

    if new_items:
        logger.info("New %s news", len(new_items))
    else:
        logger.info("Nothing to publish")

    return new_items


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    config = get_config()

    bot = TelegramBot(config.bot_token)
    try:
        news_items = parse_news()
    except Exception:
        logger.exception("Unable to parse news")
        return 1

    if not news_items:
        logger.error("No news")
        return 2

    published_ids = load_published_ids(DB_FILE)

    news_items = filter_new_news_items(news_items, published_ids)
    if not news_items:
        return 0

    for new_item in news_items:
        publish_news(bot, config.chat_id, new_item)
        sleep(3)
        published_ids.append(new_item.id)

    save_published_ids(DB_FILE, published_ids)

    return 0


if __name__ == "__main__":
    sys.exit(main())

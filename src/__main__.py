import logging
import sys
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING

from src.bot import TelegramBot
from src.config import get_config
from src.fetch import fetch
from src.news_parser import parse_news

if TYPE_CHECKING:
    from src.news import NewsItem

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
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
    try:
        bot.send_message(chat_id=chat_id, text=str(news), parse_mode="HTML")
    except Exception:
        logger.exception("Error sending message to Telegram %s", news.url)
        return False
    else:
        logger.info("News published with ID %s", news.id)
    is_ok = True
    for attachment in news.attachments:
        with fetch(attachment.link) as response:
            try:
                bot.send_local_document(chat_id, response)
            except Exception:
                logger.exception(
                    "Error sending file to Telegram %s %s", news.url, attachment.link
                )
                is_ok = False
    return is_ok


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
    logging.basicConfig(level="DEBUG")
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

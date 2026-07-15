import logging
from pathlib import Path
from typing import TYPE_CHECKING

from src.bot import TelegramBot
from src.config import get_config
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


def publish_news(
    bot: TelegramBot,
    chat_id: int,
    new_items: "list[NewsItem]",
    published_ids: "list[int]",
) -> None:
    try:
        for new_item in new_items:
            bot.send_message(chat_id=chat_id, text=new_item.summary, parse_mode="HTML")
            logger.info("News published with ID %s", new_item.id)
            published_ids.append(new_item.id)
    except Exception:
        logger.exception("Error sending to Telegram")


def filter_new_items(
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


def main() -> None:
    logging.basicConfig(level="DEBUG")
    config = get_config()
    bot = TelegramBot(config.bot_token)

    try:
        news = parse_news(page=0)
    except Exception:
        logger.exception("Unable to parse news")
        return

    if not news:
        logger.info("No news")
        return

    published_ids = load_published_ids(DB_FILE)

    new_items = filter_new_items(news, published_ids)
    if not new_items:
        return

    publish_news(bot, config.chat_id, new_items, published_ids)
    save_published_ids(DB_FILE, published_ids)


if __name__ == "__main__":
    main()

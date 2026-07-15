import json
from logging import getLogger
from urllib.error import HTTPError
from urllib.request import Request, urlopen

DOMAIN = "api.telegram.org"

logger = getLogger(__name__)


class TelegramBot:
    def __init__(self, bot_token: str) -> None:
        self._bot_token = bot_token

    def send_message(self, chat_id: int, text: str, parse_mode: str = "HTML") -> object:
        return self._call_method(
            "sendMessage",
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
        )

    def _call_method(self, method: str, **payload: object) -> object:
        try:
            with urlopen(
                Request(
                    f"https://{DOMAIN}/bot{self._bot_token}/{method}",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json; charset=utf-8"},
                )
            ) as response:
                return json.load(response)
        except HTTPError as exc:
            logger.exception("%s", exc.read().decode())
            raise


if __name__ == "__main__":
    from src.config import get_config

    config = get_config()
    bot = TelegramBot(config.bot_token)
    logger.info("%s", bot.send_message(config.chat_id, "hello"))

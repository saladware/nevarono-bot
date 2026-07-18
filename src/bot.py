import json
from logging import getLogger
from typing import Any, BinaryIO, Generic, Literal, TypedDict, TypeVar, cast

from src.fetch import fetch
from src.multipart import MultipartBuilder

DOMAIN = "api.telegram.org"

logger = getLogger(__name__)


_TelegramResult = TypeVar("_TelegramResult")


class TelegramOutput(TypedDict, Generic[_TelegramResult]):
    ok: "Literal[True]"
    result: _TelegramResult  # noqa: WPS110


class SendMessageResult(TypedDict):
    message_id: int


class TelegramBot:
    def __init__(self, bot_token: str) -> None:
        self._bot_token = bot_token

    def send_message(
        self,
        chat_id: int,
        text: str,
        reply_id: "int | None" = None,
        parse_mode: str = "HTML",
    ) -> SendMessageResult:
        payload: dict[str, object] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_id is not None:
            payload["reply_parameters"] = {"message_id": reply_id}
        output = cast(
            "TelegramOutput[SendMessageResult]",
            self._call_method("sendMessage", **payload),
        )
        return output["result"]

    def send_document_by_url(
        self,
        chat_id: int,
        url: str,
        caption: "str | None" = None,
        reply_id: "int | None" = None,
        parse_mode: str = "HTML",
    ) -> SendMessageResult:
        payload: dict[str, object] = {
            "chat_id": chat_id,
            "document": url,
        }
        if reply_id is not None:
            payload["reply_parameters"] = {"message_id": reply_id}
        if caption is not None:
            payload["caption"] = caption
            payload["parse_mode"] = parse_mode
        output = cast(
            "TelegramOutput[SendMessageResult]",
            self._call_method("sendDocument", **payload),
        )
        return output["result"]

    def send_local_document(
        self,
        chat_id: int,
        file_obj: BinaryIO,
        caption: "str | None" = None,
        reply_id: "int | None" = None,
        parse_mode: str = "HTML",
    ) -> SendMessageResult:
        builder = MultipartBuilder()
        builder.add_field("chat_id", chat_id)
        builder.add_file("document", file_obj)

        if reply_id is not None:
            builder.add_field("reply_parameters", {"message_id": reply_id})
        if caption is not None:
            builder.add_field("caption", caption)
            builder.add_field("parse_mode", parse_mode)

        with fetch(
            domain=DOMAIN,
            path=f"/bot{self._bot_token}/sendDocument",
            payload=builder.build_chunked(),
            headers=builder.headers(),
        ) as response:
            output = cast("TelegramOutput[SendMessageResult]", json.load(response))
            return output["result"]

    def _call_method(self, method: str, **payload: object) -> TelegramOutput[Any]:
        with fetch(
            domain=DOMAIN,
            path=f"/bot{self._bot_token}/{method}",
            payload=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
        ) as response:
            return cast("TelegramOutput[Any]", json.load(response))


if __name__ == "__main__":
    from src.config import get_config

    config = get_config()
    bot = TelegramBot(config.bot_token)
    logger.info(
        "%s",
        bot.send_document_by_url(
            config.chat_id,
            "https://nevarono.spb.ru/novosti/141-obshchie-dokumenty-gou-shkoly/download/12802_477e3ad34e6e01438c4a9f609c067f9c.html",
        ),
    )

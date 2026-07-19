import json
from logging import getLogger
from typing import TYPE_CHECKING, BinaryIO, TypedDict, cast

from src.fetch import fetch
from src.multipart import MultipartBuilder

if TYPE_CHECKING:
    from collections.abc import Generator

DOMAIN = "api.telegram.org"

logger = getLogger(__name__)


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
        output = self._call_method("sendMessage", **payload)
        return cast("SendMessageResult", output)

    def send_document(
        self,
        chat_id: int,
        file_obj: BinaryIO,
        caption: "str | None" = None,
        reply_id: "int | None" = None,
        parse_mode: str = "HTML",
    ) -> SendMessageResult:
        payload: dict[str, object] = {"document": file_obj, "chat_id": chat_id}

        if reply_id is not None:
            payload["reply_parameters"] = {"message_id": reply_id}
        if caption is not None:
            payload["caption"] = caption
            payload["parse_mode"] = parse_mode
        output = self._call_method("sendDocument", **payload)
        return cast("SendMessageResult", output)

    def _prepare_request(
        self, payload: "dict[str, object]"
    ) -> "tuple[bytes | Generator[bytes, None, None], dict[str,str]]":
        if any(hasattr(payload_val, "read") for payload_val in payload.values()):
            builder = MultipartBuilder()
            for key, payload_val in payload.items():
                if hasattr(payload_val, "read"):
                    builder.add_file(key, cast("BinaryIO", payload_val))
                else:
                    builder.add_field(key, payload_val)
            return builder.build_chunked(), builder.headers()

        return json.dumps(payload).encode("utf-8"), {
            "Content-Type": "application/json; charset=utf-8"
        }

    def _call_method(self, method: str, **payload: object) -> object:
        body, headers = self._prepare_request(payload)

        with fetch(
            f"https://{DOMAIN}/bot{self._bot_token}/{method}",
            payload=body,
            headers=headers,
        ) as response:
            return json.load(response)["result"]

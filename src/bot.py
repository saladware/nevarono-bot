import json
from logging import getLogger
from typing import TYPE_CHECKING, BinaryIO, Literal, NamedTuple, TypedDict, cast

from src.fetch import fetch
from src.multipart import MultipartBuilder

if TYPE_CHECKING:
    from collections.abc import Generator

DOMAIN = "api.telegram.org"

logger = getLogger(__name__)


class SendMessageResult(TypedDict):
    message_id: int


class MediaGroupItem(NamedTuple):
    type: Literal["photo", "video", "document", "audio"]
    media: BinaryIO
    caption: "str | None" = None
    parse_mode: "str | None" = None


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

    def send_media_group(
        self,
        chat_id: int,
        media_files: "list[MediaGroupItem]",
        reply_id: "int | None" = None,
        default_parse_mode: str = "HTML",
    ) -> "list[SendMessageResult]":
        payload: dict[str, object] = {"chat_id": chat_id}
        media_structure: list[dict[str, object]] = []

        for index, media_file in enumerate(media_files):
            payload[f"media_{index}"] = media_file.media
            media_item: dict[str, object] = {
                "type": media_file.type,
                "media": f"attach://media_{index}",
            }
            if media_file.caption:
                media_item["caption"] = media_file.caption
                media_item["parse_mode"] = media_file.parse_mode or default_parse_mode

            media_structure.append(media_item)

        payload["media"] = media_structure

        if reply_id is not None:
            payload["reply_parameters"] = {"message_id": reply_id}

        return cast(
            "list[SendMessageResult]", self._call_method("sendMediaGroup", **payload)
        )

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

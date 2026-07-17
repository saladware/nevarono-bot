from logging import getLogger
from typing import TYPE_CHECKING, MutableMapping, cast
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from http.client import HTTPResponse

logger = getLogger()


def fetch(
    domain: str,
    path: str,
    queries: "dict[str, str] | None" = None,
    headers: "MutableMapping[str, str] | None" = None,
    payload: "bytes | None" = None,
) -> "HTTPResponse":
    query = f"?{urlencode(queries)}" if queries else ""
    try:
        response = urlopen(
            Request(
                f"https://{domain}/{path.lstrip('/')}{query}",
                headers=headers or {},
                data=payload,
            )
        )
    except HTTPError as exc:
        logger.exception("Request error: %s", exc.read().decode())
        raise
    else:
        return cast("HTTPResponse", response)

from logging import getLogger
from typing import TYPE_CHECKING, MutableMapping, cast
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from collections.abc import Iterable
    from http.client import HTTPResponse

logger = getLogger()


def fetch(  # noqa: WPS211, PLR0913
    domain: str,
    path: str,
    *,
    queries: "dict[str, str] | None" = None,
    headers: "MutableMapping[str, str] | None" = None,
    payload: "bytes | Iterable[bytes] | None" = None,
    timeout: float = 5,
) -> "HTTPResponse":
    query = f"?{urlencode(queries)}" if queries else ""
    try:
        response = urlopen(
            Request(
                f"https://{domain}/{path.lstrip('/')}{query}",
                headers=headers or {},
                data=payload,
            ),
            timeout=timeout,
        )
    except HTTPError as exc:
        logger.exception("Request error: %s", exc.read().decode())

        raise
    else:
        return cast("HTTPResponse", response)

from logging import getLogger
from typing import TYPE_CHECKING, MutableMapping, cast
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from collections.abc import Iterable
    from http.client import HTTPResponse

logger = getLogger()


def fetch(
    url: str,
    *,
    queries: "dict[str, str] | None" = None,
    headers: "MutableMapping[str, str] | None" = None,
    payload: "bytes | Iterable[bytes] | None" = None,
    timeout: float = 5,
) -> "HTTPResponse":
    if not (url.startswith(("https://", "http://"))):
        msg = "url must start with https:// or http://"
        raise ValueError(msg)

    parsed_url = urlsplit(url)

    url_queries = dict(parse_qsl(parsed_url.query))
    if queries:
        url_queries.update(queries)

    new_query = urlencode(url_queries)
    tail_url = urlunsplit(
        (
            "",
            "",
            parsed_url.path,
            new_query,
            parsed_url.fragment,
        )
    )

    try:
        return cast(
            "HTTPResponse",
            urlopen(
                Request(
                    f"https://{parsed_url.netloc}{tail_url}",
                    headers=headers or {},
                    data=payload,
                ),
                timeout=timeout,
            ),
        )
    except HTTPError as exc:
        logger.exception("Request error: %s", exc.read().decode())
        raise

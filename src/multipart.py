import json
from typing import BinaryIO, Generator, NamedTuple
from uuid import uuid4


class Multipart(NamedTuple):
    body: bytes
    headers: "dict[str, str]"


class FieldPart(NamedTuple):
    name: bytes
    field_val: bytes


class FilePart(NamedTuple):
    name: bytes
    file_obj: BinaryIO
    content_type: bytes


class MultipartBuilder:
    chunk_size = 65536

    def __init__(self) -> None:
        self._parts: list[FieldPart | FilePart] = []
        self.boundary = b"----Boundary%x" % uuid4().int

    def add_field(self, name: str, field_val: object) -> None:
        if isinstance(field_val, str):
            payload = field_val.encode()
        elif isinstance(field_val, (list, dict)):
            payload = json.dumps(field_val).encode()
        else:
            msg = f"cannot add field with value of type {field_val.__class__}"
            raise TypeError(msg)
        self._parts.append(FieldPart(name.encode(), payload))

    def add_file(
        self,
        name: str,
        file_obj: BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> None:
        self._parts.append(FilePart(name.encode(), file_obj, content_type.encode()))

    def build_chunked(self) -> Generator[bytes, None, None]:
        for part in self._parts:
            if isinstance(part, FieldPart):
                fmt = b'--%b\r\nContent-Disposition: form-data; name="%b"\r\n\r\n'
                yield fmt % (self.boundary, part.name)
                yield b"%b\r\n" % part.field_val
            else:
                fmt = (
                    b'--%b\r\nContent-Disposition: form-data; name="%b"; filename="%b"'
                    b"\r\nContent-Type: %b\r\n\r\n"
                )
                args = (
                    self.boundary,
                    part.name,
                    getattr(part.file_obj, "name", "unknown").encode(),
                    part.content_type,
                )
                yield fmt % args

                yield from _read_file_chunked(part.file_obj, self.chunk_size)

                yield b"\r\n"

        yield b"--%b--\r\n" % self.boundary

    def build(self) -> bytes:
        return b"".join(list(self.build_chunked()))

    def headers(self) -> "dict[str, str]":
        boundary = self.boundary.decode()
        return {"Content-Type": f"multipart/form-data; boundary={boundary}"}


def _read_file_chunked(
    file_obj: BinaryIO, chunk_size: int
) -> Generator[bytes, None, None]:
    while True:
        chunk = file_obj.read(chunk_size)
        if not chunk:
            break
        yield chunk

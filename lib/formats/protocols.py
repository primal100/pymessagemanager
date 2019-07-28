from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from pathlib import Path

from lib.conf.logging import ConnectionLogger

from typing import AsyncGenerator, Generator, Any, AnyStr, Dict, Sequence
from typing_extensions import Protocol
from .types import CodecType, MessageObjectType


class MessageObject(Protocol):

    @classmethod
    @abstractmethod
    def _get_codec_kwargs(cls) -> Dict:
        return {}

    @classmethod
    @abstractmethod
    def get_codec(cls, **kwargs) -> CodecType: ...

    @property
    @abstractmethod
    def sender(self) -> str: ...

    @property
    @abstractmethod
    def uid(self) -> Any: ...

    @property
    @abstractmethod
    def request_id(self) -> Any: ...

    @property
    @abstractmethod
    def pformat(self) -> str: ...

    @property
    @abstractmethod
    def timestamp(self) -> datetime: ...

    @abstractmethod
    def filter(self) -> bool: ...

    @abstractmethod
    def processed(self) -> None: ...


class BufferObjectProtocol(MessageObject, Protocol):

    @property
    @abstractmethod
    def record(self) -> bytes: ...


class Codec(Protocol):

    @abstractmethod
    def set_context(self, context, logger: ConnectionLogger = None) -> None: ...

    @abstractmethod
    def decode(self, encoded: bytes, **kwargs) -> Generator[Sequence[AnyStr, Any], None, None]: ...

    @abstractmethod
    def encode(self, decoded: Any, **kwargs) -> AnyStr: ...

    @abstractmethod
    def decode_buffer(self, encoded: AnyStr, **kwargs) -> Generator[MessageObjectType, None, None]: ...

    @abstractmethod
    def from_decoded(self, decoded: Any, **kwargs) -> MessageObjectType: ...

    @abstractmethod
    async def from_file(self, file_path: Path, **kwargs) -> AsyncGenerator[MessageObjectType, None]:
        yield

    @abstractmethod
    async def one_from_file(self, file_path: Path, **kwargs) -> MessageObjectType: ...
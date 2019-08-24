from __future__ import annotations
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from .protocols import ReceiverProtocol


ReceiverType = TypeVar('ReceiverType', bound='ReceiverProtocol')

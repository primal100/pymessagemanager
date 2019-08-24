from __future__ import annotations
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from .protocols import ActionProtocol


ActionType = TypeVar('ActionType', bound='ActionProtocol')

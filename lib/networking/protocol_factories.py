from __future__ import annotations
import asyncio
from dataclasses import dataclass, field

from lib.actions.protocols import OneWaySequentialAction, ParallelAction
from lib.formats.base import BaseMessageObject
from lib.requesters.types import RequesterType
from lib.conf.logging import Logger
from lib.utils import dataclass_getstate, dataclass_setstate, addr_tuple_to_str

from .connections_manager import connections_manager
from .connections import TCPClientConnection, OneWayTCPServerConnection, TCPServerConnection, UDPServerConnection
from .protocols import ProtocolFactoryProtocol
from .types import ProtocolFactoryType,  NetworkConnectionType

from typing import Any, Dict, Optional, Text, Tuple, Type, Union


@dataclass
class BaseProtocolFactory(ProtocolFactoryProtocol):
    full_name = ''
    peer_prefix = ''
    connection_cls: Type[NetworkConnectionType] = field(default=None, init=False)
    action: ParallelAction = None
    preaction: OneWaySequentialAction = None
    requester: RequesterType = None
    dataformat: Type[BaseMessageObject] = None
    context: Dict[str, Any] = field(default_factory=dict, metadata={'pickle': True})
    logger: Logger = Logger('receiver')
    pause_reading_on_buffer_size: int = 0

    def __call__(self) -> NetworkConnectionType:
        return self._new_connection()

    def _new_connection(self) -> NetworkConnectionType:
        context = self.context.copy()
        return self.connection_cls(parent_name=self.full_name, peer_prefix=self.peer_prefix, action=self.action,
                                   preaction=self.preaction, requester=self.requester, dataformat=self.dataformat,
                                   context=context, pause_reading_on_buffer_size=self.pause_reading_on_buffer_size,
                                   logger=self.logger)

    def __getstate__(self):
        return dataclass_getstate(self)

    def __setstate__(self, state):
        dataclass_setstate(self, state)

    def set_logger(self, logger: Logger) -> None:
        self.logger = logger

    def set_name(self, full_name: str, peer_prefix: str) -> None:
        self.full_name = full_name
        self.peer_prefix = peer_prefix

    def is_owner(self, connection: NetworkConnectionType) -> bool:
        return connection.is_child(self.full_name)

    async def wait_num_has_connected(self, num: int) -> None:
        await connections_manager.wait_num_has_connected(self.full_name, num)

    async def wait_num_connected(self, num: int) -> None:
        await connections_manager.wait_num_connections(self.full_name, num)

    async def wait_all_messages_processed(self) -> None:
        await connections_manager.wait_all_messages_processed(self.full_name)

    async def wait_all_closed(self) -> None:
        await connections_manager.wait_num_connections(self.full_name, 0)

    async def close_actions(self) -> None:
        coros = []
        if self.action:
            coros.append(self.action.close())
        if self.preaction:
            coros.append(self.preaction.close())
        if coros:
            await asyncio.wait(coros)

    async def close(self) -> None:
        await self.close_actions()


@dataclass
class StreamServerProtocolFactory(BaseProtocolFactory):
    connection_cls = TCPServerConnection


@dataclass
class StreamServerOneWayProtocolFactory(BaseProtocolFactory):
    connection_cls = OneWayTCPServerConnection
    action: OneWaySequentialAction = None


@dataclass
class StreamClientProtocolFactory(BaseProtocolFactory):
    connection_cls = TCPClientConnection


@dataclass
class UDPProtocolFactory(asyncio.DatagramProtocol, BaseProtocolFactory):
    connection_cls: NetworkConnectionType = UDPServerConnection
    transport = None
    sock = None

    def __call__(self: ProtocolFactoryType) -> ProtocolFactoryType:
        return self

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self.transport = transport
        self.sock = self.transport.get_extra_info('sockname')

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self.logger.manage_error(exc)
        for conn in filter(self.is_owner, connections_manager):
            conn.finish_connection(exc)

    def error_received(self, exc: Optional[Exception]) -> None:
        self.logger.manage_error(exc)

    def datagram_received(self, data: Union[bytes, Text], addr: Tuple[str, int]) -> None:
        conn = connections_manager.get(addr_tuple_to_str(addr), None)
        if conn:
            conn.on_data_received(data)
        else:
            conn = self._new_connection()
            conn.initialize_connection(self.transport, addr)
            conn.on_data_received(data)

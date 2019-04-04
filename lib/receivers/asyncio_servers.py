import asyncio
from abc import ABC, abstractmethod
from dataclasses import field

from pydantic.dataclasses import dataclass

from .base import BaseServer
from lib.conf.exceptions import ConfigurationException
from lib.networking.tcp import TCPServerProtocol
from lib.networking.udp import UDPServerProtocol
from lib.networking.ssl import ServerSideSSL


from typing import NoReturn


@dataclass
class BaseTCPServerReceiver(ABC, BaseServer):
    server = None

    @abstractmethod
    async def get_server(self): ...

    async def start_server(self) -> NoReturn:
        self.server = await self.get_server()
        async with self.server:
            self.print_listening_message(self.server.sockets)
            await self.server.serve_forever()

    async def stop_server(self) -> NoReturn:
        if self.server:
            self.server.close()


class TCPServerReceiver(BaseTCPServerReceiver):
    receiver_type = "TCP Server"

    protocol: TCPServerProtocol = TCPServerProtocol()
    ssl: ServerSideSSL = ServerSideSSL()
    ssl_handshake_timeout: int = 0

    async def get_server(self) -> asyncio.AbstractServer:
        return await self.loop.create_server(self.protocol,
            self.host, self.port, ssl=self.ssl, ssl_handshake_timeout=self.ssl_handshake_timeout)


class UDPServerReceiver(BaseServer):
    receiver_type = "UDP Server"
    transport = None

    protocol: UDPServerProtocol = UDPServerProtocol()

    _start_event: asyncio.Event = field(default_factory=asyncio.Event, repr=False, init=False, hash=False, compare=False)

    async def start_server(self) -> NoReturn:
        if self.loop.__class__.__name__ == 'ProactorEventLoop':
            raise ConfigurationException('UDP Server cannot be run on Windows Proactor Loop. Use Selector Loop instead')
        self.transport, self.protocol = await self.loop.create_datagram_endpoint(
            self.protocol, local_addr=(self.host, self.port))
        self.print_listening_message([self.transport.get_extra_info('socket')])
        await self.protocol.check_senders_expired(self.expiry_minutes)

    async def stop_server(self) -> NoReturn:
        if self.transport:
            self.transport.close()

    async def started(self) -> NoReturn:
        while not self.transport:
            await asyncio.sleep(0.001)

    async def stopped(self) -> NoReturn:
        if self.transport and self.transport.is_closing():
            await self.protocol.wait_closed()

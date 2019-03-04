import asyncio

from lib.conf import ConfigurationException
from lib.networking.asyncio_protocols import TCPClientProtocol, UDPClientProtocol
from .base import BaseNetworkClient, SSLSupportedNetworkClient


class BaseAsyncioMixin:
    transport = None
    protocol_cls = None
    connection_protocol = None

    @classmethod
    def from_config(cls, *args, cp=None, **kwargs):
        instance = super().from_config(*args, cp=cp, **kwargs)
        cls.protocol_cls = cls.protocol_cls.set_config(cp=cp, logger=instance.logger)
        return instance

    async def close_connection(self):
        self.transport.close()

    async def send_data(self, encoded_data, **kwargs):
        self.connection_protocol.send_msg(encoded_data)

    async def open_connection(self):
        raise NotImplementedError

    def get_protocol(self):
        return self.protocol_cls(self.manager)


class TCPClient(BaseAsyncioMixin, SSLSupportedNetworkClient):
    sender_type = "TCP Client"
    transport = None
    protocol_cls = TCPClientProtocol
    connection_protocol = None
    ssl_allowed = True

    async def open_connection(self):
        self.transport, self.connection_protocol = await asyncio.get_event_loop().create_connection(
            self.get_protocol, self.host, self.port,
            ssl=self.ssl, local_addr=self.localaddr, ssl_handshake_timeout=self.ssl_handshake_timeout)


class UDPClient(BaseAsyncioMixin, BaseNetworkClient):
    sender_type = "UDP Client"
    transport = None
    protocol_cls = UDPClientProtocol
    connection_protocol = None

    async def open_connection(self):
        loop = asyncio.get_event_loop()
        if loop.__class__.__name__ == 'ProactorEventLoop':
            raise ConfigurationException('UDP Server cannot be run on Windows Proactor Loop. Use Selector Loop instead')
        self.transport, self.connection_protocol = await asyncio.get_event_loop().create_datagram_endpoint(
            self.get_protocol, remote_addr=(self.host, self.port), local_addr=self.localaddr)

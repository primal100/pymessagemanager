import asyncio
from functools import partial

from lib.conf import ConfigurationException
from lib.networking.asyncio_protocols import TCPClientProtocol, UDPClientProtocol
from lib.networking.mixins import TCP
from lib.networking.ssl import ClientSideSSL
from .base import BaseNetworkClient


class BaseAsyncioClient(BaseNetworkClient):
    transport = None
    protocol_cls = None
    connection_protocol = None

    @classmethod
    def from_config(cls, *args, cp=None, config=None, **kwargs):
        instance = super().from_config(*args, cp=cp, config=config, **kwargs)
        instance.protocol_cls = cls.protocol_cls.with_config(cp=cp, logger=instance.logger)
        return instance

    async def close_connection(self):
        self.transport.close()

    async def send_data(self, encoded_data, **kwargs):
        self.connection_protocol.send_msg(encoded_data)

    async def open_connection(self):
        raise NotImplementedError


class TCPClient(TCP, BaseAsyncioClient):
    sender_type = "TCP Client"
    ssl_section_name = 'SSLClient'
    transport = None
    protocol_cls = TCPClientProtocol
    connection_protocol = None
    ssl_cls = ClientSideSSL
    configurable = BaseAsyncioClient.configurable.copy()
    configurable.update(TCP.configurable)

    def __init__(self, *args, ssl=None, sslhandshaketimeout: int=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssl = ssl
        self.ssl_handshake_timeout = sslhandshaketimeout

    async def open_connection(self):
        self.transport, self.connection_protocol = await asyncio.get_event_loop().create_connection(
            partial(self.protocol_cls, self.manager), self.host, self.port, ssl=self.ssl,
            local_addr=self.localaddr, ssl_handshake_timeout=self.ssl_handshake_timeout)


class UDPClient(BaseAsyncioClient):
    sender_type = "UDP Client"
    transport = None
    protocol_cls = UDPClientProtocol
    connection_protocol = None

    async def open_connection(self):
        loop = asyncio.get_event_loop()
        if loop.__class__.__name__ == 'ProactorEventLoop':
            raise ConfigurationException('UDP Server cannot be run on Windows Proactor Loop. Use Selector Loop instead')
        self.transport, self.connection_protocol = await asyncio.get_event_loop().create_datagram_endpoint(
            partial(self.protocol_cls, self.manager), remote_addr=(self.host, self.port), local_addr=self.localaddr)

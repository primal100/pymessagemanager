import asyncio
from asyncio import transports
import logging
from functools import partial
import time

from lib import messagemanagers
from .logging import ConnectionLogger, StatsLogger
from lib.utils import log_exception, addr_tuple_to_str

from typing import TYPE_CHECKING
from typing import Optional, Union, Text, Tuple

if TYPE_CHECKING:
    from asyncio import transports
    from lib.messagemanagers import BaseMessageManager
else:
    BaseMessageManager = None


class BaseProtocolMixin:
    stats_cls = StatsLogger
    name: str = ''
    logger_name: str = ''
    logger: None
    stats_logger = None
    alias: str = ''
    peer: str = ''
    sock = (None, None)
    peer_ip: str = None
    peer_port: int = 0
    transport = None

    @classmethod
    def set_config(cls, cp=None, logger=None):
        from lib import settings
        cp = cp or settings.CONFIG
        cls.cp = cp
        cls._logger = logger
        return cls

    def __init__(self, manager: BaseMessageManager, logger=None):
        self.manager = manager
        self._logger = logger or self._logger

    def get_logger_extra(self):
        return {'protocol_name': self.name,
                'peer_ip': self.peer_ip,
                'peer_port': self.peer_port,
                'peer': self.peer,
                'client': self.client,
                'server': self.server,
                'alias': self.alias}

    def get_stats_logger(self, extra):
        return self.stats_cls.from_config(self.logger.name, extra, self.transport, cp=self.cp)

    def get_logger(self, extra):
        return ConnectionLogger(self._logger, extra)

    @property
    def client(self):
        raise NotImplementedError

    @property
    def server(self):
        raise NotImplementedError

    def send(self, msg):
        raise NotImplementedError

    def send_msg(self, msg):
        self.send(msg)
        self.stats_logger.on_msg_sent(msg)

    def check_other(self, peer_ip):
        return self.manager.check_sender(peer_ip)

    def connection_made(self, transport):
        self.transport = transport
        peer = self.transport.get_extra_info('peername')
        sock = self.transport.get_extra_info('sockname')
        connection_ok = self.define_sock_peer(sock, peer)
        extra = self.get_logger_extra()
        self.logger = self.get_logger(extra)
        self.stats_logger = self.get_stats_logger(extra)
        if connection_ok:
            self.logger.info('New %s connection from %s to %s', self.name, self.client, self.server)

    def define_sock_peer(self, sock, peer):
        self.peer_ip = peer[0]
        self.peer_port = peer[1]
        self.peer = ':'.join(str(prop) for prop in peer)
        self.sock = ':'.join(str(prop) for prop in sock)
        try:
            self.alias = self.check_other(self.peer_ip)
            return True
        except messagemanagers.MessageFromNotAuthorizedHost:
            self.close_connection()
            return False

    def close_connection(self):
        self.transport.close()

    def connection_lost(self, exc):
        self.logger.manage_error(exc)
        self.logger.info('%s connection from %s to %s has been closed', self.name, self.client, self.server)
        self.stats_logger.connection_finished()

    def send_msgs(self, msgs):
        for msg in msgs:
            self.send_msg(msg)

    def task_callback(self, num_bytes, future):
        exc = future.exception()
        self.logger.manage_error(exc)
        responses = future.result()
        if responses:
            self.send_msgs(responses)
        self.stats_logger.on_msg_processed(num_bytes)

    def on_data_received(self, data, timestamp=None):
        self.logger.debug("Received msg from %s", self.alias)
        self.stats_logger.on_msg_received(data)
        task = self.manager.handle_message(self.alias, data, timestamp=timestamp)
        task.add_done_callback(partial(self.task_callback, len(data)))


class TCP(BaseProtocolMixin, asyncio.Protocol):

    def connection_lost(self, exc):
        super(TCP, self).connection_lost(exc)
        self.transport.close()

    @property
    def client(self):
        raise NotImplementedError

    @property
    def server(self):
        raise NotImplementedError

    def data_received(self, data):
        self.on_data_received(data)

    def send(self, msg):
        self.transport.write(msg)


class UDP(BaseProtocolMixin, asyncio.DatagramProtocol):

    @property
    def client(self):
        raise NotImplementedError

    @property
    def server(self):
        raise NotImplementedError

    def send(self, msg):
        self.transport.sendto(msg)

    def error_received(self, exc):
        self.logger.manage_error(exc)


class ClientProtocolMixin:
    logger_name = 'sender'

    @property
    def client(self) -> str:
        return self.sock

    @property
    def server(self) -> str:
        return self.peer


class ServerProtocolMixin:
    logger_name = 'receiver'

    @property
    def client(self) -> str:
        if self.alias:
            return '%s(%s)' % (self.alias, self.peer)
        return self.peer

    @property
    def server(self) -> str:
        return self.sock


class TCPServerProtocol(ServerProtocolMixin, TCP):
    name = 'TCP Server'


class TCPClientProtocol(ClientProtocolMixin, TCP):
    name = 'TCP Client'


class UDPServerClientProtocol(ServerProtocolMixin, UDP):
    name = 'UDP Server'

    def send(self, msg):
        self.transport.sendto(msg, addr=(self.peer_ip, self.peer_port))

    def connection_lost(self, exc):
        self.logger.manage_error(exc)
        self.stats_logger.connection_finished()

    def close_connection(self):
        pass


class UDPClientProtocol(ClientProtocolMixin, UDP):
    name = 'UDP Client'


class UDPServerProtocol(asyncio.DatagramProtocol):
    transport = None
    logger_name = 'receiver'
    sock = (None, None)
    name = "UDP Listener"
    client_protocol_class = UDPServerClientProtocol

    @classmethod
    def set_config(cls, cp=None, logger=None):
        cls.client_protocol_class.set_config(cp=cp, logger=logger)
        cls._logger = logger or cls.logger_name

    @property
    def server(self) -> str:
        return self.sock

    def __init__(self, manager: BaseMessageManager):
        self.logger = ConnectionLogger(self._logger, {})
        self.manager = manager
        self.clients = {}
        self.closed_event = asyncio.Event()

    def connection_made(self, transport: transports.BaseTransport):
        self.transport = transport
        self.sock = self.transport.get_extra_info('sockname')

    def connection_lost(self, exc: Optional[Exception]):
        self.logger.manage_error(exc)
        connections = list(self.clients.values())
        for conn in connections:
            conn.connection_lost(None)
        self.clients.clear()
        self.closed_event.set()

    async def wait_closed(self):
        await self.closed_event.wait()

    def error_received(self, exc: Exception):
        self.manage_error(exc)

    def new_sender(self, addr, src):
        connection_protocol = self.client_protocol_class(self.manager)
        connection_ok = connection_protocol.define_sock_peer(self.sock, addr)
        if connection_ok:
            self.clients[src] = connection_protocol
            self.logger.info('%s on %s started receiving messages from %s', self.name, self.server, src)
            return connection_protocol
        return False

    def datagram_received(self, data: Union[bytes, Text], addr: Tuple[str, int]):
        src = addr_tuple_to_str(addr)
        connection_protocol = self.clients.get(src, None)
        if connection_protocol:
            connection_protocol.on_data_received(data)
        else:
            connection_protocol = self.new_sender(addr, src)
            if connection_protocol:
                connection_protocol.on_data_received(data)

    async def check_senders_expired(self, expiry_minutes):
        now = time.time()
        connections = list(self.clients.values())
        for conn in connections:
            if (now - conn.last_message_processed) / 60 > expiry_minutes:
                conn.connection_lost(None)
                del self.clients[conn.peer]
        await asyncio.sleep(60)
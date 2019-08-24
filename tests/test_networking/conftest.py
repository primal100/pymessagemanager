import pytest
from pytest_lazyfixture import lazy_fixture
import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Tuple

from lib.conf.context import context_cv
from lib.conf.logging import connection_logger_cv, logger_cv
from lib.networking.adaptors import ReceiverAdaptor, SenderAdaptor
from lib.networking.connections import TCPServerConnection, TCPClientConnection
from lib.networking.connections_manager import ConnectionsManager
from lib.networking.protocol_factories import StreamServerProtocolFactory, StreamClientProtocolFactory
from lib.networking.types import SimpleNetworkConnectionType

from lib.receivers.base import BaseServer


from tests.mock import MockTCPTransport

from tests.test_actions.conftest import *
from tests.test_logging.conftest import *


@pytest.fixture
def initial_server_context() -> Dict[str, Any]:
    return {'endpoint': 'TCP Server 127.0.0.1:8888'}


@pytest.fixture
def initial_client_context() -> Dict[str, Any]:
    return {'endpoint': 'TCP Client 127.0.0.1:0'}


@pytest.fixture
def one_way_receiver_adaptor(buffered_file_storage_action, buffered_file_storage_recording_action, context,
                             receiver_connection_logger) -> ReceiverAdaptor:
    context_cv.set(context)
    connection_logger_cv.set(receiver_connection_logger)
    return ReceiverAdaptor(JSONObject, action=buffered_file_storage_action,
                           preaction=buffered_file_storage_recording_action)


@pytest.fixture
async def one_way_sender_adaptor(context_client, sender_connection_logger, deque) -> SenderAdaptor:
    context_cv.set(context_client)
    connection_logger_cv.set(sender_connection_logger)
    yield SenderAdaptor(JSONObject, send=deque.append)


@pytest.fixture
async def file_containing_json_recording(tmpdir, buffer_codec, json_encoded_multi, timestamp) -> Path:
    obj1 = buffer_codec.from_decoded(json_encoded_multi[0], received_timestamp=timestamp)
    await asyncio.sleep(1)
    obj2 = buffer_codec.from_decoded(json_encoded_multi[1],
                                     received_timestamp=timestamp + timedelta(seconds=1, microseconds=200000))
    p = Path(tmpdir.mkdir("recording") / "json.recording")
    p.write_bytes(obj1.encoded + obj2.encoded)
    return p


@pytest.fixture
def extra(peername, sock) -> dict:
    return {'peername': peername, 'sockname': sock}


@pytest.fixture
def extra_client(peername, sock) -> dict:
    return {'peername': sock, 'sockname': peername}


@pytest.fixture
async def tcp_transport(queue, extra) -> asyncio.Transport:
    yield MockTCPTransport(queue, extra=extra)


@pytest.fixture
async def tcp_transport_client(queue, extra_client) -> asyncio.Transport:
    yield MockTCPTransport(queue, extra=extra_client)


@pytest.fixture
def peername() -> Tuple[str, int]:
    return '127.0.0.1', 60000


@pytest.fixture
def sock() -> Tuple[str, int]:
    return '127.0.0.1', 8888


@pytest.fixture
def true() -> bool:
    return True


@pytest.fixture
def false() -> bool:
    return False


@pytest.fixture
def protocol_factory(connection_args):
    return connection_args[0]


@pytest.fixture
def connection(connection_args):
    return connection_args[1]


@pytest.fixture
def transport(connection_args):
    return connection_args[2]


@pytest.fixture
def adaptor(connection_args):
    return connection_args[3]


@pytest.fixture
def peer_data(connection_args):
    return connection_args[4]


@pytest.fixture
def connection_is_stored(connection_args):
    return connection_args[5]


@pytest.fixture
def protocol_factory_one_way_server(buffered_file_storage_action, buffered_file_storage_recording_action,
                                    receiver_logger, initial_server_context) -> StreamServerProtocolFactory:
    context_cv.set(initial_server_context)
    logger_cv.set(receiver_logger)
    factory = StreamServerProtocolFactory(
        preaction=buffered_file_storage_recording_action,
        action=buffered_file_storage_action,
        dataformat=JSONObject)
    if not factory.full_name:
        factory.set_name('TCP Server 127.0.0.1:8888', 'tcp')
    yield factory


@pytest.fixture
def protocol_factory_one_way_client(sender_logger, initial_client_context) -> StreamClientProtocolFactory:
    context_cv.set(initial_client_context)
    logger_cv.set(sender_logger)
    factory = StreamClientProtocolFactory(
        dataformat=JSONObject)
    if not factory.full_name:
        factory.set_name('TCP Client 127.0.0.1:0', 'tcp')
    yield factory


@pytest.fixture
async def tcp_protocol_one_way_server(buffered_file_storage_action, buffered_file_storage_recording_action,
                                      receiver_logger, initial_server_context) -> TCPServerConnection:
    logger_cv.set(receiver_logger)
    context_cv.set(initial_server_context)
    conn = TCPServerConnection(dataformat=JSONObject, action=buffered_file_storage_action,
                              parent_name="TCP Server 127.0.0.1:8888", peer_prefix='tcp',
                              preaction=buffered_file_storage_recording_action)
    yield conn
    if not conn.is_closing():
        conn.connection_lost(None)
    await conn.wait_closed()


@pytest.fixture
async def tcp_protocol_one_way_client(sender_logger, initial_client_context) -> TCPClientConnection:
    logger_cv.set(sender_logger)
    context_cv.set(initial_client_context)
    conn = TCPClientConnection(dataformat=JSONObject, peer_prefix='tcp', parent_name="TCP Client 127.0.0.1:0")
    yield conn
    if not conn.is_closing():
        conn.connection_lost(None)
    await conn.wait_closed()


@pytest.fixture(params=[
    lazy_fixture((
                 protocol_factory_one_way_server.__name__, tcp_protocol_one_way_server.__name__, tcp_transport.__name__,
                 one_way_receiver_adaptor.__name__, peername.__name__)) + [True],
    lazy_fixture((protocol_factory_one_way_client.__name__, tcp_protocol_one_way_client.__name__,
                  tcp_transport_client.__name__, one_way_sender_adaptor.__name__, sock.__name__)) + [False],
])
def connection_args(request):
    return request.param
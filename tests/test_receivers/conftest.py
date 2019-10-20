import asyncssh
from lib.receivers.base import BaseServer
from lib.receivers.sftp import SFTPServer
from lib.receivers.servers import TCPServer, UDPServer, pipe_server

from tests.test_networking.conftest import *
from lib.utils import pipe_address_by_os
from pytest_lazyfixture import lazy_fixture


@pytest.fixture
async def pipe_path() -> Path:
    path = pipe_address_by_os()
    yield path
    if path.exists():
        path.unlink()


@pytest.fixture
async def tcp_server_one_way(protocol_factory_one_way_server, sock) -> TCPServer:
    server = TCPServer(protocol_factory=protocol_factory_one_way_server, host=sock[0], port=sock[1])
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def tcp_server_two_way(protocol_factory_two_way_server, sock) -> TCPServer:
    server = TCPServer(protocol_factory=protocol_factory_two_way_server, host=sock[0], port=sock[1])
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def tcp_server_one_way_quiet(tcp_server_one_way) -> TCPServer:
    tcp_server_one_way.quiet = True
    yield tcp_server_one_way


@pytest.fixture
async def tcp_server_two_way_quiet(tcp_server_two_way) -> TCPServer:
    tcp_server_two_way.quiet = True
    yield tcp_server_two_way


@pytest.fixture
async def tcp_server_one_way_started(tcp_server_one_way) -> TCPServer:
    await tcp_server_one_way.start()
    yield tcp_server_one_way


@pytest.fixture
async def tcp_server_two_way_started(tcp_server_two_way) -> TCPServer:
    await tcp_server_two_way.start()
    yield tcp_server_two_way


@pytest.fixture
async def udp_server_one_way(udp_protocol_factory_one_way_server, sock) -> UDPServer:
    server = UDPServer(protocol_factory=udp_protocol_factory_one_way_server, host=sock[0], port=sock[1])
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def udp_server_two_way(udp_protocol_factory_two_way_server, sock) -> UDPServer:
    server = UDPServer(protocol_factory=udp_protocol_factory_two_way_server, host=sock[0], port=sock[1])
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def udp_server_one_way_quiet(udp_server_one_way) -> UDPServer:
    udp_server_one_way.quiet = True
    yield udp_server_one_way


@pytest.fixture
async def udp_server_two_way_quiet(udp_server_two_way) -> UDPServer:
    udp_server_two_way.quiet = True
    yield udp_server_two_way


@pytest.fixture
async def udp_server_one_way_started(udp_server_one_way) -> UDPServer:
    await udp_server_one_way.start()
    yield udp_server_one_way


@pytest.fixture
async def udp_server_two_way_started(udp_server_two_way) -> UDPServer:
    await udp_server_two_way.start()
    yield udp_server_two_way


@pytest.fixture
async def pipe_server_one_way(protocol_factory_one_way_server, pipe_path) -> BaseServer:
    server = pipe_server(protocol_factory=protocol_factory_one_way_server, path=pipe_path)
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def pipe_server_two_way(protocol_factory_two_way_server, pipe_path) -> BaseServer:
    server = pipe_server(protocol_factory=protocol_factory_two_way_server, path=pipe_path)
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def pipe_server_one_way_quiet(pipe_server_one_way) -> BaseServer:
    pipe_server_one_way.quiet = True
    yield pipe_server_one_way


@pytest.fixture
async def pipe_server_two_way_quiet(pipe_server_two_way) -> BaseServer:
    pipe_server_two_way.quiet = True
    yield pipe_server_two_way


@pytest.fixture
async def pipe_server_one_way_started(pipe_server_one_way) -> BaseServer:
    await pipe_server_one_way.start()
    yield pipe_server_one_way


@pytest.fixture
async def pipe_server_two_way_started(pipe_server_two_way) -> BaseServer:
    await pipe_server_two_way.start()
    yield pipe_server_two_way


@pytest.fixture
async def ssh_host_key(tmp_path) -> Path:
    private_path = Path(tmp_path) / 'skey'
    skey = asyncssh.generate_private_key('ssh-rsa')
    skey.write_private_key(str(private_path))
    yield private_path


@pytest.fixture
async def sftp_server(sftp_protocol_factory_server, sock, ssh_host_key) -> SFTPServer:
    server = SFTPServer(protocol_factory=sftp_protocol_factory_server, host=sock[0], port=sock[1],
                        server_host_key=ssh_host_key)
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def sftp_server_quiet(sftp_server) -> SFTPServer:
    sftp_server.quiet = True
    yield sftp_server


@pytest.fixture
async def sftp_server_started(sftp_server) -> SFTPServer:
    await sftp_server.start()
    yield sftp_server


@pytest.fixture
def server_receiver(receiver_args) -> BaseServer:
    return receiver_args[0]


@pytest.fixture
def server_started(receiver_args) -> BaseServer:
    return receiver_args[1]


@pytest.fixture
def server_quiet(receiver_args) -> BaseServer:
    return receiver_args[2]


server_client_params = [
    lazy_fixture((tcp_server_one_way.__name__,)),
    lazy_fixture((tcp_server_two_way.__name__,)),
    pytest.param(
        lazy_fixture((pipe_server_one_way.__name__,)),
        marks=pytest.mark.skipif(
            "not supports_pipe_or_unix_connections()")
    ),
    pytest.param(
        lazy_fixture((pipe_server_one_way.__name__,)),
        marks=pytest.mark.skipif(
            "not supports_pipe_or_unix_connections()")
    ),
    pytest.param(
        lazy_fixture((pipe_server_two_way.__name__,)),
        marks=pytest.mark.skipif(
            "not supports_pipe_or_unix_connections()")
    ),
]
@pytest.fixture(params=server_client_params)
def server_args(request) -> Tuple:
    return request.param


@pytest.fixture(params=[
    lazy_fixture(
        (tcp_server_one_way.__name__, tcp_server_one_way_started.__name__, tcp_server_one_way_quiet.__name__)),
    lazy_fixture(
        (tcp_server_two_way.__name__, tcp_server_two_way_started.__name__, tcp_server_two_way_quiet.__name__)),
    pytest.param(
        lazy_fixture(
        (udp_server_one_way.__name__, udp_server_one_way_started.__name__, udp_server_one_way_quiet.__name__)),
        marks=pytest.mark.skipif(
            "not datagram_supported()")
    ),
    pytest.param(lazy_fixture(
        (udp_server_two_way.__name__, udp_server_two_way_started.__name__, udp_server_two_way_quiet.__name__)),
        marks=pytest.mark.skipif(
            "not datagram_supported()")
    ),
    pytest.param(
        lazy_fixture((pipe_server_one_way.__name__, pipe_server_one_way_started.__name__,
                      pipe_server_one_way_quiet.__name__)),
        marks=pytest.mark.skipif(
            "not supports_pipe_or_unix_connections()")
    ),
    pytest.param(
        lazy_fixture((pipe_server_two_way.__name__, pipe_server_two_way_started.__name__,
                      pipe_server_two_way_quiet.__name__)),
        marks=pytest.mark.skipif(
            "not supports_pipe_or_unix_connections()")
    ),
    lazy_fixture(
        (sftp_server.__name__, sftp_server_started.__name__, sftp_server_quiet.__name__)),
    ])
def receiver_args(request):
    return request.param

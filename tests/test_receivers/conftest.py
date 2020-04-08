from aionetworking import TCPServer, UDPServer, PipeServer
from aionetworking.receivers import BaseServer
from aionetworking.receivers.sftp import SFTPServer
from scripts.generate_ssh_host_key import generate_key_in_path

from tests.test_networking.conftest import *

from typing import Optional


@pytest.fixture
async def tcp_server(protocol_factory_server, server_sock) -> TCPServer:
    yield TCPServer(protocol_factory=protocol_factory_server, host=server_sock[0], port=0)


@pytest.fixture
async def tcp_server_ipv6(protocol_factory_server, server_sock_ipv6) -> TCPServer:
    yield TCPServer(protocol_factory=protocol_factory_server, host=server_sock_ipv6[0], port=0)


@pytest.fixture
def ssl_handshake_timeout() -> Optional[int]:
    return 60


@pytest.fixture
async def tcp_server_ssl(protocol_factory_server, server_sock, server_side_ssl, ssl_handshake_timeout) -> TCPServer:
    yield TCPServer(protocol_factory=protocol_factory_server, host=server_sock[0], port=0, ssl=server_side_ssl,
                    ssl_handshake_timeout=ssl_handshake_timeout)


@pytest.fixture
async def server_quiet(server) -> TCPServer:
    server.quiet = True
    yield server


@pytest.fixture
async def udp_server(protocol_factory_server, server_sock) -> UDPServer:
    server = UDPServer(protocol_factory=protocol_factory_server, host=server_sock[0], port=0)
    yield server


@pytest.fixture
async def pipe_server(protocol_factory_server, pipe_path) -> BaseServer:
    server = PipeServer(protocol_factory=protocol_factory_server, path=pipe_path)
    yield server


@pytest.fixture
async def ssh_host_key(tmp_path) -> Path:
    private_path = Path(tmp_path) / 'skey'
    generate_key_in_path(private_path)
    yield private_path


@pytest.fixture
async def sftp_server(protocol_factory_server, server_sock, ssh_host_key, tmp_path) -> SFTPServer:
    server = SFTPServer(protocol_factory=protocol_factory_server, host=server_sock[0], port=0,
                        server_host_key=ssh_host_key, base_upload_dir=Path(tmp_path) / 'sftp_received')
    yield server


@pytest.fixture
async def sftp_server_quiet(sftp_server) -> SFTPServer:
    sftp_server.quiet = True
    yield sftp_server


@pytest.fixture
async def sftp_server_started(sftp_server) -> SFTPServer:
    await sftp_server.start()
    yield sftp_server


@pytest.fixture
async def server(connection_type, tcp_server, tcp_server_ssl, udp_server, pipe_server, sftp_server) -> BaseServer:
    servers = {
        'tcp': tcp_server,
        'tcpssl': tcp_server_ssl,
        'udp': udp_server,
        'pipe': pipe_server,
        'sftp': sftp_server
    }
    server = servers[connection_type]
    yield server
    if server.is_started():
        await server.close()


@pytest.fixture
async def server_started(server) -> BaseServer:
    await server.start()
    yield server


@pytest.fixture
async def tcp_server_ipv6_started(tcp_server_ipv6) -> TCPServer:
    await tcp_server_ipv6.start()
    yield tcp_server_ipv6


@pytest.fixture
async def tcp_server_ssl_started(tcp_server_ssl) -> TCPServer:
    await tcp_server_ssl.start()
    yield tcp_server_ssl


@pytest.fixture
def patch_systemd(monkeypatch) -> Optional[Tuple]:
    try:
        from systemd import daemon
        from systemd import journal
        monkeypatch.setattr(daemon, 'notify', Mock())
        monkeypatch.setattr(journal, 'send', Mock())
        return daemon, journal
    except ImportError:
        return None

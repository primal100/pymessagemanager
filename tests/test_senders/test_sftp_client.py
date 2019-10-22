import asyncio
import pickle
import pytest
import asyncssh

from lib.receivers.exceptions import ServerException

###Required for skipif in fixture params###
from lib.compatibility import datagram_supported
from lib.utils import supports_pipe_or_unix_connections


class TestClientStartStop:
    @pytest.mark.asyncio
    async def test_00_client_start(self, sftp_server_started, sftp_client, sftp_server_context,
                                   sftp_client_context, connections_manager):
        assert not sftp_client.is_started()
        async with sftp_client as conn:
            assert sftp_client.is_started()
            assert conn.conn
            assert sftp_client.conn
            assert sftp_client.sftp
            assert sftp_client.sftp_conn
            await asyncio.wait_for(conn.wait_context_set(), timeout=1)
            sftp_client_context['client'] = conn.context['client']
            sftp_client_context['sock'] = conn.context['sock']
            sftp_client_context['own'] = conn.context['own']
            assert conn.context == sftp_client_context
            server_peer = conn.get_peername("sftp", conn.context['client'], conn.context['server'])
            server_conn = connections_manager.get(server_peer)
            sftp_server_context['client'] = server_conn.context['client']
            sftp_server_context['peer'] = server_conn.context['peer']
            sftp_server_context['port'] = sftp_client.actual_srcport
            assert server_conn.context == sftp_server_context
        assert sftp_client.is_closing()

    @pytest.mark.asyncio
    async def test_01_client_connect_close(self, sftp_server_started, sftp_client):
        await sftp_client.connect()
        await sftp_client.close()
        assert sftp_client.is_closing()

    @pytest.mark.asyncio
    async def test_02_client_cannot_connect(self, sftp_client):
        with pytest.raises(ConnectionRefusedError):
            await sftp_client.connect()

    @pytest.mark.asyncio
    async def test_03_client_wrong_password(self, sftp_server_started, sftp_client_wrong_password):
        with pytest.raises(asyncssh.misc.PermissionDenied):
            await sftp_client_wrong_password.connect()

    @pytest.mark.asyncio
    async def test_04_client_pickle(self, sftp_client):
        data = pickle.dumps(sftp_client)
        new_client = pickle.loads(data)
        assert new_client == sftp_client

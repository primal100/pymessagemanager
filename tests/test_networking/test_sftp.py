import asyncio
import pytest
import pickle
from pathlib import Path

from lib.compatibility_tests import AsyncMock
from lib.formats.recording import get_recording_from_file
from lib.utils import alist


class TestConnectionShared:

    @pytest.mark.asyncio
    async def test_00_connection_made_lost(self, sftp_protocol, sftp_conn, sftp_adaptor, connections_manager,
                                           sftp_connection_is_stored, sftp_factory):
        assert connections_manager.total == 0
        assert sftp_protocol.logger
        assert sftp_protocol.conn is None
        sftp_protocol.connection_made(sftp_conn)
        await sftp_protocol.wait_connected()
        assert sftp_protocol.is_connected()
        assert sftp_protocol._adaptor.context == sftp_adaptor.context
        assert sftp_protocol._adaptor == sftp_adaptor
        assert sftp_factory.sftp_connection == sftp_protocol
        assert sftp_conn.get_extra_info('sftp_factory') == sftp_factory
        assert sftp_protocol.peer == f"sftp_{sftp_adaptor.context['peer']}"
        assert sftp_protocol.logger is not None
        assert sftp_protocol.conn == sftp_conn
        total_connections = 1 if sftp_connection_is_stored else 0
        assert connections_manager.total == total_connections
        if sftp_connection_is_stored:
            assert connections_manager.get(sftp_protocol.peer) == sftp_protocol
        sftp_conn.close()
        await sftp_protocol.wait_closed()
        assert connections_manager.total == 0


class TestConnectionOneWayServer:
    @pytest.mark.asyncio
    async def test_00_data_received(self, tmp_path, sftp_protocol_one_way_server, json_rpc_login_request_encoded,
                                    json_rpc_logout_request_encoded, json_recording_data, json_codec, json_objects,
                                    sftp_one_way_conn_server):
        sftp_protocol_one_way_server.connection_made(sftp_one_way_conn_server)
        sftp_protocol_one_way_server.data_received(json_rpc_login_request_encoded)
        await asyncio.sleep(1.2)
        sftp_protocol_one_way_server.data_received(json_rpc_logout_request_encoded)
        sftp_one_way_conn_server.close()
        await asyncio.wait_for(sftp_protocol_one_way_server.wait_closed(), timeout=1)
        expected_file = Path(tmp_path/'Data/Encoded/127.0.0.1_JSON.JSON')
        assert expected_file.exists()
        msgs = await alist(json_codec.from_file(expected_file))
        assert msgs == json_objects
        expected_file = Path(tmp_path / 'Recordings/127.0.0.1.recording')
        assert expected_file.exists()
        packets = await alist((get_recording_from_file(expected_file)))
        assert (packets[1].timestamp - packets[0].timestamp).total_seconds() > 1
        packets[0] = packets[0]._replace(timestamp=json_recording_data[0].timestamp)
        packets[1] = packets[1]._replace(timestamp=json_recording_data[1].timestamp)
        assert packets == json_recording_data

    def test_01_is_child(self, sftp_protocol_one_way_server):
        assert sftp_protocol_one_way_server.is_child("SFTP Server 127.0.0.1:8888")
        assert not sftp_protocol_one_way_server.is_child("ABC Server 127.0.0.1:8888")

    @pytest.mark.asyncio
    async def test_02_pickle(self, sftp_protocol_one_way_server):
        data = pickle.dumps(sftp_protocol_one_way_server)
        protocol = pickle.loads(data)
        assert protocol == sftp_protocol_one_way_server


class TestConnectionOneWayClient:

    @pytest.mark.asyncio
    async def test_00_send(self, sftp_protocol_one_way_client, sftp_protocol_factory_one_way_client, sftp_factory_client,
                           sftp_one_way_conn_client, json_rpc_login_request_encoded, patch_datetime_now):
        sftp_protocol_one_way_client.connection_made(sftp_one_way_conn_client)
        sftp_factory_client.realpath = AsyncMock(return_value='.')
        await sftp_protocol_one_way_client.set_sftp(sftp_factory_client)
        sftp_factory_client.realpath.assert_awaited_with('.')
        sftp_factory_client.realpath = AsyncMock(return_value=str(Path('/')))
        task = sftp_protocol_one_way_client.send(json_rpc_login_request_encoded)
        await task
        sftp_factory_client.realpath.assert_awaited_with('.FILE19700101010100101000')
        sftp_factory_client.put.assert_awaited_with(json_rpc_login_request_encoded)

    @pytest.mark.asyncio
    async def test_01_send_data_adaptor_method(self, connection, json_rpc_login_request_encoded, transport, queue,
                                               peer_data):
        connection.connection_made(transport)
        transport.set_protocol(connection)
        connection.send_data(json_rpc_login_request_encoded)
        assert queue.get_nowait() == (peer_data, json_rpc_login_request_encoded)

    def test_02_is_child(self, one_way_client_connection, one_way_client_protocol_name):
        assert one_way_client_connection.is_child(f"{one_way_client_protocol_name.upper()} Client 127.0.0.1:0")
        assert not one_way_client_connection.is_child("ABC Client 127.0.0.1:8888")

    @pytest.mark.asyncio
    async def test_03_pickle(self, one_way_client_connection):
        data = pickle.dumps(one_way_client_connection)
        protocol = pickle.loads(data)
        assert protocol == one_way_client_connection


class TestSFTPProtocolFactories:

    @pytest.mark.asyncio
    async def test_00_connection_lifecycle(self, stream_protocol_factory, stream_connection, stream_transport,
                                           stream_connection_is_stored):
        new_connection = stream_protocol_factory()
        assert stream_protocol_factory.logger == new_connection.logger
        assert new_connection == stream_connection
        assert stream_protocol_factory.is_owner(new_connection)
        new_connection.connection_made(stream_transport)
        new_connection.transport.set_protocol(new_connection)
        if stream_connection_is_stored:
            await asyncio.wait_for(stream_protocol_factory.wait_num_connected(1), timeout=1)
        await asyncio.wait_for(new_connection.wait_connected(), timeout=1)
        new_connection.transport.close()
        await asyncio.wait_for(stream_protocol_factory.close(), timeout=1)
        await asyncio.wait_for(new_connection.wait_closed(), timeout=1)

    @pytest.mark.asyncio
    async def test_01_pickle_protocol_factory(self, stream_protocol_factory):
        data = pickle.dumps(stream_protocol_factory)
        factory = pickle.loads(data)
        assert factory == stream_protocol_factory
        await stream_protocol_factory.close()
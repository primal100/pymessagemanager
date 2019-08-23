import pytest
import asyncio


class TestNetworkConnections:

    @pytest.mark.asyncio
    async def test_00_multiple_connections(self, connections_manager, simple_network_connection):
        parent_name = simple_network_connection.parent_name
        peer = simple_network_connection.peer
        task1 = asyncio.create_task(connections_manager.wait_num_connections(parent_name, 1))
        await simple_network_connection.wait_all_messages_processed()
        await asyncio.sleep(0)
        assert not task1.done()
        connections_manager.add_connection(simple_network_connection)
        assert connections_manager.num_connections(parent_name) == 1
        connection = connections_manager.get(peer)
        assert connection == simple_network_connection
        await asyncio.sleep(0)
        assert task1.done()
        task = asyncio.create_task(connections_manager.wait_num_connections(parent_name, 0))
        await asyncio.sleep(0)
        assert not task.done()
        connections_manager.remove_connection(simple_network_connection)
        assert connections_manager.num_connections(parent_name) == 0
        await asyncio.wait_for(task, timeout=1)
        await connections_manager.wait_num_has_connected(parent_name, 1)

    @pytest.mark.asyncio
    async def test_01_multiple_connections_iter(self, connections_manager, simple_network_connections):
        connections_manager.add_connection(simple_network_connections[0])
        connections_manager.add_connection(simple_network_connections[1])
        connections = list(connections_manager)
        assert connections == simple_network_connections

    def test_02_subscribe_notify_unsubscribe(self, connections_manager, simple_network_connection, queue):
        connections_manager.add_connection(simple_network_connection)
        connections_manager.notify("test", "message sent")
        assert queue.qsize() == 0
        connections_manager.subscribe(simple_network_connection.peer, "test")
        assert connections_manager.is_subscribed(simple_network_connection, "test") is True
        assert connections_manager.peer_is_subscribed(simple_network_connection.peer, "test") is True
        connections_manager.notify("test", "message sent")
        assert queue.qsize() == 1
        assert queue.get_nowait() == "message sent"
        assert queue.qsize() == 0
        connections_manager.unsubscribe(simple_network_connection.peer, "test")
        assert connections_manager.is_subscribed(simple_network_connection, "test") is False
        assert connections_manager.peer_is_subscribed(simple_network_connection.peer, "test") is False
        connections_manager.notify("test", "message sent")
        assert queue.qsize() == 0

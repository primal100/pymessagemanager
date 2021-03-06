import logging
import pytest
import asyncio
import signal
import os
from unittest.mock import call
from aionetworking.compatibility import create_task
from aionetworking.conf.yaml_config import node_from_config_file
from aionetworking.utils import port_from_out


ready_call = call('READY=1')
stopping_call = call('STOPPING=1')
reloading_call = call('RELOADING=1')
restarting_status = call('STATUS=Restarting server')


def status_call(port, host='127.0.0.1'):
    return call(f'STATUS=Serving TCP Server on {host}:{port}')


class TestYamlConfig:
    @pytest.mark.connections('allplus_oneway_all')
    def test_00_yaml_config_node_oneway(self, config_file, expected_object, all_paths, load_all_yaml_tags,
                                        peer_filter, reset_logging, server_pipe_address_load):
        node = node_from_config_file(config_file, paths=all_paths)
        assert node.protocol_factory.action == expected_object.protocol_factory.action
        assert node.protocol_factory == expected_object.protocol_factory
        assert node == expected_object

    @pytest.mark.connections('all_twoway_all')
    def test_01_yaml_config_node_twoway(self, config_file, expected_object, all_paths, load_all_yaml_tags, peer_filter,
                                        reset_logging, server_pipe_address_load):
        node = node_from_config_file(config_file, paths=all_paths)
        assert node.protocol_factory.action == expected_object.protocol_factory.action
        assert node.protocol_factory == expected_object.protocol_factory
        assert node == expected_object

    @pytest.mark.connections('tcp_oneway_server')
    def test_02_yaml_config_node_with_logging(self, config_file, expected_object, all_paths,
                                              load_all_yaml_tags, peer_filter, reset_logging):
        node = node_from_config_file(config_file, paths=all_paths)
        assert node == expected_object
        root_logger = logging.getLogger()
        assert root_logger.getEffectiveLevel() == logging.INFO
        assert root_logger.propagate is True
        assert len(root_logger.handlers) == 2
        receiver_logger = logging.getLogger('receiver')
        assert receiver_logger.getEffectiveLevel() == logging.INFO
        sender_logger = logging.getLogger('sender')
        assert sender_logger.getEffectiveLevel() == logging.INFO
        receiver_connection_logger = logging.getLogger('receiver.connection')
        assert receiver_connection_logger.getEffectiveLevel() == logging.INFO
        sender_connection_logger = logging.getLogger('sender.connection')
        assert sender_connection_logger.getEffectiveLevel() == logging.INFO
        receiver_stats_logger = logging.getLogger('receiver.stats')
        assert receiver_stats_logger.getEffectiveLevel() == logging.INFO
        sender_stats_logger = logging.getLogger('sender.stats')
        assert sender_stats_logger.getEffectiveLevel() == logging.INFO
        receiver_raw_logger = logging.getLogger('receiver.raw_received')
        assert receiver_raw_logger.filters == [peer_filter]
        assert receiver_raw_logger.getEffectiveLevel() == logging.DEBUG
        sender_raw_logger = logging.getLogger('sender.raw_sent')
        assert sender_raw_logger.getEffectiveLevel() == logging.DEBUG
        assert sender_raw_logger.filters == [peer_filter]
        receiver_msg_logger = logging.getLogger('receiver.msg_received')
        assert receiver_msg_logger.getEffectiveLevel() == logging.DEBUG
        sender_msg_logger = logging.getLogger('sender.msg_sent')
        assert sender_msg_logger.getEffectiveLevel() == logging.DEBUG
        loggers = [receiver_logger, sender_logger, receiver_connection_logger, sender_connection_logger,
                   receiver_stats_logger, sender_stats_logger, receiver_raw_logger, sender_raw_logger,
                   receiver_msg_logger, sender_msg_logger]
        for logger in loggers:
            assert logger.propagate is False
            assert len(logger.handlers) == 2

    @pytest.mark.connections('tcp_oneway_server')
    def test_03_yaml_config_node_with_env_var(self, tcp_server_one_way_yaml_with_env_config_path,
                                              tcp_server_one_way_env_ip, all_paths, load_all_yaml_tags,
                                              reset_logging):
        node = node_from_config_file(tcp_server_one_way_yaml_with_env_config_path, paths=all_paths)
        assert node == tcp_server_one_way_env_ip


class TestSignalServerManager:
    @pytest.mark.asyncio
    async def test_00_start_close(self, signal_server_manager, patch_systemd, server_sock, capsys, reset_logging):
        task = create_task(signal_server_manager.serve_until_stopped())
        try:
            await asyncio.wait_for(signal_server_manager.wait_server_started(), timeout=2)
            signal_server_manager.close()
        except asyncio.TimeoutError:
            await asyncio.wait_for(task, timeout=2)
        else:
            await asyncio.wait_for(task, timeout=1)
            await asyncio.wait_for(signal_server_manager.wait_server_stopped(), timeout=1)
            if patch_systemd:
                daemon, journal = patch_systemd
                out = capsys.readouterr().out
                port = port_from_out(out)
                daemon.notify.assert_has_calls([status_call(port), ready_call, stopping_call])
                assert daemon.notify.call_count == 3

    @pytest.mark.asyncio
    async def test_01_check_reload_no_change(self, signal_server_manager_started, reset_logging):
        current_server_id = id(signal_server_manager_started.server)
        signal_server_manager_started.check_reload()
        await asyncio.sleep(1)
        assert signal_server_manager_started.server_is_started()
        assert id(signal_server_manager_started.server) == current_server_id

    @staticmethod
    def modify_config_file(tmp_config_file, second_ip: str = '::1'):
        with open(str(tmp_config_file), "rt") as f:
            data = f.read()
            data = data.replace('127.0.0.1', second_ip)
        with open(str(tmp_config_file), 'wt') as f:
            f.write(data)

    @pytest.mark.asyncio
    async def test_02_check_reload_with_change(self, capsys, patch_systemd, signal_server_manager_started,
                                               tmp_config_file, reset_logging):
        second_ip = '::1'
        out = capsys.readouterr().out
        port1 = port_from_out(out)
        current_server_id = id(signal_server_manager_started.server)
        assert signal_server_manager_started.server.host == '127.0.0.1'
        self.modify_config_file(tmp_config_file, second_ip=second_ip)
        signal_server_manager_started.check_reload()
        await asyncio.wait_for(signal_server_manager_started.wait_server_stopped(), timeout=1)
        await asyncio.wait_for(signal_server_manager_started.wait_server_started(), timeout=2)
        assert signal_server_manager_started.server.host == second_ip
        assert id(signal_server_manager_started.server) != current_server_id
        if patch_systemd:
            daemon, journal = patch_systemd
            out = capsys.readouterr().out
            port2 = port_from_out(out)
            daemon.notify.assert_has_calls(
                [status_call(port1), ready_call, reloading_call, restarting_status,
                 status_call(port2, host=second_ip), ready_call])
            assert daemon.notify.call_count == 6

    @pytest.mark.asyncio
    async def test_03_check_reload_file_deleted(self, patch_systemd, signal_server_manager, tmp_config_file, capsys,
                                                reset_logging):
        task = create_task(signal_server_manager.serve_until_stopped())
        await signal_server_manager.wait_server_started()
        tmp_config_file.unlink()
        signal_server_manager.check_reload()
        assert signal_server_manager._stop_event.is_set()
        assert not signal_server_manager._restart_event.is_set()
        await asyncio.wait_for(signal_server_manager.wait_server_stopped(), timeout=2)
        await asyncio.wait_for(task, timeout=1)
        if patch_systemd:
            out = capsys.readouterr().out
            port = port_from_out(out)
            daemon, journal = patch_systemd
            daemon.notify.assert_has_calls(
                [status_call(port), ready_call, stopping_call])
            assert daemon.notify.call_count == 3

    @staticmethod
    async def send_signal(server_manager, signal_num):
        await server_manager.wait_server_started()
        os.kill(os.getpid(), signal_num)

    @pytest.mark.asyncio
    @pytest.mark.parametrize('signal_num', [
        pytest.param(signal.SIGINT, marks=pytest.mark.skipif(os.name == 'nt', reason='POSIX only')),
        pytest.param(signal.SIGTERM, marks=pytest.mark.skipif(os.name == 'nt', reason='POSIX only'))
    ])
    async def test_04_close_signal(self, patch_systemd, signal_server_manager, signal_num, capsys, reset_logging):
        task = create_task(self.send_signal(signal_server_manager, signal_num))
        await signal_server_manager.serve_until_stopped()
        await task
        await asyncio.wait_for(signal_server_manager.server.wait_stopped(), timeout=10)
        if patch_systemd:
            out = capsys.readouterr().out
            port = port_from_out(out)
            daemon, journal = patch_systemd
            daemon.notify.assert_has_calls(
                [status_call(port), ready_call, stopping_call])
            assert daemon.notify.call_count == 3

    @pytest.mark.asyncio
    @pytest.mark.parametrize('signal_num', [
        pytest.param(getattr(signal, 'SIGUSR1', None), marks=pytest.mark.skipif(os.name == 'nt', reason='POSIX only')),
    ])
    async def test_05_reload_no_change_on_signal(self, signal_server_manager_started, signal_num, reset_logging):
        current_server_id = id(signal_server_manager_started.server)
        await self.send_signal(signal_server_manager_started, signal_num)
        await asyncio.sleep(1)
        assert signal_server_manager_started.server_is_started()
        assert id(signal_server_manager_started.server) == current_server_id

    @pytest.mark.asyncio
    @pytest.mark.parametrize('signal_num', [
        pytest.param(getattr(signal, 'SIGUSR1', None), marks=pytest.mark.skipif(os.name == 'nt', reason='POSIX only')),
    ])
    async def test_06_reload_change_on_signal(self, capsys, patch_systemd, signal_server_manager_started, signal_num,
                                              tmp_config_file, server_port, reset_logging):
        second_id = '::1'
        out = capsys.readouterr().out
        port1 = port_from_out(out)
        current_server_id = id(signal_server_manager_started.server)
        assert signal_server_manager_started.server.host == '127.0.0.1'
        self.modify_config_file(tmp_config_file)
        await self.send_signal(signal_server_manager_started, signal_num)
        await asyncio.wait_for(signal_server_manager_started.wait_server_stopped(), timeout=1)
        await asyncio.wait_for(signal_server_manager_started.wait_server_started(), timeout=2)
        assert signal_server_manager_started.server.host == second_id
        assert id(signal_server_manager_started.server) != current_server_id
        out = capsys.readouterr().out
        port2 = port_from_out(out)
        if patch_systemd:
            daemon, journal = patch_systemd
            daemon.notify.assert_has_calls(
                [status_call(port1), ready_call, reloading_call, restarting_status,
                 status_call(port2, host=second_id), ready_call])
            assert daemon.notify.call_count == 6

    @pytest.mark.asyncio
    @pytest.mark.parametrize('signal_num', [
        pytest.param(getattr(signal, 'SIGUSR1', None), marks=pytest.mark.skipif(os.name == 'nt', reason='POSIX only')),
    ])
    async def test_07_reload_no_file_signal(self, patch_systemd, signal_server_manager, signal_num,
                                            tmp_config_file, capsys, reset_logging):
        task = create_task(signal_server_manager.serve_until_stopped())
        await signal_server_manager.wait_server_started()
        tmp_config_file.unlink()
        await self.send_signal(signal_server_manager, signal_num)
        await signal_server_manager._stop_event.wait()
        assert not signal_server_manager._restart_event.is_set()
        await asyncio.wait_for(signal_server_manager.wait_server_stopped(), timeout=2)
        await asyncio.wait_for(task, timeout=1)
        if patch_systemd:
            out = capsys.readouterr().out
            port = port_from_out(out)
            daemon, journal = patch_systemd
            daemon.notify.assert_has_calls(
                [status_call(port), ready_call, stopping_call])
            assert daemon.notify.call_count == 3

import logging


class TestStatsTracker:
    def test_00_on_buffer_received_msg_processed(self, stats_tracker, asn_buffer):
        assert not stats_tracker.msgs.first_received
        assert not stats_tracker.msgs.last_received
        assert stats_tracker.received == 0
        stats_tracker.on_buffer_received(asn_buffer)
        assert stats_tracker.msgs.first_received
        assert stats_tracker.msgs.last_received
        assert stats_tracker.msgs.received == 1
        assert stats_tracker.received == 326
        assert stats_tracker.processed == 0
        stats_tracker.on_msg_processed(326)
        assert stats_tracker.msgs.last_processed >= stats_tracker.msgs.last_received
        assert stats_tracker.msgs.processed == 1
        assert stats_tracker.processed == 326
        assert stats_tracker.processing_rate.bytes == 326.0
        assert stats_tracker.receive_rate.bytes == 326.0
        assert int(stats_tracker.interval) <= 1
        assert stats_tracker.average_buffer.bytes == 326.0

    def test_01_on_msg_sent(self, stats_tracker, asn_one_encoded):
        assert stats_tracker.msgs.sent == 0
        stats_tracker.on_msg_sent(asn_one_encoded)
        assert stats_tracker.msgs.sent == 1
        assert stats_tracker.msgs.first_sent
        assert stats_tracker.sent == 73
        assert stats_tracker.average_sent == 73.0

    def test_02_end_interval(self, stats_tracker, asn_one_encoded):
        assert not stats_tracker.end
        stats_tracker.end_interval()
        assert stats_tracker.end

    def test_03_iterkeys(self, stats_tracker):
        d = {}
        for key in stats_tracker:
            d[key] = stats_tracker[key]
        assert list(d) == ['start', 'end', 'msgs', 'sent', 'received', 'processed',
                           'processing_rate', 'receive_rate', 'interval', 'average_buffer', 'average_sent']


class TestStatsLogger:
    def test_00_process(self, stats_logger):
        msg, kwargs = stats_logger.process("abc", {})
        assert msg == 'abc'
        keys = list(kwargs['extra'].keys())
        assert sorted(keys) == sorted(
            ['taskname', 'start', 'end', 'msgs', 'sent', 'received', 'processed', 'processing_rate',
             'receive_rate', 'interval', 'average_buffer', 'average_sent', 'protocol_name', 'host',
             'port', 'peer', 'sock', 'alias'])

    def test_01_reset(self, stats_logger, asn_buffer):
        stats_logger.on_buffer_received(asn_buffer)
        stats_logger.on_msg_processed(326)
        assert stats_logger.received == 326
        assert stats_logger.processed == 326
        stats_logger.reset()
        assert stats_logger.received == 0
        assert stats_logger.processed == 0

    def test_02_log_info(self, stats_logger, asn_buffer, stats_formatter, caplog):
        caplog.set_level(logging.INFO, logger=stats_logger.logger_name)
        caplog.handler.setFormatter(stats_formatter)
        stats_logger.on_buffer_received(asn_buffer)
        stats_logger.on_msg_processed(326)
        assert stats_logger.received == 326
        assert stats_logger.processed == 326
        stats_logger.info('INTERVAL')
        assert caplog.text == "127.0.0.1 INTERVAL 1 0.32KB 0.32KB 0.32KB/s 0.32KB 1\n"

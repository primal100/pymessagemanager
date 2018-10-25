import logging
import binascii
import asyncio
from pathlib import Path
from typing import Sequence, AnyStr, Type
from lib import utils
from lib.protocols.base import BaseProtocol

import definitions

logger = logging.getLogger(definitions.LOGGER_NAME)


class BaseSender:
    sender_type: str
    configurable = {
        'interval': float
    }

    @classmethod
    def from_config(cls, msg_protocol:Type[BaseProtocol], queue=None, **kwargs):
        config = definitions.CONFIG.section_as_dict('Sender', **cls.configurable)
        logger.debug('Found configuration for', cls.sender_type, ':', config)
        config.update(kwargs)
        return cls(msg_protocol, queue=queue, **kwargs)

    def __init__(self, msg_protocol:Type[BaseProtocol], queue=None, interval:float=0):
        self.msg_protocol = msg_protocol
        self.queue = queue
        self.interval = interval
        if self.queue:
            self.process_queue_task = asyncio.get_event_loop().create_task(self.process_queue_later())
        else:
            self.process_queue_task = None

    @property
    def source(self):
        raise NotImplementedError

    async def process_queue_later(self):
        if self.interval:
            await asyncio.sleep(self.interval)
        try:
            await self.process_queue()
        finally:
            await self.process_queue_later()

    async def process_queue(self):
        msgs = []
        try:
            while not self.queue.empty():
                msgs.append(self.queue.get_nowait())
                logger.debug('Took item from queue')
            await self.send_msgs(msgs)
        finally:
            for msg in msgs:
                logger.debug("Setting task done on queue")
                self.queue.task_done()

    async def close(self):
        if self.queue:
            logger.debug('Closing message queue')
            try:
                timeout = self.interval + 1
                logger.info('Waiting', timeout, 'seconds for queue to empty')
                await asyncio.wait_for(self.queue.join(), timeout=timeout)
            except asyncio.TimeoutError:
                logger.error('Queue did not empty in time. Cancelling task with messages in queue.')
            self.process_queue_task.cancel()
            logger.debug('Message queue closed')

    @property
    def dst(self):
        raise NotImplementedError

    async def __aenter__(self):
        await self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        await self.stop()

    async def start(self):
        pass

    async def stop(self):
        pass

    async def send_data(self, msg_encoded:bytes):
        raise NotImplementedError

    async def send_msg(self, msg_encoded:bytes):
        logger.debug("Sending message to", self.dst)
        logger.debug(msg_encoded)
        await self.send_data(msg_encoded)
        logger.debug('Message sent')

    async def send_hex(self, hex_msg:AnyStr):
        await self.send_msg(binascii.unhexlify(hex_msg))

    async def send_msgs(self, msgs:Sequence[bytes]):
        for msg in msgs:
            await self.send_msg(msg)
            await asyncio.sleep(0.001)

    async def send_hex_msgs(self, hex_msgs:Sequence[AnyStr]):
        await self.send_msgs([binascii.unhexlify(hex_msg) for hex_msg in hex_msgs])

    async def encode_and_send_msgs(self, decoded_msgs):
        for decoded_msg in decoded_msgs:
            await self.encode_and_send_msg(decoded_msg)

    async def encode_and_send_msg(self, msg_decoded):
        msg = self.msg_protocol(self.source, decoded=msg_decoded)
        await self.send_msg(msg.encoded)

    async def play_recording(self, file_path:Path, immediate:bool=False):
        with file_path.open('rb') as f:
            content = f.read()
        packets = utils.unpack_recorded_packets(content)
        if immediate:
            await self.send_msgs([p[2] for p in packets])
        for seconds, sender, data in packets:
            if not immediate and seconds >= 1:
                await asyncio.sleep(seconds)
            await self.send_msg(data)


class BaseNetworkClient(BaseSender):
    sender_type = "Network client"
    sock_name: str

    configurable = BaseSender.configurable.copy()
    configurable.update({
        'host': str,
        'port': int,
        'ssl': bool,
        'src_ip': str,
        'src_port': int
    })

    def __init__(self, protocol, queue=None, host:str='127.0.0.1', port:int = 4000,
                 ssl=False, src_ip:str='', src_port:int=0, **kwargs):
        super(BaseNetworkClient, self).__init__(protocol, queue=queue, **kwargs)
        self.host = host
        self.port = port
        self.localaddr = (src_ip, src_port) if src_ip else None
        self.ssl = ssl

    @property
    def source(self) -> str:
        return self.sock_name[0]

    @property
    def dst(self) -> str:
        return "%s:%s" % (self.host, self.port)

    async def open_connection(self):
        raise NotImplementedError

    async def close_connection(self):
        raise NotImplementedError

    async def send_data(self, encoded_data:bytes):
        raise NotImplementedError

    async def start(self):
        logger.info("Opening", self.sender_type, 'connection to', self.dst)
        await self.open_connection()

    async def stop(self):
        logger.info("Closing", self.sender_type, 'connection to', self.dst)
        await self.close_connection()

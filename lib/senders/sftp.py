import asyncssh
from dataclasses import dataclass, InitVar
from pathlib import Path

from lib.networking.sftp import SFTPClientProtocolFactory, SFTPClientProtocol
from .clients import BaseNetworkClient

from typing import Tuple


@dataclass
class SFTPClient(BaseNetworkClient):
    name = "SFTP Client"
    protocol_factory = SFTPClientProtocolFactory
    sftp_log_level: InitVar[int] = 1
    known_hosts: Path = None
    username: str = None
    password: str = None
    client_keys: Path = None
    passphrase: str = None
    client_version: Tuple = ()
    sftp_client = None
    sftp = None
    cwd = None

    def __post_init__(self, sftp_log_level) -> None:
        super().__post_init__()
        asyncssh.logging.set_debug_level(sftp_log_level)

    async def _open_connection(self) -> SFTPClientProtocol:
        self.sftp_conn, self.conn = await asyncssh.create_connection(
            self.protocol_factory, self.host, self.port, local_addr=self.local_addr, known_hosts=self.known_hosts,
            username=self.username, password=self.password, client_keys=self.client_keys, passphrase=self.passphrase,
            client_version = self.client_version)
        self.sftp = await self.sftp_conn.start_sftp_client()
        await self.conn.set_sftp(self.sftp)
        return self.conn

    def is_closing(self) -> bool:
        return self._status.is_stopping_or_stopped()

    async def _close_connection(self) -> None:
        self.sftp.exit()
        self.sftp_conn.close()
        await self.conn.wait_closed()

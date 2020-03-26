from __future__ import annotations
import pytest
from dataclasses import dataclass
import datetime
from pathlib import Path
from aionetworking import JSONObject, JSONCodec
from aionetworking.compatibility import default_server_port, default_client_port
from aionetworking.formats import BufferCodec, BufferObject, recorded_packet
from aionetworking.utils import hostname_or_ip
from aionetworking.types.formats import MessageObjectType
from aionetworking.types.networking import AFINETContext

from typing import Dict, Any, List, NamedTuple, Tuple, Type


@pytest.fixture
def timestamp() -> datetime.datetime:
    return datetime.datetime(2019, 1, 1, 1, 1)


@pytest.fixture
def server_port() -> int:
    return default_server_port()


@pytest.fixture
def client_port() -> int:
    return default_client_port()


@pytest.fixture
def server_sock(server_port) -> Tuple[str, int]:
    return '127.0.0.1', server_port


@pytest.fixture
def client_sock(client_port) -> Tuple[str, int]:
    return '127.0.0.1', client_port


@pytest.fixture
def server_sock_str(server_sock) -> str:
    return f'{server_sock[0]}:{server_sock[1]}'


@pytest.fixture
def server_hostname(server_sock) -> str:
    return 'localhost'


@pytest.fixture
def client_hostname(client_sock) -> str:
    return 'localhost'


@pytest.fixture
def server_hostname_ip6(server_sock) -> str:
    return 'ip6-localhost'


@pytest.fixture
def client_hostname_ip6(client_sock) -> str:
    return 'ip6-localhost'


@pytest.fixture
def client_sock_str(client_sock) -> str:
    return f'{client_sock[0]}:{client_sock[1]}'


@pytest.fixture
def server_sock_ipv6(server_port) -> Tuple[str, int, int, int]:
    return '::1', server_port, 0, 0


@pytest.fixture
def client_sock_ipv6() -> Tuple[str, int, int, int]:
    return '::1', 60000, 0, 0


@pytest.fixture
def client_sock_ipv6str(client_sock_ipv6) -> str:
    return f'{client_sock_ipv6[0]}:{client_sock_ipv6[1]}'


@pytest.fixture
def context(client_sock, client_sock_str, client_hostname, server_sock, server_sock_str) -> AFINETContext:
    context: AFINETContext = {
        'protocol_name': 'TCP Server', 'host': client_hostname, 'port': client_sock[1], 'peer': client_sock_str,
        'alias': f'{client_hostname}({client_sock_str})', 'server': server_sock_str, 'client': client_sock_str,
        'own': server_sock_str, 'address': client_sock[0]
    }
    return context


@pytest.fixture
def json_codec(context) -> JSONCodec:
    return JSONCodec(JSONObject, context=context)


@pytest.fixture
def user1() -> List[str, str]:
    return ['user1', 'password']


@pytest.fixture
def json_rpc_login_request(user1) -> Dict[str, Any]:
    return {'jsonrpc': "2.0", 'id': 1, 'method': 'login', 'params': user1}


@pytest.fixture
async def json_rpc_logout_request_object(json_rpc_logout_request, json_codec, timestamp) -> JSONObject:
    return await json_codec.encode_obj(json_rpc_logout_request, received_timestamp=timestamp)


@pytest.fixture
async def json_rpc_login_request_object(json_rpc_login_request, json_codec, timestamp) -> JSONObject:
    return await json_codec.encode_obj(json_rpc_login_request, received_timestamp=timestamp)


@pytest.fixture
def json_rpc_login_request_encoded() -> bytes:
    return b'{"jsonrpc": "2.0", "id": 1, "method": "login", "params": ["user1", "password"]}'


@pytest.fixture
def json_rpc_logout_request() -> Dict[str, Any]:
    return {'jsonrpc': "2.0", 'id': 2, 'method': 'logout'}


@pytest.fixture
def json_rpc_logout_request_encoded(user1) -> bytes:
    return b'{"jsonrpc": "2.0", "id": 2, "method": "logout"}'


@pytest.fixture
def json_buffer() -> bytes:
    return b'{"jsonrpc": "2.0", "id": 1, "method": "login", "params": ["user1", "password"]}{"jsonrpc": "2.0", "id": 2, "method": "logout"}'


@pytest.fixture
def json_encoded_multi(json_rpc_login_request_encoded, json_rpc_logout_request_encoded) -> List[bytes]:
    return [
        json_rpc_login_request_encoded,
        json_rpc_logout_request_encoded
    ]


@pytest.fixture
def json_decoded_multi(json_rpc_login_request, json_rpc_logout_request) -> List[dict]:
    return [
        json_rpc_login_request,
        json_rpc_logout_request
    ]


@pytest.fixture
def decoded_result(json_encoded_multi, json_decoded_multi) -> List[Tuple[bytes, Dict[str, Any]]]:
    return [(json_encoded_multi[0], json_decoded_multi[0]), (json_encoded_multi[1], json_decoded_multi[1])]


@pytest.fixture
def file_containing_multi_json(tmpdir, json_buffer) -> Path:
    p = Path(tmpdir.mkdir("encoded").join("json"))
    p.write_bytes(json_buffer)
    return p


@pytest.fixture
def json_object(json_rpc_login_request_encoded, json_rpc_login_request, context, timestamp) -> MessageObjectType:
    return JSONObject(json_rpc_login_request_encoded, json_rpc_login_request, context=context, received_timestamp=timestamp)


@pytest.fixture
def json_objects(json_encoded_multi, json_decoded_multi, timestamp, context) -> List[MessageObjectType]:
    return [JSONObject(encoded, json_decoded_multi[i], context=context,
            received_timestamp=timestamp) for i, encoded in
            enumerate(json_encoded_multi)]


@pytest.fixture
def json_recording_data(json_rpc_login_request_encoded, json_rpc_logout_request_encoded, timestamp) -> List[
                        NamedTuple]:
    return [recorded_packet(sent_by_server=False, timestamp=timestamp, sender='127.0.0.1',
                            data=json_rpc_login_request_encoded),
            recorded_packet(sent_by_server=False, timestamp=timestamp, sender='127.0.0.1',
                            data=json_rpc_logout_request_encoded)]


@pytest.fixture
def buffer_codec(context) -> BufferCodec:
    return BufferCodec(BufferObject, context=context)


@pytest.fixture
def json_encoded_multi(json_rpc_login_request_encoded, json_rpc_logout_request_encoded) -> List[bytes]:
    return [
        json_rpc_login_request_encoded,
        json_rpc_logout_request_encoded
    ]


@dataclass
class JSONCodecWithKwargs(JSONCodec):
    test_param: str = None


class JSONObjectWithCodecKwargs(JSONObject):
    codec_cls = JSONCodecWithKwargs


@pytest.fixture
def json_codec_with_kwargs() -> JSONCodecWithKwargs:
    return JSONCodecWithKwargs(JSONObjectWithCodecKwargs, test_param='abc')


@pytest.fixture
def json_object_with_codec_kwargs() -> Type[JSONObjectWithCodecKwargs]:
    return JSONObjectWithCodecKwargs

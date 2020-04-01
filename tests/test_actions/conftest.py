from aionetworking import FileStorage, BufferedFileStorage
from aionetworking.actions import ManagedFile
from aionetworking.actions import EchoAction
from aionetworking.formats import get_recording_from_file
from aionetworking.utils import alist
from tests.test_formats.conftest import *
from tests.test_actions.actions import file_storage_actions, duplex_actions, get_recording_buffered_file_storage
import pytest

from typing import List, Dict, Optional, Union, Coroutine


@pytest.fixture
async def managed_file(tmp_path) -> ManagedFile:
    path = tmp_path/'managed_file1'
    f = ManagedFile.open(path, mode='ab', buffering=0)
    yield f
    if not f.is_closing():
        await f.close()


@pytest.fixture
def data_dir(tmp_path) -> Path:
    return tmp_path / 'data'


@pytest.fixture
def recordings_dir(tmp_path) -> Path:
    return tmp_path / 'recordings'


@pytest.fixture
def sender(connection_type, pipe_path, context) -> str:
    return context['address']


@pytest.fixture
def expected_files_buffered_storage(data_dir, json_objects, sender) -> Dict[Path, List[MessageObjectType]]:
    return {
        Path(data_dir / f'{sender}.JSON'): json_objects,
    }


async def _assert_file_storage_ok(expected_action_files, json_codec):
    for path, objects in expected_action_files.items():
            assert path.exists()
            items = await alist(json_codec.from_file(path))
            assert sorted(items, key=str) == sorted(objects, key=str)


@pytest.fixture()
def assert_file_storage_ok(expected_action_files, json_codec) -> Coroutine:
    return _assert_file_storage_ok(expected_action_files, json_codec)


@pytest.fixture()
def assert_buffered_file_storage_ok(expected_files_buffered_storage, json_codec) -> Coroutine:
    return _assert_file_storage_ok(expected_files_buffered_storage, json_codec)


@pytest.fixture
def assert_recordings_ok(recordings_dir, recording_data, sender) -> Coroutine:
    async def coro():
        expected_file = recordings_dir / f'{sender}.recording'
        assert expected_file.exists()
        packets = await alist(get_recording_from_file(expected_file))
        assert packets == recording_data
    return coro()


@pytest.fixture
def expected_action_files(file_storage, data_dir, expected_files_buffered_storage, json_objects,
                          sender) -> Dict[Path, List[MessageObjectType]]:
    if isinstance(file_storage, FileStorage):
        return {
            Path(data_dir / f'{sender}_1.JSON'): [json_objects[0]],
            Path(data_dir / f'{sender}_2.JSON'): [json_objects[1]]
        }
    return expected_files_buffered_storage


@pytest.fixture(params=[
    'FileStorageAction',
    'BufferedFileStorageAction'
])
async def file_storage(request, data_dir) -> Union[FileStorage, BufferedFileStorage]:
    action_callable = file_storage_actions[request.param]
    action = action_callable(data_dir)
    yield action
    if not action.is_closing():
        await action.close()


@pytest.fixture
async def action(duplex_type, endpoint, data_dir) -> Optional[Union[FileStorage, BufferedFileStorage]]:
    if endpoint == 'server':
        action_callable = duplex_actions[duplex_type]
        action = action_callable(data_dir)
        yield action
        if not action.is_closing():
            await action.close()
    else:
        yield None


@pytest.fixture
async def recording_file_storage(recordings_dir) -> Union[BufferedFileStorage]:
    action = get_recording_buffered_file_storage(recordings_dir)
    yield action
    if not action.is_closing():
        await action.close()


@pytest.fixture
async def buffer_objects(json_encoded_multi, buffer_codec, timestamp):
    yield [await buffer_codec.encode_obj(decoded, system_timestamp=timestamp) for decoded in json_encoded_multi]


@pytest.fixture
def echo() -> dict:
    return {'id': 1, 'method': 'echo'}


@pytest.fixture
def echo_response() -> dict:
    return {'id': 1, 'result': 'echo'}


@pytest.fixture
def echo_notification_request() -> dict:
    return {'method': 'send_notification'}


@pytest.fixture
def echo_notification() -> dict:
    return {'result': 'notification'}


@pytest.fixture
def echo_exception_request() -> dict:
    return {'id': 1, 'method': 'echo_typo'}


@pytest.fixture
def echo_exception_response() -> dict:
    return {'id': 1, 'error': 'InvalidRequestError'}


@pytest.fixture
def echo_encoded_multi(echo, echo_notification_request) -> List[Dict]:
    return [echo, echo_notification_request]


@pytest.fixture
def echo_encoded() -> bytes:
    return b'{"id": 1, "method": "echo"}'


@pytest.fixture
def echo_request_object(echo_encoded, echo) -> JSONObject:
    return JSONObject(echo_encoded, echo)


@pytest.fixture
def echo_response_encoded() -> bytes:
    return b'{"id": 1, "result": "echo"}'


@pytest.fixture
def echo_response_object(echo_response_encoded, echo_response) -> JSONObject:
    return JSONObject(echo_response_encoded, echo_response)


@pytest.fixture
def echo_notification_client_encoded() -> bytes:
    return b'{"method": "send_notification"}'


@pytest.fixture
def echo_notification_request_object(echo_notification_client_encoded, echo_notification_request, context) -> JSONObject:
    return JSONObject(echo_notification_client_encoded, echo_notification_request, context=context)


@pytest.fixture
def echo_notification_server_encoded() -> bytes:
    return b'{"result": "notification"}'


@pytest.fixture
def echo_notification_object(echo_notification_server_encoded, echo_notification) -> JSONObject:
    return JSONObject(echo_notification_server_encoded, echo_notification)


@pytest.fixture
def echo_exception_request_encoded() -> bytes:
    return b'{"id": 1, "method": "echo_typo"}'


@pytest.fixture
def echo_exception_request_object(echo_exception_request_encoded, echo_exception_request) -> JSONObject:
    return JSONObject(echo_exception_request_encoded, echo_exception_request)


@pytest.fixture
def echo_exception_response_encoded() -> bytes:
    return b'{"id": 1, "error": "InvalidRequestError"}'


@pytest.fixture
def echo_exception_response_object(echo_exception_response_encoded, echo_exception_response) -> JSONObject:
    return JSONObject(echo_exception_response_encoded, echo_exception_response)


@pytest.fixture
def echo_request_invalid_json(echo) -> bytes:
    return b'{"id": 1, "method": echo"}'


@pytest.fixture
def echo_decode_error_response(echo_request_invalid_json) -> Dict:
    return {'error': 'JSON was invalid'}


@pytest.fixture
async def echo_action(tmp_path) -> FileStorage:
    action = EchoAction()
    yield action


class JSONObjectWithKeepAlive(JSONObject):
    @property
    def store(self) -> bool:
        return self.decoded['method'] != 'keepalive'

    @property
    def response(self) -> Optional[Dict[str, Any]]:
        if self.decoded['method'] == 'keepalive':
            return {'result': 'keepalive-response'}
        return None


@pytest.fixture
def keep_alive_request_decoded() -> Dict[str, str]:
    return {'method': 'keepalive'}


@pytest.fixture
def keep_alive_request_encoded() -> bytes:
    return b'{"method": "keepalive"}'


@pytest.fixture
def keepalive_object(keep_alive_request_encoded, keep_alive_request_decoded, context, timestamp) -> JSONObjectWithKeepAlive:
    return JSONObjectWithKeepAlive(keep_alive_request_encoded, keep_alive_request_decoded, context=context,
                                   system_timestamp=timestamp)


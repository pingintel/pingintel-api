from unittest import mock

from pingintel_api import SOVFixerAPIClient


def _client():
    return SOVFixerAPIClient(api_url="https://api.example.test", auth_token="token")


def _posted_data(post):
    return post.call_args.kwargs["data"]


def test_create_submission_sends_is_test_only_when_set():
    client = _client()
    with mock.patch.object(client, "post") as post:
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"id": 1}
        client.create_submission(is_test=True)
        assert _posted_data(post)["is_test"] == "true"
        client.create_submission()
        assert "is_test" not in _posted_data(post)


def test_fix_sov_async_start_sends_is_test_only_when_set(tmp_path):
    sov = tmp_path / "sov.xlsx"
    sov.write_bytes(b"x")
    client = _client()
    with mock.patch.object(client, "post") as post:
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"id": "abc", "message": "ok"}
        client.fix_sov_async_start(sov, is_test=True)
        assert _posted_data(post)["is_test"] == "true"
        client.fix_sov_async_start(sov)
        assert "is_test" not in _posted_data(post)

import unittest
from unittest import mock

from pingintel_api import SOVFixerAPIClient

API = "https://api.example.test"
SOVID = "s-no-wf-abc123"
R001_URL = f"{API}/api/v1/sov/{SOVID}-r001/output/20261119000420503311-My%20SOV-Westfield.xlsm"
R0_URL = f"{API}/api/v1/sov/{SOVID}/output/My%20SOV-Westfield.xlsm"


def response(status=200, json=None, content=b""):
    r = mock.Mock(ok=200 <= status < 300, status_code=status, content=content)
    r.json.return_value = json
    r.iter_content.return_value = [content]
    return r


def status_response(*outputs):
    return response(json={"request": {"status": "COMPLETE"}, "result": {"outputs": list(outputs)}})


class FetchSOVOutputTests(unittest.TestCase):
    def setUp(self):
        self.client = SOVFixerAPIClient(api_url=API, auth_token="token")

    def fetch(self, filename, status, **kwargs):
        with mock.patch.object(self.client, "get", side_effect=[status, response(content=b"file")]) as get:
            content = self.client.fetch_sov_output(SOVID, filename, **kwargs)
        self.assertEqual(content, b"file")
        self.assertEqual(get.call_args_list[0].args[0], f"{API}/api/v1/sov/{SOVID}")
        return get.call_args_list[1].args[0]

    def test_downloads_the_url_of_the_output_with_that_filename(self):
        status = status_response({"filename": "My SOV-Westfield.xlsm", "url": R001_URL})
        self.assertEqual(self.fetch("My SOV-Westfield.xlsm", status), R001_URL)

    def test_matches_the_last_path_segment_of_the_url(self):
        status = status_response({"filename": "My SOV-Westfield.xlsm", "url": R001_URL})
        self.assertEqual(self.fetch("20261119000420503311-My SOV-Westfield.xlsm", status), R001_URL)

    def test_relative_urls_get_the_api_url(self):
        status = status_response({"filename": "My SOV-Westfield.xlsm", "url": R001_URL.removeprefix(API)})
        self.assertEqual(self.fetch("My SOV-Westfield.xlsm", status), R001_URL)

    def test_falls_back_to_the_constructed_address_when_no_output_matches(self):
        status = status_response({"filename": "other.json", "url": f"{API}/api/v1/sov/{SOVID}/output/other.json"})
        self.assertEqual(
            self.fetch("My SOV-Westfield.xlsm", status), f"{API}/api/v1/sov/{SOVID}/output/My SOV-Westfield.xlsm"
        )

    def test_falls_back_to_the_constructed_address_when_the_status_lookup_fails(self):
        self.assertEqual(
            self.fetch("My SOV-Westfield.xlsm", response(status=404)),
            f"{API}/api/v1/sov/{SOVID}/output/My SOV-Westfield.xlsm",
        )

    def test_writes_output_path(self):
        status = status_response({"filename": "My SOV-Westfield.xlsm", "url": R0_URL})
        with mock.patch("builtins.open", mock.mock_open()) as opened:
            self.assertEqual(self.fetch("My SOV-Westfield.xlsm", status, output_path="out.xlsm"), R0_URL)
        opened.assert_called_once_with("out.xlsm", "wb")
        opened().write.assert_called_once_with(b"file")


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch, MagicMock
import urllib.parse

import redis
import tornado.testing

import main


class BaseTornadoTest(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        app = main.make_app()
        app.settings["autoreload"] = False
        return app



class TestHospitalHandlerGet(BaseTornadoTest):

    @patch("main.r")
    def test_get_ok_renders(self, r_mock):
        r_mock.get.return_value = b"2"  # значит i=0..1

        r_mock.hgetall.side_effect = [
            {
                b"name": b"City Hospital",
                b"address": b"123 St",
                b"phone": b"1234567890",
                b"beds_number": b"50",
            },
            {},  # второй пустой, не добавится
        ]

        resp = self.fetch("/hospital")
        self.assertEqual(resp.code, 200)


        r_mock.get.assert_called_with("hospital:autoID")
        r_mock.hgetall.assert_any_call("hospital:0")
        r_mock.hgetall.assert_any_call("hospital:1")

    @patch("main.r")
    def test_get_redis_connection_error(self, r_mock):
        r_mock.get.side_effect = redis.exceptions.ConnectionError()

        resp = self.fetch("/hospital")
        self.assertEqual(resp.code, 400)
        self.assertIn(b"Redis connection refused", resp.body)


class TestHospitalHandlerPost(BaseTornadoTest):

    @patch("main.r")
    def test_post_validation_error(self, r_mock):
        # name пустой => 400 и сообщение
        body = urllib.parse.urlencode({
            "name": "",
            "address": "Addr",
            "beds_number": "10",
            "phone": "123",
        })
        resp = self.fetch("/hospital", method="POST", body=body)
        self.assertEqual(resp.code, 400)
        self.assertIn(b"Hospital name and address required", resp.body)

        # Redis не должен вызываться
        r_mock.get.assert_not_called()

    @patch("main.r")
    def test_post_ok(self, r_mock):
        r_mock.get.return_value = b"1"
        r_mock.hset.return_value = 1  # 4 раза по 1 => a == 4
        r_mock.incr.return_value = 2

        body = urllib.parse.urlencode({
            "name": "New Hospital",
            "address": "456 St",
            "beds_number": "100",
            "phone": "9876543210",
        })
        resp = self.fetch("/hospital", method="POST", body=body)

        self.assertEqual(resp.code, 200)
        self.assertIn(b"OK: ID 1 for New Hospital", resp.body)

        r_mock.get.assert_called_with("hospital:autoID")
        self.assertEqual(r_mock.hset.call_count, 4)
        r_mock.incr.assert_called_with("hospital:autoID")

    @patch("main.r")
    def test_post_redis_connection_error(self, r_mock):
        r_mock.get.side_effect = redis.exceptions.ConnectionError()

        body = urllib.parse.urlencode({
            "name": "H",
            "address": "A",
            "beds_number": "1",
            "phone": "2",
        })
        resp = self.fetch("/hospital", method="POST", body=body)
        self.assertEqual(resp.code, 400)
        self.assertIn(b"Redis connection refused", resp.body)


if __name__ == "__main__":
    unittest.main()

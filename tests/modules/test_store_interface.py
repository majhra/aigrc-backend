import unittest
from collections import namedtuple
from itertools import count
from unittest.mock import MagicMock, patch

from app.modules.store_interface import RedisStore


class TestStoreInterface(unittest.TestCase):
    def setUp(self):
        # Setup a mock logger
        self.logger = MagicMock()
        self.logger.info.return_value = MagicMock()
        self.logger.warning.return_value = MagicMock()
        self.logger.error.return_value = MagicMock()

        self.mock_user_data = [
            {
                "unpacked": {
                    "key": "gorocoaico+test1@gmail.com",
                    "value": {
                        "full_name": "John Doe",
                        "email": "gorocoaico+test1@gmail.com",
                        "password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
                        "disabled": False,
                        "created_at": "2021-01-01T00:00:00",
                        "last_login": "2021-01-01T00:00:00",
                    },
                },
                "packed": {
                    "key": "gorocoaico+test1@gmail.com",
                    "value": {
                        "full_name": "John Doe",
                        "email": "gorocoaico+test1@gmail.com",
                        "password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
                        "disabled": b"\xc2",
                        "created_at": "2021-01-01T00:00:00",
                        "last_login": "2021-01-01T00:00:00",
                        # "redis_search_tag": "gorocoaico+test1@gmail.com"
                    },
                },
                "hgetall": {
                    "key": "gorocoaico+test1@gmail.com",
                    "value": {
                        b"full_name": b"John Doe",
                        b"email": b"gorocoaico+test1@gmail.com",
                        b"password": b"$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
                        b"disabled": b"\xc2",
                        b"created_at": b"2021-01-01T00:00:00",
                        b"last_login": b"2021-01-01T00:00:00",
                        # b"redis_search_tag": b"gorocoaico+test1@gmail.com"
                    },
                },
            },
            {
                "unpacked": {
                    "key": "gorocoaico+test2@gmail.com",
                    "value": {
                        "full_name": "Bill Smith",
                        "email": "gorocoaico+test2@gmail.com",
                        "password": "randompassword",
                        "disabled": False,
                        "created_at": "2021-01-01T00:00:00",
                        "last_login": "2021-01-01T00:00:00",
                    },
                },
                "packed": {
                    "key": "gorocoaico+test2@gmail.com",
                    "value": {
                        "full_name": "Bill Smith",
                        "email": "gorocoaico+test2@gmail.com",
                        "password": "randompassword",
                        "disabled": b"\xc2",
                        "created_at": "2021-01-01T00:00:00",
                        "last_login": "2021-01-01T00:00:00",
                        # "redis_search_tag": "gorocoaico+test2@gmail.com"
                    },
                },
                "hgetall": {
                    "key": "gorocoaico+test2@gmail.com",
                    "value": {
                        b"full_name": b"Bill Smith",
                        b"email": b"gorocoaico+test2@gmail.com",
                        b"password": b"randompassword",
                        b"disabled": b"\xc2",
                        b"created_at": b"2021-01-01T00:00:00",
                        b"last_login": b"2021-01-01T00:00:00",
                        # b"redis_search_tag": b"gorocoaico+test2@gmail.com"
                    },
                },
            },
        ]

    @patch("redis.Redis")
    def test_put_new_key(self, mock_redis):
        # Load the store
        prefix = "test"
        store = RedisStore(self.logger, prefix)
        mock_redis_instance = mock_redis.return_value

        # Assert that the mock redis was called with the correct arguments
        mock_redis.assert_called_with(host="localhost", port=6379)

        # Mock relevant Redis methods
        mock_redis_instance.incr.side_effect = (i for i in count(1))
        mock_redis_instance.zscore.side_effect = [
            None for i in range(len(self.mock_user_data))
        ]  # + [i for i in range(1, len(self.mock_user_data) + 1)]

        # Iterate over the mock data and assert that the mock redis was called with the correct arguments
        i = 0
        for user_data in self.mock_user_data:
            # Increment the counter
            i += 1

            # Call the method under test
            store.put(user_data["unpacked"]["key"], user_data["unpacked"]["value"])

            # Assert that the mock redis was called with the correct arguments
            mock_redis_instance.hmset.assert_called_with(
                f"{prefix}:{i}", user_data["packed"]["value"]
            )

        # Assert that duplicate keys cannot be added
        # for user_data in self.mock_user_data:
        #     with self.assertRaises(Exception):
        #         store.put(user_data["unpacked"]["key"], user_data["unpacked"]["value"])

    @patch("redis.Redis")
    def test_get(self, mock_redis):
        # Load the store
        prefix = "test"
        store = RedisStore(self.logger, prefix)
        mock_redis_instance = mock_redis.return_value

        # Assert that the mock redis was called with the correct arguments
        mock_redis.assert_called_with(host="localhost", port=6379)

        # Mock relevant Redis methods
        mock_redis_instance.zscore.side_effect = [
            i for i in range(1, len(self.mock_user_data) + 1)
        ] + [None]
        mock_redis_instance.hgetall.side_effect = [
            user_data["hgetall"]["value"] for user_data in self.mock_user_data
        ]

        # Iterate over the mock data and assert that the mock redis was called with the correct arguments
        i = 0
        for user_data in self.mock_user_data:
            # Increment the counter
            i += 1

            # Call the method under test
            result = store.get(user_data["unpacked"]["key"])

            # Assert that the mock redis was called with the correct arguments
            mock_redis_instance.hgetall.assert_called_with(f"{prefix}:{i}")

            # Assert that the result is correct
            self.assertEqual(result, user_data["unpacked"]["value"])

        # Assert that a key that does not exist returns None
        result = store.get("nonexistent_key")
        self.assertIsNone(result)

    @patch("redis.Redis")
    def test_keys(self, mock_redis):
        # Load the store
        prefix = "test"
        store = RedisStore(self.logger, prefix)
        mock_redis_instance = mock_redis.return_value

        # Assert that the mock redis was called with the correct arguments
        mock_redis.assert_called_with(host="localhost", port=6379)

        # Mock relevant Redis methods
        mock_redis_instance.zrange.return_value = [
            user_data["packed"]["key"].encode() for user_data in self.mock_user_data
        ]

        # Call the method under test
        result = store.keys()

        # Assert that the result is correct
        self.assertEqual(
            result, [user_data["packed"]["key"] for user_data in self.mock_user_data]
        )

    @patch("redis.Redis")
    def test_pop(self, mock_redis):
        # Load the store
        prefix = "test"
        store = RedisStore(self.logger, prefix)
        mock_redis_instance = mock_redis.return_value

        # Assert that the mock redis was called with the correct arguments
        mock_redis.assert_called_with(host="localhost", port=6379)

        # Mock relevant Redis methods
        mock_redis_instance.hgetall.side_effect = [
            user_data["hgetall"]["value"] for user_data in self.mock_user_data
        ]
        mock_redis_instance.zscore.side_effect = [
            i for i in range(1, len(self.mock_user_data) + 1)
        ] + [None]

        # Iterate over the mock data and assert that the mock redis was called with the correct arguments
        i = 0
        for user_data in self.mock_user_data:
            # Increment the counter
            i += 1

            # Call the method under test
            result = store.pop(user_data["unpacked"]["key"])

            # Assert that the mock redis was called with the correct arguments
            mock_redis_instance.hgetall.assert_called_with(f"{prefix}:{i}")
            mock_redis_instance.delete.assert_called_with(f"{prefix}:{i}")
            mock_redis_instance.zrem.assert_called_with(
                store.redis_set_name, user_data["unpacked"]["key"]
            )

            # Assert that the result is correct
            self.assertEqual(result, user_data["unpacked"]["value"])

        # Assert that an error is raised when the key does not exist
        with self.assertRaises(Exception):
            store.pop("nonexistent_key")

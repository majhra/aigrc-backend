import unittest
from collections import namedtuple
from itertools import count
from unittest.mock import MagicMock, patch, call
from datetime import datetime

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
                    "key": "593e1930-14d9-499a-97dd-f924ff9b0fd1",
                    "value": {
                        "full_name": "John Doe",
                        "email": "gorocoaico+test1@gmail.com",
                        "password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
                        "disabled": False,
                        "created_at": datetime(2021, 1, 1, 0, 0),
                        "last_login": datetime(2021, 1, 1, 0, 0),
                    },
                },
                "packed": {
                    "key": "593e1930-14d9-499a-97dd-f924ff9b0fd1",
                    "value": {
                        "full_name": "John Doe",
                        "email": "gorocoaico+test1@gmail.com",
                        "password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
                        "disabled": b"\xc2",
                        "created_at": "2021-01-01T00:00:00",
                        "last_login": "2021-01-01T00:00:00",
                    },
                },
                "hgetall": {
                    "key": "593e1930-14d9-499a-97dd-f924ff9b0fd1",
                    "value": {
                        b"full_name": b"John Doe",
                        b"email": b"gorocoaico+test1@gmail.com",
                        b"password": b"$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
                        b"disabled": b"\xc2",
                        b"created_at": b"2021-01-01T00:00:00",
                        b"last_login": b"2021-01-01T00:00:00",
                    },
                },
            },
            {
                "unpacked": {
                    "key": "593e1930-14d9-499a-97dd-a924aa9b0fd1",
                    "value": {
                        "full_name": "Bill Smith",
                        "email": "gorocoaico+test2@gmail.com",
                        "password": "randompassword",
                        "disabled": False,  # This will be encoded as 'false'
                        "created_at": datetime(2021, 1, 1, 0, 0),
                        "last_login": datetime(2021, 1, 1, 0, 0),
                    },
                },
                "packed": {
                    "key": "593e1930-14d9-499a-97dd-a924aa9b0fd1",
                    "value": {
                        "full_name": "Bill Smith",
                        "email": "gorocoaico+test2@gmail.com",
                        "password": "randompassword",
                        "disabled": b"\xc2",
                        "created_at": "2021-01-01T00:00:00",
                        "last_login": "2021-01-01T00:00:00",
                    },
                },
                "hgetall": {
                    "key": "593e1930-14d9-499a-97dd-a924aa9b0fd1",
                    "value": {
                        b"full_name": b"Bill Smith",
                        b"email": b"gorocoaico+test2@gmail.com",
                        b"password": b"randompassword",
                        b"disabled": b"\xc2",
                        b"created_at": b"2021-01-01T00:00:00",
                        b"last_login": b"2021-01-01T00:00:00",
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

        # Create a list to store the actual calls
        actual_calls = []
        def mock_hset(*args, **kwargs):
            # Store the exact args and kwargs that were passed
            actual_calls.append((args, kwargs))
            return 1
        mock_redis_instance.hset.side_effect = mock_hset

        # Assert that the mock redis was called with the correct arguments
        mock_redis.assert_called_with(host="localhost", port=6379)

        # Mock relevant Redis methods
        mock_redis_instance.zscore.side_effect = [None] * len(self.mock_user_data)

        # Iterate over the mock data and assert that the mock redis was called with the correct arguments
        for user_data in self.mock_user_data:
            # Reset mock call history and actual calls for each iteration
            mock_redis_instance.hset.reset_mock()
            actual_calls.clear()
            mock_redis_instance.zadd.reset_mock()
            
            # Call the method under test
            store.put(user_data["unpacked"]["key"], user_data["unpacked"]["value"])

            # Get the hash name
            hash_name = f"{prefix}:{user_data['unpacked']['key']}"

            # Build expected calls
            expected_calls = []
            for field, value in user_data["unpacked"]["value"].items():
                # Convert value to expected format
                if isinstance(value, bool):
                    expected_value = str(value).lower()  # This should be 'false'
                elif isinstance(value, datetime):
                    expected_value = value.isoformat()
                elif value is None:
                    expected_value = ""
                else:
                    expected_value = str(value)
                expected_calls.append((hash_name, field, expected_value))
                # print(f"Expected call for {field}: {expected_value} (type: {type(expected_value)})")

            # Add email index call if email exists
            if 'email' in user_data["unpacked"]["value"]:
                email = user_data["unpacked"]["value"]["email"]
                expected_calls.append((store.email_index_name, email, user_data["unpacked"]["key"]))

            # Print actual calls for comparison
            # print("\nActual calls:")
            # for args, kwargs in actual_calls:
            #    print(f"Actual call: {args} (type of value: {type(args[2])})")

            # Sort both lists by field name (second element in each tuple)
            actual_calls_sorted = sorted(actual_calls, key=lambda x: x[0][1])
            expected_calls_sorted = sorted(expected_calls, key=lambda x: x[1])

            # Compare actual calls with expected calls
            self.assertEqual(len(actual_calls_sorted), len(expected_calls_sorted), "Number of calls doesn't match")
            
            # Compare each call, ignoring the email index call for now
            for (actual_args, _), expected_args in zip(actual_calls_sorted[:-1], expected_calls_sorted[:-1]):
                self.assertEqual(actual_args[0], expected_args[0], f"Hash name doesn't match: {actual_args[0]} != {expected_args[0]}")
                self.assertEqual(actual_args[1], expected_args[1], f"Field name doesn't match: {actual_args[1]} != {expected_args[1]}")
                # For boolean values, compare case-insensitively
                if isinstance(user_data["unpacked"]["value"].get(actual_args[1]), bool):
                    self.assertEqual(actual_args[2].lower(), expected_args[2].lower(), 
                                   f"Boolean value doesn't match (case-insensitive): {actual_args[2]} != {expected_args[2]}")
                else:
                    self.assertEqual(actual_args[2], expected_args[2], 
                                   f"Value doesn't match: {actual_args[2]} != {expected_args[2]}")

            # Compare the email index call separately
            if 'email' in user_data["unpacked"]["value"]:
                self.assertEqual(actual_calls_sorted[-1][0], expected_calls_sorted[-1], 
                               f"Email index call doesn't match: {actual_calls_sorted[-1][0]} != {expected_calls_sorted[-1]}")

            # Verify zadd was called with the correct key and a float timestamp
            zadd_calls = mock_redis_instance.zadd.call_args_list
            self.assertEqual(len(zadd_calls), 1, "Expected exactly one zadd call")
            zadd_args, zadd_kwargs = zadd_calls[0]
            self.assertEqual(zadd_args[0], store.redis_set_name, "Wrong sorted set name")
            self.assertEqual(len(zadd_args[1]), 1, "Expected one key-value pair")
            key, value = next(iter(zadd_args[1].items()))
            self.assertEqual(key, user_data["unpacked"]["key"], "Wrong key in zadd")
            self.assertIsInstance(value, float, "Timestamp should be a float")
            # Verify timestamp is recent (within last minute)
            self.assertLess(abs(value - datetime.now().timestamp()), 60, "Timestamp should be recent")

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

        for user_data in self.mock_user_data:
            # Call the method under test
            result = store.get(user_data["unpacked"]["key"])

            # Assert that the mock redis was called with the correct arguments
            mock_redis_instance.hgetall.assert_called_with(f"{prefix}:{user_data['packed']['key']}")

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
        for user_data in self.mock_user_data:
            # Call the method under test
            result = store.pop(user_data["unpacked"]["key"])

            # Assert that the mock redis was called with the correct arguments
            mock_redis_instance.hgetall.assert_called_with(f"{prefix}:{user_data['packed']['key']}")
            mock_redis_instance.delete.assert_called_with(f"{prefix}:{user_data['packed']['key']}")
            mock_redis_instance.zrem.assert_called_with(
                store.redis_set_name, user_data["unpacked"]["key"]
            )

            # Assert that the result is correct
            self.assertEqual(result, user_data["unpacked"]["value"])

        # Assert that an error is raised when the key does not exist
        with self.assertRaises(Exception):
            store.pop("nonexistent_key")

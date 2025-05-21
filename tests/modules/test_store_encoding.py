import pytest
from datetime import datetime
import uuid
import msgpack
from app.modules.store_interface import RedisStore
from unittest.mock import Mock

@pytest.fixture
def mock_logger():
    return Mock()

@pytest.fixture
def redis_store(mock_logger):
    return RedisStore(logger=mock_logger, prefix="test")

class TestStoreEncoding:
    """Test suite for RedisStore encoding and decoding functionality"""

    def test_encoder_none(self, redis_store, mock_logger):
        """Test encoding of None values"""
        result = redis_store._encoder(None)
        assert result == b'\xc0'
        mock_logger.debug.assert_called()

    def test_encoder_datetime(self, redis_store, mock_logger):
        """Test encoding of datetime objects"""
        test_dt = datetime(2024, 1, 1, 12, 0, 0)
        result = redis_store._encoder(test_dt)
        assert result == "2024-01-01T12:00:00"
        mock_logger.debug.assert_called()

    def test_encoder_basic_types(self, redis_store, mock_logger):
        """Test encoding of basic Python types"""
        test_cases = [
            ("string", "string"),
            (123, "123"),
            (123.45, "123.45"),
            (True, "True"),
            (False, "False"),
        ]
        
        for input_val, expected in test_cases:
            result = redis_store._encoder(input_val)
            assert result == expected
            mock_logger.debug.assert_called()

    def test_encoder_uuid(self, redis_store, mock_logger):
        """Test encoding of UUID objects"""
        test_uuid = uuid.uuid4()
        result = redis_store._encoder(test_uuid)
        assert result == str(test_uuid)
        mock_logger.debug.assert_called()

    def test_encoder_dict(self, redis_store, mock_logger):
        """Test encoding of dictionaries"""
        test_dict = {
            "str": "value",
            "int": 123,
            "float": 123.45,
            "bool": True,
            "none": None,
            "datetime": datetime(2024, 1, 1, 12, 0, 0),
            "uuid": uuid.uuid4()
        }

        result = redis_store._encoder(test_dict)
        # Verify it's msgpack encoded
        assert isinstance(result, bytes)
        # Decode and verify contents using our decoder
        decoded = redis_store._decoder(result)
        print(f"Decoded structure: {decoded}")
        print(f"encoded: {result}")
        assert decoded["str"] == "value"
        assert decoded["int"] == "123"
        assert decoded["float"] == "123.45"
        assert decoded["bool"] == True
        assert decoded["none"] is None
        assert decoded["datetime"] == test_dict['datetime']
        assert isinstance(decoded["datetime"], datetime)
        assert isinstance(decoded["uuid"], uuid.UUID)
        mock_logger.debug.assert_called()

    def test_encoder_list(self, redis_store, mock_logger):
        """Test encoding of lists"""
        test_list = [
            "string",
            123,
            123.45,
            True,
            None,
            datetime(2024, 1, 1, 12, 0, 0),
            uuid.uuid4()
        ]

        result = redis_store._encoder(test_list)
        # Verify it's msgpack encoded
        assert isinstance(result, bytes)
        # Decode and verify contents using our decoder
        decoded = redis_store._decoder(result)
        assert decoded[0] == "string"
        assert decoded[1] == "123"
        assert decoded[2] == "123.45"
        assert decoded[3] == True
        assert decoded[4] == None
        assert decoded[5] == test_list[5]
        assert decoded[6] == test_list[6]
        assert isinstance(decoded[6], uuid.UUID)
        mock_logger.debug.assert_called()

    def test_encoder_nested_structures(self, redis_store, mock_logger):
        """Test encoding of nested structures"""
        test_data = {
            "list": [
                {"nested": "value"},
                [1, 2, 3],
                None
            ],
            "dict": {
                "inner": {
                    "key": "value",
                    "number": 123
                }
            }
        }
        
        # Encode the entire structure
        encoded = redis_store._encoder(test_data)
        assert isinstance(encoded, bytes)
        
        # Decode should handle all nested structures automatically
        decoded = redis_store._decoder(encoded)
        
        print("Encoded structure:", encoded)
        print("Decoded structure:", decoded)
        assert decoded["list"][0]["nested"] == "value"
        assert decoded["list"][1] == ["1", "2", "3"]
        assert decoded["list"][2] == None
        assert decoded["dict"]["inner"]["key"] == "value"
        assert decoded["dict"]["inner"]["number"] == "123"
        mock_logger.debug.assert_called()

    def test_encoder_custom_object(self, redis_store, mock_logger):
        """Test encoding of custom objects"""
        class CustomObject:
            def __init__(self, value):
                self.value = value
        
        test_obj = CustomObject("test")
        with pytest.raises(Exception):
            redis_store._encoder(test_obj)
        mock_logger.error.assert_called()

    def test_decoder_none_empty(self, redis_store):
        """Test decoding of None and empty values"""
        assert redis_store._decoder(None) is None
        assert redis_store._decoder(b'') is None
        assert redis_store._decoder("") is ""

    def test_decoder_datetime(self, redis_store):
        """Test decoding of datetime strings"""
        test_dt = "2024-01-01T12:00:00"
        result = redis_store._decoder(test_dt)
        assert isinstance(result, datetime)
        assert result.isoformat() == test_dt

    def test_decoder_boolean(self, redis_store):
        """Test decoding of boolean strings"""
        assert redis_store._decoder("true") is True
        assert redis_store._decoder("false") is False
        assert redis_store._decoder("TRUE") is True
        assert redis_store._decoder("FALSE") is False

    def test_decoder_uuid(self, redis_store):
        """Test decoding of UUID strings"""
        test_uuid = uuid.uuid4()
        result = redis_store._decoder(str(test_uuid))
        assert isinstance(result, uuid.UUID)
        assert result == test_uuid

    def test_decoder_msgpack(self, redis_store):
        """Test decoding of msgpack encoded data"""
        test_data = {
            "str": "value",
            "int": "123",
            "float": "123.45",
            "bool": True,
            "none": "",
            "list": ["1", "2", "3"]
        }
        encoded = msgpack.packb(test_data)
        result = redis_store._decoder(encoded)
        assert result == test_data

    def test_decoder_utf8(self, redis_store):
        """Test decoding of UTF-8 encoded data"""
        test_str = "Hello, 世界!"
        encoded = test_str.encode('utf-8')
        result = redis_store._decoder(encoded)
        assert result == test_str

    def test_decoder_nested_msgpack(self, redis_store):
        """Test decoding of nested msgpack structures"""
        test_data = {
            "list": [
                {"nested": "value"},
                ["1", "2", "3"],
                ""
            ],
            "dict": {
                "inner": {
                    "key": "value",
                    "number": "123"
                }
            }
        }
        encoded = msgpack.packb(test_data)
        result = redis_store._decoder(encoded)
        assert result == test_data

    def test_decoder_invalid_msgpack(self, redis_store):
        """Test decoding of invalid msgpack data"""
        invalid_data = b'\xc1' # This byte (0xC1) is reserved in the MessagePack spec and must never appear
        result = redis_store._decoder(invalid_data)
        assert isinstance(result, bytes)

    def test_decoder_invalid_utf8(self, redis_store):
        """Test decoding of invalid UTF-8 data"""
        invalid_data = b'\xff\xfe'  # Invalid UTF-8 sequence
        result = redis_store._decoder(invalid_data)
        assert isinstance(result, bytes)
        assert result == invalid_data

    def test_encoder_decoder_roundtrip(self, redis_store, mock_logger):
        """Test roundtrip encoding and decoding of various data types"""
        test_cases = [
            "string",
            123,
            123.45,
            True,
            None,
            datetime(2024, 1, 1, 12, 0, 0),
            uuid.uuid4(),
            ["1", "2", "3"],
            {"key": "value", "number": "123"},
            {
                "nested": {
                    "list": ["1", "2", "3"],
                    "dict": {"key": "value"}
                }
            }
        ]
        
        for test_value in test_cases:
            encoded = redis_store._encoder(test_value)
            decoded = redis_store._decoder(encoded)
            
            if isinstance(test_value, (str, int, float, bool)):
                assert str(decoded) == str(test_value)
            elif isinstance(test_value, datetime):
                assert decoded.isoformat() == test_value.isoformat()
            elif isinstance(test_value, uuid.UUID):
                assert str(decoded) == str(test_value)
            elif isinstance(test_value, (list, dict)):
                assert decoded == test_value
            elif test_value is None:
                assert decoded is None 
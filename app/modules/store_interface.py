from datetime import datetime
from typing import Any, Dict, List, Protocol

import msgpack
import redis
import uuid

class StoreProtocol(Protocol):
    def put(self, key: str, value: dict) -> None:
        pass

    def get(self, key: str) -> Dict[str, str] | None:
        pass

    def get_by_email(self, email: str) -> Dict[str, str] | None:
        """Get user by email using the email index"""
        pass

    def keys(self) -> List[str] | None:
        pass

    def pop(self, key: str) -> dict | None:
        pass


class RedisStore(StoreProtocol):
    def __init__(self, logger, prefix: str, host: str = "localhost", port: int = 6379):
        """
        Object to store and retrieve data from Redis
        :param logger: Object used for logging
        :param prefix: Prefix to use for the Redis hash name (e.g., "user" is used for "user:<uuid>")
        :param host: Redis host
        :param port: Redis port
        """
        self.logger = logger
        self.prefix = prefix.lower()
        self.redis_set_name = f"{self.prefix}_sorted_set"  # Stores UUIDs only
        self.email_index_name = f"{self.prefix}_email_index"  # Maps email -> UUID

        try:
            self.redis = redis.Redis(host=host, port=port)
        except Exception as e:
            self.logger.error(f"Redis initialisation load fail: {e}")
            raise Exception(f"Redis initialisation load fail: {e}")

    def _get_hash_name(self, key: str) -> str:
        """Get the hash name for a key"""
        return f"{self.prefix}:{key}"

    def _hgetall(self, hash_name: str):
        """
        Gets all values from a Redis hash
        :param hash_name: Name of the hash
        """
        try:
            packed = self.redis.hgetall(hash_name)
        except Exception as e:
            self.logger.error(f"Redis download fail: {e}")
            raise Exception(f"Redis download fail: {e}")
        try:
            unpacked = {
                self._decoder(key): self._decoder(value) for key, value in packed.items()
            }
        except Exception as e:
            self.logger.error(f"Redis decode fail: {e}")
            raise Exception(f"Redis decode fail: {e}")
        return unpacked or None

    def _encoder(self, obj):
        """Function to serialise objects for Redis"""
        self.logger.debug(f"Encoding value: {obj} of type {type(obj)}")
        
        if obj is None:
            # Always encode None using msgpack to ensure consistent handling
            return msgpack.packb(None)
        elif isinstance(obj, datetime):
            encoded = obj.isoformat()
        elif isinstance(obj, (str, int, float)):
            encoded = str(obj)  # Ensure all basic types are strings
        elif isinstance(obj, bool):
            encoded = str(obj).lower()  # Convert bool to 'true' or 'false'
        elif isinstance(obj, uuid.UUID):
            encoded = str(obj)
        elif isinstance(obj, dict):
            # First encode all values in the dictionary
            encoded_dict = {k: self._encoder(v) for k, v in obj.items()}
            # Then serialize the whole dictionary
            return msgpack.packb(encoded_dict)
        elif isinstance(obj, list):
            # First encode all items in the list
            encoded_list = [self._encoder(item) for item in obj]
            # Then serialize the whole list
            return msgpack.packb(encoded_list)
        else:
            # For any other type (custom objects), use msgpack
            try:
                encoded = msgpack.packb(obj)
            except Exception as e:
                self.logger.error(f"Failed to encode object of type {type(obj)}: {e}")
                raise
            
        self.logger.debug(f"Encoded value: {encoded} of type {type(encoded)}")
        return encoded

    def _decoder(self, obj):
        """Function to deserialise objects from Redis"""
        if obj is None or obj == b'':  # Handle empty bytes as None
            return None
        if obj == "":  # Handle empty string as empty string
            return ""
        if isinstance(obj, str):
            # Try to parse as datetime first
            try:
                return datetime.fromisoformat(obj)
            except ValueError:
                # Try to parse as boolean
                if obj.lower() == 'true':
                    return True
                if obj.lower() == 'false':
                    return False
                try:
                    return uuid.UUID(obj)
                except ValueError:
                    pass
                return obj
        if isinstance(obj, bytes):
            # Try msgpack first
            try:
                decoded = msgpack.unpackb(obj)
                # Recursively decode the entire structure
                return self._decoder(decoded)
            except (msgpack.exceptions.ExtraData, msgpack.exceptions.UnpackException):
                # If not msgpack, try UTF-8
                try:
                    decoded = obj.decode("utf-8")
                    # Try to parse as boolean
                    if decoded.lower() == 'true':
                        return True
                    if decoded.lower() == 'false':
                        return False
                    try:
                        return uuid.UUID(decoded)
                    except ValueError:
                        pass
                    # Try to parse as datetime
                    try:
                        return datetime.fromisoformat(decoded)
                    except ValueError:
                        pass
                    return decoded
                except UnicodeDecodeError:
                    return obj
        # If we get a dict or list, recursively decode their values
        if isinstance(obj, dict):
            return {k: self._decoder(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._decoder(v) for v in obj]
        return obj

    def put(self, key: str, value: dict):
        """
        Uploads data to Redis
        :param key: UUID key to use for the data
        :param value: Data to upload
        """
        self.logger.info(f'Redis put called: "{key}": {value}')

        # Get the hash name using the UUID
        hash_name = self._get_hash_name(key)

        try:
            # Log the input value types
            self.logger.debug(f"Input value types: {[(k, type(v)) for k, v in value.items()]}")
            
            # Store each field individually using hset
            for k, v in value.items():
                try:
                    encoded_value = self._encoder(v)
                    self.logger.debug(f"Setting {k}: {v} -> {encoded_value} (type: {type(encoded_value)})")
                    # Add debug logging for the actual Redis call
                    self.logger.debug(f"About to call hset with: {hash_name}, {k}, {encoded_value} (type: {type(encoded_value)})")
                    self.redis.hset(hash_name, k, encoded_value)
                    # Add debug logging after the Redis call
                    self.logger.debug(f"After hset call for {k}: {encoded_value} (type: {type(encoded_value)})")
                except Exception as e:
                    self.logger.error(f"Failed to encode/set {k}: {v} of type {type(v)}. Error: {e}")
                    raise
            
            # Add the UUID to the sorted set with current timestamp
            self.redis.zadd(self.redis_set_name, {key: datetime.now().timestamp()})
            
            # Update email index if email is present
            if 'email' in value and value['email']:
                # Remove any existing email mapping first
                old_uuid = self.redis.hget(self.email_index_name, value['email'])
                if old_uuid and old_uuid.decode('utf-8') != key:
                    # If email was mapped to a different UUID, remove that mapping
                    self.redis.hdel(self.email_index_name, value['email'])
                # Add new email -> UUID mapping
                self.redis.hset(self.email_index_name, value['email'], key)
                
        except Exception as e:
            self.logger.error(f"Redis upload fail: {e}")
            self.logger.error(f"Failed value: {value}")
            raise Exception(f"Redis upload fail: {e}")

        self.logger.info(f"Redis put complete for key: {key}")

    def get_by_email(self, email: str) -> Dict[str, str] | None:
        """Get user by email using the email index"""
        try:
            # Get UUID from email index
            uuid_bytes = self.redis.hget(self.email_index_name, email.lower())
            self.logger.info(f"Redis get by email called: {email} -> {uuid_bytes}")
            if not uuid_bytes:
                return None
            
            # Get user data using the UUID
            uuid_str = uuid_bytes.decode('utf-8')
            return self.get(uuid_str)
        except Exception as e:
            self.logger.error(f"Redis email lookup fail: {e}")
            raise Exception(f"Redis email lookup fail: {e}")

    def get(self, key: str):
        """
        Downloads data from Redis
        :param key: UUID key to fetch data
        """
        self.logger.info(f"Redis get called: {key}")

        # Check if key exists in sorted set
        if not self.redis.zscore(self.redis_set_name, key):
            self.logger.warning(f"Redis get complete: no data found for {key}")
            return None

        # Get the hash name using the UUID
        hash_name = self._get_hash_name(key)
        data = self._hgetall(hash_name)

        try:
            # sometimes this is enpty, mostly on test data
            self.logger.info(f"Redis get complete: {data['id']}")
        except Exception as e:
            pass
        return data

    def keys(self):
        """Returns all UUIDs in the Redis database"""
        self.logger.info(f"Redis keys called for {self.redis_set_name}")
        try:
            # Get all UUIDs from the sorted set
            keys = self.redis.zrange(self.redis_set_name, 0, -1)
            keys_decoded = [key.decode("utf-8") for key in keys]
            # self.logger.info("Redis keys complete")
            return keys_decoded
        except Exception as e:
            self.logger.error(f"Redis fetch keys fail: {e}")
            raise Exception(f"Redis fetch keys fail: {e}")

    def pop(self, key: str):
        """
        Removes data from Redis
        :param key: UUID key to remove data
        """
        self.logger.info(f"Redis pop called: {key}")

        # Get the hash name using the UUID
        hash_name = self._get_hash_name(key)
        data = self._hgetall(hash_name)

        if not data:
            self.logger.error(f"Redis pop fail: {key} does not exist")
            raise Exception(f"Redis pop fail: {key} does not exist")

        try:
            # Remove from email index if email exists
            if 'email' in data:
                self.redis.hdel(self.email_index_name, data['email'])
            
            # Delete the hash and remove from sorted set
            self.redis.delete(hash_name)
            self.redis.zrem(self.redis_set_name, key)
        except Exception as e:
            self.logger.error(f"Redis delete fail: {e}")
            raise Exception(f"Redis delete fail: {e}")

        self.logger.info(f"Redis pop complete: {data}")
        return data


class LocalStore(StoreProtocol):
    def __init__(self):
        self.data: Dict[str, Any] = {}
        self.email_index: Dict[str, str] = {}  # Maps email to UUID

    def put(self, key: str, value: dict) -> None:
        self.data[str(key)] = value
        # Update email index if email is present
        if 'email' in value and value['email']:
            self.email_index[value['email']] = key

    def get(self, key: str) -> Dict[str, str] | None:
        return self.data.get(str(key), None)

    def get_by_email(self, email: str) -> Dict[str, str] | None:
        # Get UUID from email index
        uuid = self.email_index.get(email.lower())
        if not uuid:
            return None
        # Get user data using UUID
        return self.data.get(uuid)

    def keys(self) -> List[str] | None:
        return list(self.data.keys())

    def pop(self, key: str) -> dict | None:
        # Remove from email index if email exists
        user_data = self.data.get(str(key))
        if user_data and 'email' in user_data:
            self.email_index.pop(user_data['email'], None)
        return self.data.pop(str(key), None)

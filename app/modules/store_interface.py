from datetime import datetime
from typing import Any, Dict, List, Protocol

import msgpack
import redis


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
        :param prefix: Prefix to use for the Redis hash name (e.g., "user" is used for "user:<id>")
        :param host: Redis host
        :param port: Redis port
        """
        # Initialise the logger
        self.logger = logger
        # self.logger.info("[+] Store Creation")

        # Set variables
        self.prefix = prefix.lower()
        self.redis_id_name = f"{self.prefix}_id"
        self.redis_set_name = f"{self.prefix}_sorted_set"
        self.email_index_name = f"{self.prefix}_email_index"  # New email index

        # Initialise the redis connection
        try:
            self.redis = redis.Redis(host=host, port=port)
            # self.logger.info("Redis Store Loaded") # initialising the redis connection doesn't actually connect to the redis server, so this is a bit premature
        except Exception as e:
            self.logger.error(f"Redis initialisation load fail: {e}")
            raise Exception(f"Redis initialisation load fail: {e}")

    def _hgetall(self, hash_name: str):
        """
        Gets all values from a Redis hash
        :param hash_name: Name of the hash
        """
        # Grab the data from Redis
        try:
            packed = self.redis.hgetall(hash_name)
        except Exception as e:
            self.logger.error(f"Redis download fail: {e}")
            raise Exception(f"Redis download fail: {e}")

        # Unpack data
        unpacked = {
            self._decoder(key): self._decoder(value) for key, value in packed.items()
        }

        # Return the unpacked values or None if the hash doesn't exist
        return unpacked or None

    def _encoder(self, obj):
        """
        Function to serialise stubborn objects for Redis
        :param obj: Object to serialise
        """
        if isinstance(obj, datetime):
            return obj.isoformat()

        if isinstance(obj, (str, int)) and not isinstance(
            obj, bool
        ):  # bool is a subclass of int, so we need to exclude it
            return obj

        return msgpack.packb(obj)

    def _decoder(self, obj):
        """
        Function to deserialise stubborn objects for Redis
        :param obj: Object to deserialise
        """
        if isinstance(obj, str):
            try:
                return datetime.fromisoformat(obj)
            except ValueError:
                pass

        if isinstance(obj, bytes):
            try:
                return msgpack.unpackb(obj)
            except msgpack.exceptions.ExtraData:
                pass

        return obj.decode("utf-8")

    def get_by_email(self, email: str) -> Dict[str, str] | None:
        """
        Get user by email using the email index
        :param email: Email to look up
        """
        try:
            # Get UUID from email index
            user_id = self.redis.hget(self.email_index_name, email)
            if not user_id:
                return None
            
            # Get user data using UUID
            return self.get(user_id.decode('utf-8'))
        except Exception as e:
            self.logger.error(f"Redis email lookup fail: {e}")
            raise Exception(f"Redis email lookup fail: {e}")

    def put(self, key: str, value: dict):
        """
        Uploads data to Redis
        :param key: UUID key to use for the data
        :param value: Data to upload
        """
        # Logging
        self.logger.info(f'Redis put called: "{key}": {value}')

        # Get item ID
        try:
            id = self.redis.zscore(self.redis_set_name, key)
            if id:
                id = int(id)  # Convert to int if value not None
        except Exception as e:
            self.logger.error(f"Redis fetch ID fail: {e}")
            raise Exception(f"Redis fetch ID fail: {e}")

        # Get the hash name
        # If the key doesn't exist, create a new ID (we allow data to be overwritten)
        if id:
            hash_name = f"{self.prefix}:{id}"
        else:
            try:
                id = self.redis.incr(self.redis_id_name)
                hash_name = f"{self.prefix}:{id}"
            except Exception as e:
                self.logger.error(f"Redis increment fail: {e}")
                raise Exception(f"Redis increment fail: {e}")

        # Redis requires all values to be serialisable
        packed = {k: self._encoder(v) for k, v in value.items()}

        # Store the value in Redis and add the key to the sorted set
        try:
            self.redis.hmset(hash_name, packed)
            self.redis.zadd(self.redis_set_name, {key: id})
            
            # Update email index if email is present
            if 'email' in value and value['email']:
                self.redis.hset(self.email_index_name, value['email'], key)
                
        except Exception as e:
            self.logger.error(f"Redis upload fail: {e}")
            raise Exception(f"Redis upload fail: {e}")

        # Logging
        self.logger.info(f"Redis put complete: {packed}")

    def get(self, key: str):
        """
        Downloads data from Redis
        :param key: Unique key to fetch data (the equivalent of a primary key)
        """
        # Logging
        self.logger.info(f"Redis get called: {key}")

        # Get item ID
        try:
            id = self.redis.zscore(self.redis_set_name, key)

            if not id:
                self.logger.warning(f"Redis get complete: no data found for {key}")
                return None

            id = int(id)  # type: ignore
        except Exception as e:
            self.logger.error(f"Redis fetch ID fail: {e}")
            raise Exception(f"Redis fetch ID fail: {e}")

        # Get the hash name
        hash_name = f"{self.prefix}:{id}"

        # Grab the data from Redis
        data = self._hgetall(hash_name)

        # Logging
        self.logger.info(f"Redis get complete: {data}")

        # Return the unpacked values or None if the hash doesn't exist
        return data or None

    def keys(self):
        """
        Returns all keys in the Redis database that match the prefix (keys are the equivalent of a primary key)
        """
        # Logging
        self.logger.info(f"Redis keys called")

        # Get all keys
        try:
            keys = self.redis.zrange(self.redis_set_name, 0, -1)
        except Exception as e:
            self.logger.error(f"Redis fetch keys fail: {e}")
            raise Exception(f"Redis fetch keys fail: {e}")

        # Decode the keys
        keys_decoded = [key.decode("utf-8") for key in keys]

        # Logging
        self.logger.info(f"Redis keys complete")

        # Return the keys
        return keys_decoded

    def pop(self, key: str):
        """
        Removes data from Redis
        :param key: UUID key to remove data
        """
        # Logging
        self.logger.info(f"Redis pop called: {key}")

        # Get item ID
        try:
            id = self.redis.zscore(self.redis_set_name, key)
            if id:
                id = int(id)  # Convert to int if value not None
        except Exception as e:
            self.logger.error(f"Redis fetch ID fail: {e}")
            raise Exception(f"Redis fetch ID fail: {e}")

        # Get hash name
        if id:
            hash_name = f"{self.prefix}:{id}"
        else:
            self.logger.error(f"Redis pop fail: {key} does not exist")
            raise Exception(f"Redis pop fail: {key} does not exist")

        # Grab the data from Redis
        data = self._hgetall(hash_name)

        # Delete the hash
        try:
            # Remove from email index if email exists
            if 'email' in data:
                self.redis.hdel(self.email_index_name, data['email'])
            
            self.redis.delete(hash_name)
            self.redis.zrem(self.redis_set_name, key)
        except Exception as e:
            self.logger.error(f"Redis delete fail: {e}")
            raise Exception(f"Redis delete fail: {e}")

        # Logging
        self.logger.info(f"Redis pop complete: {data}")

        # Return the deleted data
        return data


class LocalStore(StoreProtocol):
    def __init__(self):
        self.data: Dict[str, Any] = {}

    def put(self, key: str, value: dict) -> None:
        self.data[key] = value

    def get(self, key: str) -> Dict[str, str] | None:
        return self.data.get(key, None)

    def keys(self) -> List[str] | None:
        return list(self.data.keys())

    def pop(self, key: str) -> dict | None:
        return self.data.pop(key, None)

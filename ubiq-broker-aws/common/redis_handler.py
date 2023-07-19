import json
from redis import StrictRedis
from typing import Dict, List, Any


class RedisHandler:
    """
    Encapsulates Redis client connection and handles getting/setting Ubiq API
    key in the Redis cache.
    """

    def __init__(self, redis_config="redis.json") -> None:
        """
        Reads the Redis configuration file and configures the Redis client.

        Args:
            redis_config: name of JSON configuration file containing Redis host,
                port, database, password and other Redis configuration parameters.
        """
        # Read Redis configuration file
        config = json.load(open(redis_config))

        # Configure Redis client from configuration file parameters
        self.redis = StrictRedis(**config)

    def key_exists(
        self, access_key: str, signing_key: str, endpoint_name: str, *args: List[str]
    ) -> bool:
        """
        Tests whether a Ubiq API key corresponding to the given API access key,
        signing key and endpoint has already been cached.

        Args:
            access_key: the Ubiq API access key
            signing_key: the Ubiq API secret signing key
            endpoint_name: the endpoint that was invoked to broker a Ubiq API call

        Returns:
            Boolean value indicating whether a Ubiq API key corresponding to the
            given access key, signing key and endpoint has already been cached.
        """
        return self.redis.exists(
            self._derive_key(access_key, signing_key, endpoint_name, *args)
        )

    def get_key(
        self, access_key: str, signing_key: str, endpoint_name: str, *args: List[str]
    ) -> Dict[str, Any]:
        """
        Retrieves Ubiq API key corresponding to the given access key, signing
        key and endpoint from the cache.

        Args:
            access_key: the Ubiq API access key
            signing_key: the Ubiq API secret signing key
            endpoint_name: the endpoint that was invoked to broker a Ubiq API call

        Returns:
            Cached Ubiq API key corresponding to the given access key, signing
            key and endpoint.
        """
        return json.loads(
            self.redis.get(
                self._derive_key(access_key, signing_key, endpoint_name, *args)
            )
        )

    def set_key(
        self,
        access_key: str,
        signing_key: str,
        endpoint_name: str,
        ubiq_key: Dict[str, Any],
        *args: List[str],
    ) -> None:
        """
        Caches a Ubiq API key corresponding to the given access key, signing key
        and endpoint.

        Args:
            access_key: the Ubiq API access key
            signing_key: the Ubiq API secret signing key
            endpoint_name: the endpoint that was invoked to broker a Ubiq API call
            ubiq_key: the Ubiq API key to cache
        """
        self.redis.set(
            self._derive_key(access_key, signing_key, endpoint_name, *args),
            json.dumps(ubiq_key),
        )

    @staticmethod
    def _derive_key(
        access_key: str, signing_key: str, endpoint_name: str, *args: List[str]
    ) -> str:
        """
        Derives unique Redis key from a given access key, signing key, endpoint
        name and any additional optional parameters (e.g., Field Format Specification)
        by concatenating each parameter with hyphen separators.

        Args:
            access_key: the Ubiq API access key
            signing_key: the Ubiq API secret signing key
            endpoint_name: the endpoint that was invoked to broker a Ubiq API call

        Returns:
            Derived Redis key for the given access key, signing key, Ubiq
            endpoint and optional delineating parameters.
        """
        return "-".join([access_key, signing_key, endpoint_name, *args])


# Set singleton instance
redis_client = RedisHandler()

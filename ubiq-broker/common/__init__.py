# Base URL for Ubiq REST API endpoint
UBIQ_API_URL = "https://api.ubiqsecurity.com/api/v0"

# Expected character length of access key and signing key
ACCESS_KEY_LENGTH = 24
SIGNING_KEY_LENGTH = 44

import json
import logging
import requests
from typing import Any, Dict, List
from .auth import http_auth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(filename)s:%(lineno)s - %(funcName)20s()] %(message)s",
)


def validate_access_key(access_key: Any) -> None:
    """
    Validates that the access key is a string and it matches the expected length,
    and throws an attribute error if either of those conditions fail.

    Args:
        access_key: the Ubiq API access key received in the request
    """
    if not isinstance(access_key, str) or len(access_key) != ACCESS_KEY_LENGTH:
        raise AttributeError("Access key ID in request is malformed")


def validate_signing_key(signing_key: Any) -> None:
    """
    Validates that the secret signing key is a string and it matches the expected
    length, and throws an attribute error if either of those conditions fail.

    Args:
        signing_key: the Ubiq API secret signing key received in the request
    """
    if not isinstance(signing_key, str) or len(signing_key) != SIGNING_KEY_LENGTH:
        raise AttributeError("Secret signing key in request is malformed")


def unpack_request(request: Any, expected_num_attributes: int) -> List[List[Any]]:
    """
    Unpacks, validates and returns the request contents.

    Args:
        request: content of the REST request
        expected_num_attributes: expected number of attributes for each row
            in the request body

    Returns:
        List of request rows, with each row containing one or more request
        attribute values.
    """

    # Validate outer request structure
    if (
        "data" not in request.keys()
        or not isinstance(request["data"], list)
        or len(request["data"]) < 1
    ):
        raise AttributeError("Request body does not match the expected format")

    # List of request rows
    request_rows: List[List[Any]] = []

    # Validate each row in the request
    for entry in request["data"]:

        # Note that the first entry in each request should be an integer row index
        if (
            not isinstance(entry, list)
            or len(entry) != expected_num_attributes
            or not isinstance(entry[0], int)
        ):
            raise AttributeError(
                f"Row [{entry[0]}] in request does not match the expected format or contain the expected number of attributes ([{len(entry)}] rather than [{expected_num_attributes}])"
            )

        # Append the validated entry
        request_rows.append(entry)

    # Extract and return body attribute values
    return request_rows


def parse_ubiq_response(
    ubiq_response: requests.models.Response, params: List[str]
) -> Dict[str, Any]:
    """
    Extracts Ubiq API response contents, converts to a dictionary representation
    and validates API response and response contents.

    Args:
        ubiq_response: response contents from the Ubiq API
        params: list of parameter names expected to be contained in the response
            from the Ubiq API

    Returns:
        Ubiq API response contents as a dictionary.
    """
    try:
        # Parse contents of the Ubiq API response
        contents = json.loads(ubiq_response.content.decode("utf-8"))
    except Exception as e:
        raise RuntimeError("An exception occurred while parsing Ubiq response") from e

    # Validate that Ubiq request was successful
    if "status" in contents.keys() and not 200 <= contents["status"] < 300:
        raise RuntimeError("Ubiq API request failed")

    # Validate that Ubiq repsonse contains all needed parameters
    if any(param not in contents.keys() for param in params):
        raise RuntimeError("Ubiq API endpoint did not return all requisite parameters")

    return contents


def format_error_response(error_msg: str) -> str:
    """
    Wraps error message in list which is assigned as a value of key "data,"
    which is the format expected by Snowflake external functions.

    Args:
        error_msg: error message to include in Snowflake response

    Returns:
        Reformatted response to match format expected by Snowflake external
        functions.
    """
    return json.dumps({"data": [[0, error_msg]]})


def format_response(contents: List[Dict[str, Any]], params: List[str]) -> str:
    """
    Creates dictionary of response parameters and wraps response contents in
    list which is assigned as a value of key "data," which is the format expected
    by Snowflake external functions.

    Args:
        contents: response contents, which should be a list of dictionaries
        params: list of parameter names to be contained in the response

    Returns:
        Reformatted response to match format expected by Snowflake external
        functions.
    """
    return json.dumps(
        {
            "data": [
                [idx, {param: contents[param] for param in params}]
                for idx, contents in enumerate(contents)
            ]
        }
    )

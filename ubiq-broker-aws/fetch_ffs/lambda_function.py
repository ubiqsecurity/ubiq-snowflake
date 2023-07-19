import logging
import requests
# from common.redis_handler import redis_client
import json 
from common import (
    format_response,
    format_error_response,
    http_auth,
    unpack_request,
    validate_access_key,
    validate_signing_key,
    parse_ubiq_response,
    UBIQ_API_URL,
)

# Parameter names to extract from the Ubiq FFS API response
UBIQ_FFS_PARAMS = [
    "name",
    "encryption_algorithm",
    "passthrough",
    "input_character_set",
    "output_character_set",
    "msb_encoding_bits",
    "tweak",
    "tweak_min_len",
    "tweak_max_len",
]

def lambda_handler(event, context):
    logging.info("Received request to fetch Field Format Specification (FFS)")

    try:
        if(isinstance(event,list) or isinstance(event, dict)):
            req_body = event;
        else:
            req_body = json.loads(event)
    except Exception as e:
        msg = "An exception occurred while parsing FFS request body contents as JSON"
        logging.exception(msg)
        return format_error_response(msg)

    try:
        # Extract and validate each row within the request
        rows = unpack_request(req_body, 4)
    except AttributeError as e:
        logging.exception(e)
        return format_error_response(str(e))

    # List of response contents
    response_contents = []

    # Extract FFS name, access key ID and secret signing key and query Ubiq API
    for idx, ffs_name, access_key, signing_key in rows:

        logging.info(f"Processing row [{idx}] of fetch FFS request")

        # Validate FFS name
        if not isinstance(ffs_name, str):
            msg = "Field Format Specification in request is malformed"
            logging.error(msg)
            return format_error_response(msg)

        # Validate access key and signing key format
        try:
            validate_access_key(access_key)
            validate_signing_key(signing_key)
        except AttributeError as e:
            logging.exception(e)
            return format_error_response(str(e))

        # # If the Ubiq API key has been cached, get it from the cache and skip
        # # the Ubiq API call
        # if redis_client.key_exists(access_key, signing_key, __name__, ffs_name):
        #     contents = redis_client.get_key(access_key, signing_key, __name__, ffs_name)

        # If the key doesn't exist, call the Ubiq API to get it
        else:
            try:
                # Call Ubiq API to get the FFS metadata
                ubiq_response = requests.get(
                    url=f"{UBIQ_API_URL}/ffs?ffs_name={ffs_name}&papi={access_key}",
                    auth=http_auth(access_key, signing_key),
                )
            except Exception as e:
                msg = "An exception occurred while calling Ubiq FFS API endpoint"
                logging.exception(msg)
                return format_error_response(msg)

            try:
                # Parse contents of Ubiq FFS API response
                contents = parse_ubiq_response(ubiq_response, UBIQ_FFS_PARAMS)
            except Exception as e:
                logging.exception(e)
                return format_error_response(str(e))

            # # Cache the resulting Ubiq key
            # redis_client.set_key(access_key, signing_key, __name__, contents, ffs_name)

        # Append to list of response contents
        response_contents.append(contents)

    logging.info("Request to fetch Field Format Specification (FFS) successful")

    # Transmit HTTP response with Ubiq-supplied FFS parameters
    return format_response(response_contents, UBIQ_FFS_PARAMS)
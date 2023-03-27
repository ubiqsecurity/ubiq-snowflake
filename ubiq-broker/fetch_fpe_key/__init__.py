import logging
import azure.functions as func
import requests
from common.redis_handler import redis_client
from common import (
    http_auth,
    format_response,
    format_error_response,
    unpack_request,
    validate_access_key,
    validate_signing_key,
    parse_ubiq_response,
    UBIQ_API_URL,
)

# Parameter names to extract from the Ubiq FPE API response
UBIQ_FPE_PARAMS = ["encrypted_private_key", "wrapped_data_key", "key_number"]


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Received request to fetch Format Preserving Encryption (FPE) key")

    try:
        req_body = req.get_json()
    except Exception as e:
        msg = "An exception occurred while parsing FFS request body contents as JSON"
        logging.exception(msg)
        return func.HttpResponse(format_error_response(msg), status_code=400)

    try:
        # Extract and validate each row within the request
        rows = unpack_request(req_body, 4)
    except AttributeError as e:
        logging.exception(e)
        return func.HttpResponse(format_error_response(str(e)), status_code=400)

    # List of response contents
    response_contents = []

    # Extract FFS name, access key ID and secret signing key and query Ubiq API
    for idx, ffs_name, access_key, signing_key in rows:

        logging.info(f"Processing row [{idx}] of fetch FPE key request")

        # Validate FFS name
        if not isinstance(ffs_name, str):
            msg = "Field Format Specification in request is malformed"
            logging.error(msg)
            return func.HttpResponse(format_error_response(msg), status_code=400)

        # Validate access key and signing key format
        try:
            validate_access_key(access_key)
            validate_signing_key(signing_key)
        except AttributeError as e:
            logging.exception(e)
            return func.HttpResponse(format_error_response(str(e)), status_code=400)

        # If the Ubiq API key has been cached, get it from the cache and skip
        # the Ubiq API call
        if redis_client.key_exists(access_key, signing_key, __name__, ffs_name):
            contents = redis_client.get_key(access_key, signing_key, __name__, ffs_name)

        # If the key doesn't exist, call the Ubiq API to get it
        else:
            try:
                # Call Ubiq API to get the FPE key
                ubiq_response = requests.get(
                    url=f"{UBIQ_API_URL}/fpe/key?ffs_name={ffs_name}&papi={access_key}",
                    auth=http_auth(access_key, signing_key),
                )
            except Exception as e:
                msg = "An exception occurred while calling Ubiq FPE API endpoint"
                logging.exception(msg)
                return func.HttpResponse(format_error_response(msg), status_code=500)

            try:
                # Parse contents of Ubiq FPE API response
                contents = parse_ubiq_response(ubiq_response, UBIQ_FPE_PARAMS)
            except Exception as e:
                logging.exception(e)
                return func.HttpResponse(format_error_response(str(e)), status_code=500)

            # Cache the resulting Ubiq key
            redis_client.set_key(access_key, signing_key, __name__, contents, ffs_name)

        # Append to list of response contents
        response_contents.append(contents)

    logging.info("Request to fetch FPE encryption key successful")

    # Transmit HTTP response with Ubiq-supplied FPE parameters
    # NOTE: Snowflake only recognizes status code 200 as a success indicator
    return func.HttpResponse(
        format_response(response_contents, UBIQ_FPE_PARAMS),
        status_code=200,
    )

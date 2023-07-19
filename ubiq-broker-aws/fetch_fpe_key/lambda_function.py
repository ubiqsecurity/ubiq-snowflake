import logging
import json
import requests
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


def lambda_handler(event, context):
    logging.info("Received request to fetch Format Preserving Encryption (FPE) key")

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

        logging.info(f"Processing row [{idx}] of fetch FPE key request")

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
                return format_error_response(msg)

            try:
                # Parse contents of Ubiq FPE API response
                contents = parse_ubiq_response(ubiq_response, UBIQ_FPE_PARAMS)
            except Exception as e:
                logging.exception(e)
                return format_error_response(str(e))

        # Append to list of response contents
        response_contents.append(contents)

    logging.info("Request to fetch FPE encryption key successful")

    # Transmit HTTP response with Ubiq-supplied FPE parameters
    return format_response(response_contents, UBIQ_FPE_PARAMS)

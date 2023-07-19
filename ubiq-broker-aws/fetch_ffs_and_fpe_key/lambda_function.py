import logging
import requests
import json
from common import (
    http_auth,
    format_error_response,
    unpack_request,
    validate_access_key,
    validate_signing_key,
    parse_ubiq_response,
    UBIQ_API_URL
)

def lambda_handler(event, context):
    logging.info("Received request to fetch Field Format Specification (FFS) and Format Preserving Encryption (FPE) key")

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
    ffs_name_list = []

    # Extract FFS name, access key ID and secret signing key and query Ubiq API
    for idx, ffs_names, access_key, signing_key in rows:

        logging.info(f"Processing row [{idx}] of fetch FPE key request")

        # Validate FFS name
        if not isinstance(ffs_names, str):
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

        try:
            # Call Ubiq API to get the FPE key
            ubiq_response = requests.get(
                url=f"{UBIQ_API_URL}/fpe/def_keys?ffs_name={ffs_names}&papi={access_key}",
                auth=http_auth(access_key, signing_key),
            )
        except Exception as e:
            msg = "An exception occurred while calling Ubiq FPE API endpoint"
            logging.exception(msg)
            return format_error_response(msg)

        try:
            # Parse contents of Ubiq FPE API response
            contents = parse_ubiq_response(ubiq_response, ffs_names.split(','))
        except Exception as e:
            logging.exception(e)
            return format_error_response(str(e))

        response_contents.append(contents)
    logging.info("Request to fetch FPE encryption key successful")

    return {
        "data": [
            [0,response_contents[0]]
        ]
    }

import logging
import azure.functions as func
import requests
import json
from common.redis_handler import redis_client
from common import (
    http_auth,
    format_response,
    format_error_response,
    unpack_request,
    validate_access_key,
    validate_signing_key,
    parse_ubiq_response,
    UBIQ_API_URL
)

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Received request to fetch dataset and structured encryption key")

    try:
        req_body = req.get_json()
    except Exception as e:
        msg = "An exception occurred while parsing request body contents as JSON"
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
    dataset_name_list = []

    # Extract dataset name, access key ID and secret signing key and query Ubiq API
    for idx, dataset_names, access_key, signing_key in rows:

        logging.info(f"Processing row [{idx}] of fetch key request")

        # Validate dataset name
        if not isinstance(dataset_names, str):
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

        try:
            # Call Ubiq API to get the key
            ubiq_response = requests.get(
                url=f"{UBIQ_API_URL}/fpe/def_keys?dataset_name={dataset_names}&papi={access_key}",
                auth=http_auth(access_key, signing_key),
            )
        except Exception as e:
            msg = "An exception occurred while calling Ubiq Structured Encryption Key API endpoint"
            logging.exception(msg)
            return func.HttpResponse(format_error_response(msg), status_code=500)

        try:
            # Parse contents of Ubiq API response
            contents = parse_ubiq_response(ubiq_response, dataset_names.split(','))
        except Exception as e:
            logging.exception(e)
            return func.HttpResponse(format_error_response(str(e)), status_code=500)

        response_contents.append(contents)
    logging.info("Request to fetch encryption key successful")

    # Transmit HTTP response with Ubiq-supplied parameters
    # NOTE: Snowflake only recognizes status code 200 as a success indicator
    return func.HttpResponse(
        json.dumps({"data": [[0,response_contents[0]]]}),
        status_code=200,
    )

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
    logging.info("Received request to fetch datasets and structured keys")

    try:
        if(isinstance(event,list) or isinstance(event, dict)):
            if 'body' in event:
                # Snowflake sends a request with the body stringified
                req_body = json.loads(event['body'])
            else:
                # API Gateway doesn't send the full request as the event
                req_body = event
        else:
            json_event = json.loads(event)
            req_body = json_event['body']
    except Exception as e:
        msg = "An exception occurred while parsing request body contents as JSON"
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
    dataset_name_list = []

    # Extract dataset name, access key ID and secret signing key and query Ubiq API
    for idx, dataset_names, access_key, signing_key in rows:

        logging.info(f"Processing row [{idx}] of fetch key request")

        # Validate dataset name
        if not isinstance(dataset_names, str):
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
            # Call Ubiq API to get the key
            ubiq_response = requests.get(
                url=f"{UBIQ_API_URL}/fpe/def_keys?ffs_name={dataset_names}&papi={access_key}",
                auth=http_auth(access_key, signing_key),
            )
        except Exception as e:
            msg = "An exception occurred while calling Ubiq API endpoint"
            logging.exception(msg)
            return format_error_response(msg)

        try:
            # Parse contents of Ubiq API response
            contents = parse_ubiq_response(ubiq_response, dataset_names.split(','))
        except Exception as e:
            logging.exception(e)
            return format_error_response(str(e))

        response_contents.append(contents)
    logging.info("Request to fetch encryption key successful")

    return {
        "statusCode": 200, 
        "body": json.dumps({"data": [[0, response_contents[0]]]})
        }

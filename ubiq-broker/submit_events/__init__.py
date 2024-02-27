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
    UBIQ_API_URL,
)

UBIQ_API_URL = 'https://api.ubiqsecurity.com/api/v3'

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Received request to submit event data")

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

    # Extract Events, access key ID and secret signing key and query Ubiq API
    for idx, events, access_key, signing_key in rows:
        usage = []
        for event in events:
            logging.info(f"Processing row [{idx}] of event data")
            usage.append(
                {
                    "api_key": access_key,
                    "count": event['executionCount'],
                    "product": "ubiq-snowflake",
                    "product_version": "0.1.0",
                    "user_agent": "ubiq-snowflake/0.1.0",
                    "api_version": "v3",
                    "first_call_timestamp": event['start_time'],
                    "last_call_timestamp": event['end_time'],
                    "metadata": {
                        "query_id": event['query_id'],
                        "python_execution_time": event['executionTime'],
                        "warehouse_size": event['warehouse_size']
                    }
                }
            )

        # Validate access key and signing key format
        try:
            validate_access_key(access_key)
            validate_signing_key(signing_key)
        except AttributeError as e:
            logging.exception(e)
            return func.HttpResponse(format_error_response(str(e)), status_code=400)

        data = json.dumps({
                    "usage": usage
                }).encode('utf-8')
        try:
            logging.info(f"Sending event data to ubiq")
            # Call Ubiq API to get the key
            ubiq_response = requests.post(
                url=f"{UBIQ_API_URL}/tracking/events",
                auth=http_auth(access_key, signing_key),
                headers={'Content-Type': 'application/json'},
                data=data
            )
        except Exception as e:
            msg = f"An exception occurred while calling Ubiq API endpoint. {str(e)} -- Data Sent {data}"
            logging.exception(msg)
            return func.HttpResponse(format_error_response(msg), status_code=500)
            

    logging.info("Events reported successfully")

    # Transmit HTTP response with Ubiq-supplied parameters
    # NOTE: Snowflake only recognizes status code 200 as a success indicator
    return func.HttpResponse(
        json.dumps({"data": [[0,"Success"]]}),
        status_code=200,
    )

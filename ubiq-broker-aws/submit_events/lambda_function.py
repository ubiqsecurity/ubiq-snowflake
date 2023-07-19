import logging
import requests
import json
from common import (
    http_auth,
    format_error_response,
    unpack_request,
    validate_access_key,
    validate_signing_key,
    UBIQ_API_URL,
)

def lambda_handler(event, context):
    logging.info("Received request to submit event data")

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
            return format_error_response(str(e))

        data = json.dumps({
                    "usage": usage
                }).encode('utf-8')
        try:
            logging.info(f"Sending event data to ubiq")
            # Call Ubiq API to get the FPE key
            ubiq_response = requests.post(
                url=f"{UBIQ_API_URL}/tracking/events",
                auth=http_auth(access_key, signing_key),
                headers={'Content-Type': 'application/json'},
                data=data
            )
        except Exception as e:
            msg = f"An exception occurred while calling Ubiq FPE API endpoint. {str(e)} -- Data Sent {data}"
            logging.exception(msg)
            return format_error_response(msg)
            

    logging.info("Events reported successfully")

    # Transmit HTTP response with Ubiq-supplied FPE parameters
    # NOTE: Snowflake only recognizes status code 200 as a success indicator
    return {"data": [[0,"Success"]]}

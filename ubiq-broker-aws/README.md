# Ubiq API - Snowflake Broker
This repository contains the BETA version Ubiq broker function definition. The Ubiq broker performs the following functions:

1. Consumes REST request from Snowflake data platform
2. Converts them to a format expected by the intended Ubiq API and queries the applicable Ubiq API
3. Parses the Ubiq API response and returns the data in an array format consumable by Snowflake

The broker consists of the following endpoints:

* _fetch_key:_ Consumes an access key ID and secret signing key and retrieves a new encrypted private key from the Ubiq API
* _fetch_key_from_data:_ Consumes an access key ID, secret signing key and hex-encrypted data and retrieves the corresponding encrypted private key from the Ubiq API (this is useed during decrypt operations)
* _fetch_ffs_and_fpe_key: Consumes an access key ID, secret signing key and field format specification (FFS) and retrieves the corresponding metadata and encrypted private keys from the Ubiq API

## AWS (Lambda) Function Deployment and Configuration
Execute the following steps to deploy the Ubiq broker function to AWS. (To be performed by a UBIQ Employee)

1. Ensure there is a IAM role for Lambda Execution. Create one if needed. Save the arn (arn:aws:iam:....)
2. Run `sh create_functions.sh`, it will create and set up the functions on Lambda.
3. Follow the remaning steps as shown in [Snowflake's documentation](https://docs.snowflake.com/en/sql-reference/external-functions-creating-aws-ui-proxy-service). This will mean creating an API gateway, assigning resources/methods to the lambda functions created by the script, and then end users can continue with the rest of the steps as noted below. 

### To Deploy Update

Run `sh create_functions.sh`. This will grab the latest code and upload it to lambda. No changes to API Gateway should be required.

### Requirements
- Python 3.10
- Visual Studio Code 


## Snowflake Configuration

1. In a Snowflake worksheet, run the below command to create an AWS integration service. The IDs are obtained in the following manner:
    * _api_aws_role_arn:_ This is a new role created for use with the broker functions. Ubiq Employee will follow the steps listed on this [Snowflake page](https://docs.snowflake.com/en/sql-reference/external-functions-creating-aws-ui-proxy-service#create-a-new-iam-role-in-your-aws-account) and provide you with it upon request.
    * _api_allowed_prefixes:_ This is the URL provided by API Gateway service. Click _Stages_, select the appropriate stage, then this will be _Invoke URL_ at the top of the page.

NOTE that the owner/administrator of the AWS account where the API Gateway is being hosted will need to grant execute:invoke for the snowflake ID provided.

```
create or replace api integration ubiq_broker_aws
    api_provider=aws_api_gateway
    api_aws_role_arn='...'
    api_allowed_prefixes=('{Gateway URL}')
    enabled=true;
```

2. In a Snowflake worksheet, run the below command

```
describe api integration ubiq_broker_int;
```

Look for the property named API_AWS_IAM_USER_ARN and API_AWS_EXTERNAL_ID. Provide these to Ubiq. These will be aded to the previously mentioned Role's trust policy to grant your instance permissions to call the broker functions.

3. In a Snowflake worksheet, run the below commands to create external functions corresponding to the Ubiq broker endpoints.  The Ubiq Broker Base API URL can be found by visiting API Gateway service. Click _Stages_, select the appropriate stage, then this will be _Invoke URL_ at the top of the page.

```
create or replace external function _ubiq_broker_fetch_key(access_key_id varchar, secret_signing_key varchar)
    returns variant
    api_integration = ubiq_broker_int
    as '[Ubiq broker base URL]/fetch_key';
create or replace external function _ubiq_broker_fetch_key_from_data(encrypted_data binary, access_key_id varchar, secret_signing_key varchar)
    returns variant
    api_integration = ubiq_broker_int
    as '[Ubiq broker base URL]/fetch_key_from_data';
create or replace external function _ubiq_broker_fetch_ffs_and_fpe_key(ffs_name varchar, access_key_id varchar, secret_signing_key varchar)
    returns variant
    api_integration = ubiq_broker_int
    as '[Ubiq broker base URL]/fetch_ffs_and_fpe_key';
create or replace external function _ubiq_broker_submit_events(events variant, access_key_id varchar, secret_signing_key varchar)
    returns variant
    api_integration = ubiq_broker_int
    as '[Ubiq broker base URL]/submit_events';

```

### If the default wrapper functions are to be used:

1. Run the instructions in https://gitlab.com/ubiqsecurity/ubiq-snowflake/-/tree/master/ubiq-udf to create the Python UDFs

2. Create a credential table with

```
create or replace TABLE UBIQ_CREDS (
    ACCESS_KEY_ID VARCHAR(24),
    SECRET_SIGNING_KEY VARCHAR(44),
    SECRET_CRYPTO_ACCESS_KEY VARCHAR(44)
);
```

3. Insert a row to the `UBIQ_CREDS` table with the API keys that will be used for encrypt/decrypt

4. Create the functions described in `./ubiq_functions.sql` to create wrapper UDFs to the broker and API UDFs.  Update the default database/schema in the CREATEs as necessary

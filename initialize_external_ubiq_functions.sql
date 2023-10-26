-- Create the Broker Integration

-- AZURE VERSION
create or replace api integration ubiq_broker_int
    api_provider = azure_api_management
    azure_tenant_id = '089e0dc6-e4fd-4306-b4eb-f0d412949167'
    azure_ad_application_id = '9ace26c4-c2db-4556-994a-36d869c63194'
    api_allowed_prefixes = ('https://ubiq-api-broker.azure-api.net/ubiq-api-broker')
    enabled = true;

-- AWS VERSION
create or replace api integration ubiq_broker_int
    api_provider=aws_api_gateway
    api_aws_role_arn='arn:aws:iam::109850196672:role/SnowflakeCustomerUser_Role'
    api_allowed_prefixes=('https://x02qdux9x9.execute-api.us-west-2.amazonaws.com/Production')
    enabled=true;

-- In a Snowflake worksheet, run the below command, 
-- AZURE: Click on the URL within the _AZURE\_CONSENT\_URL_ field, and click _Accept_ to grant Snowflake access to the Azure tenancy.
-- AWS: Provide API_AWS_IAM_USER_ARN and API_AWS_EXTERNAL_ID to Ubiq. These will be needed to grant you access.
describe api integration ubiq_broker_int;

-- Create the external functions
-- Ubiq Broker Base URL
-- AZURE VERSION
create or replace external function _ubiq_broker_fetch_key(access_key_id varchar, secret_signing_key varchar)
    returns variant
    api_integration = ubiq_broker_int
    as 'https://ubiq-api-broker.azure-api.net/ubiq-api-broker/fetch_key';
create or replace external function _ubiq_broker_fetch_ffs_and_fpe_key(ffs_name varchar, access_key_id varchar, secret_signing_key varchar)
    returns variant
    api_integration = ubiq_broker_int
    as 'https://ubiq-api-broker.azure-api.net/ubiq-api-broker/fetch_ffs_and_fpe_key';
create or replace external function _ubiq_broker_submit_events(events variant, access_key_id varchar, secret_signing_key varchar)
    returns variant
    api_integration = ubiq_broker_int
    as 'https://ubiq-api-broker.azure-api.net/ubiq-api-broker/submit_events';

-- AWS VERSION
create or replace external function _ubiq_broker_fetch_key(access_key_id varchar, secret_signing_key varchar)
    returns variant
    api_integration = ubiq_broker_int
    as 'https://x02qdux9x9.execute-api.us-west-2.amazonaws.com/Production/fetch_key';
create or replace external function _ubiq_broker_fetch_ffs_and_fpe_key(ffs_name varchar, access_key_id varchar, secret_signing_key varchar)
    returns variant
    api_integration = ubiq_broker_int
    as 'https://x02qdux9x9.execute-api.us-west-2.amazonaws.com/Production/fetch_ffs_and_fpe_key';
create or replace external function _ubiq_broker_submit_events(events variant, access_key_id varchar, secret_signing_key varchar)
    returns variant
    api_integration = ubiq_broker_int
    as 'https://x02qdux9x9.execute-api.us-west-2.amazonaws.com/Production/submit_events';
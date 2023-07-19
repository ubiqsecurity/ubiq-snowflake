-- Create the Broker Integration

-- AZURE VERSION
-- Get tenant id, application id, and prefixes from Ubiq
create or replace api integration ubiq_broker_int
    api_provider = azure_api_management
    azure_tenant_id = '...'
    azure_ad_application_id = '...'
    api_allowed_prefixes = ('{Gateway URL}')
    enabled = true;

-- AWS VERSION
-- Get api_aws_role_arn and api_allowed_prefixes from Ubiq
create or replace api integration ubiq_broker_int
    api_provider=aws_api_gateway
    api_aws_role_arn='...'
    api_allowed_prefixes=('{Gateway URL}')
    enabled=true;

-- In a Snowflake worksheet, run the below command, 
-- AZURE: Click on the URL within the _AZURE\_CONSENT\_URL_ field, and click _Accept_ to grant Snowflake access to the Azure tenancy.
-- AWS: Provide API_AWS_IAM_USER_ARN and API_AWS_EXTERNAL_ID to Ubiq. These will be needed to grant you access.
describe api integration ubiq_broker_int;

-- Create the external functions
create or replace external function _ubiq_broker_fetch_key(access_key_id varchar, secret_signing_key varchar)
    returns variant
    api_integration = ubiq_broker_int
    as '[Ubiq broker base URL]/fetch_key';
create or replace external function _ubiq_broker_fetch_key_from_data(encrypted_data binary, access_key_id varchar, secret_signing_key varchar)
    returns variant
    api_integration = ubiq_broker_int
    as '[Ubiq broker base URL]/fetch_key_from_data';
create or replace external function _ubiq_broker_fetch_ffs(ffs_name varchar, access_key_id varchar, secret_signing_key varchar)
    returns variant
    api_integration = ubiq_broker_int
    as '[Ubiq broker base URL]/fetch_ffs';
create or replace external function _ubiq_broker_fetch_fpe_key(ffs_name varchar, access_key_id varchar, secret_signing_key varchar)
    returns variant
    api_integration = ubiq_broker_int
    as '[Ubiq broker base URL]/fetch_fpe_key';
create or replace external function _ubiq_broker_fetch_ffs_and_fpe_key(ffs_name varchar, access_key_id varchar, secret_signing_key varchar)
    returns variant
    api_integration = ubiq_broker_int
    as '[Ubiq broker base URL]/fetch_ffs_and_fpe_key';
create or replace external function _ubiq_broker_submit_events(events variant, access_key_id varchar, secret_signing_key varchar)
    returns variant
    api_integration = ubiq_broker_int
    as '[Ubiq broker base URL]/submit_events';
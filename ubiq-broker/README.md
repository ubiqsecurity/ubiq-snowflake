# Ubiq API - Snowflake Broker (BETA)
This repository contains the BETA version Ubiq broker function definition. The Ubiq broker performs the following functions:

1. Consumes REST request from Snowflake data platform
2. Converts them to a format expected by the intended Ubiq API and queries the applicable Ubiq API
3. Parses the Ubiq API response and returns the data in an array format consumable by Snowflake

The broker consists of the following endpoints:

* _fetch_key:_ Consumes an access key ID and secret signing key and retrieves a new encrypted private key from the Ubiq API
* _fetch_key_from_data:_ Consumes an access key ID, secret signing key and hex-encrypted data and retrieves the corresponding encrypted private key from the Ubiq API (this is useed during decrypt operations)
* _fetch_ffs:_ Consumes an access key ID, secret signing key and field format specification (FFS) and retrieves the corresponding FFS metadata from the Ubiq API
* _fetch_fpe_key:_ Consumes an access key ID, secret signing key and field format specification (FFS) and retrieves the corresponding encrypted private key from the Ubiq API

The Ubiq broker also supports caching of previously-retrieved encrypted private keys in an Azure-managed Redis cache.

## Azure Redis Deployment
Execute the following steps to provision a managed Redis instance within Azure.

1. Within the Azure Portal, click _Create a resource_, select _Databases_ and click _Azure Cache for Redis_

2. On the _Azure Cache for Redis_ page, click _Create_

3. On the _New Redis Cache_ page, select the desired resource group, enter the desired DNS name, and select the _Basic C0_ cache type

4. Click the _Review + create_ button

## Azure Function Deployment and Configuration
Execute the following steps to deploy the Ubiq broker function to Azure.

1. Install the required packages by running the following command from the top-level of the ubiq-broker project directory:
```
pip install -r requirements.txt
```

2. In VSCode, click on the Azure extension [icon](https://learn.microsoft.com/en-us/azure/includes/media/functions-publish-project-vscode/functions-vscode-deploy.png) and sign into Azure

3. Under the _Workspace_ sidebar menu, click the _Deploy_ button (middle button on the top-right of the workspace box)

4. Within the Azure Portal, click _Create a resource_, select _Web_, and click the _Create_ link under _API Management_

5. On the _Install API Management gateway_ page, select the desired resource group, region and resource name and click _Review + create_

6. On the _Overview_ page of the newly-created Azure API Management service, click _APIs_ (left sidebar)

7. Select _Add API_ and click _Function App_ (under _Create from Azure resource_)

8. Click _Browse_ to select the Ubiq broker API function and click _Create_

9. On the Ubiq broker API function page, click the _Settings_ button (top menu) and under _Subscription_, uncheck _Subscription required_

### To Deploy Update


If you would like to create a revision to deploy to

1. For the endpoint/function that is currently deployed, click the ellipsis (...) and click _Add revision_

2. Provide some reviewsion/versioning notes

3. To set it live, on the reveison just published, click the ellipsis (...) and click _Make current_


To use the new function updates/methods

1. Under the _Functions_ sidebar menu, click the _Deploy_ button (middle button on the top-right of the workspace box)

2. Select the local project name `ubiq-snowflake`

3. Enter the name of the pre-existing Function that was deployed (VS will prompt that it can be overwritten)

4. In Azure _API Management services_, navigate to the _APIs_ page

5. For the endpoint/function that is currently deployed, click the ellipsis (...) and click _Import_

6. Select the newly-deployed function, the methods you would like to update



### Requirements
- Python 3.8
- Visual Studio Code 
- Azure Functions VSCode extension (ms-azuretools.vscode-azurefunctions)


## Snowflake Configuration

1. In a Snowflake worksheet, run the below command to create an Azure integration service. The IDs are obtained in the following manner:
    * _azure_tenant_id:_ On the Azure Portal home page, go to _All services_, find and click _Azure Active Directory_ and copy _Tenant ID_
    * _azure_ad_application_id:_ On the Azure Portal home page, go to _All services_, find and click on _Azure Active Directory_, click _App registrations_ (left menubar), and copy the _Application (client) ID_
    * _api_allowed_prefixes:_ On the Azure Portal home page, go to _All services_, find and click on _API Management services_, click on the Ubiq API management service, and copy the _Gateway URL_ address

NOTE that the owner/administrator of the Azure account where the API Gateway is being hosted will need to follow the consent link that is generated in this step in order to  provide usage consent.

```
create or replace api integration ubiq_broker_int
    api_provider = azure_api_management
    azure_tenant_id = '...'
    azure_ad_application_id = '...'
    api_allowed_prefixes = ('{Gateway URL}')
    enabled = true;
```

2. In a Snowflake worksheet, run the below command, click onc the URL within the _AZURE\_CONSENT\_URL_ field, and click _Accept_ to grant Snowflake access to the Azure tenancy

```
describe api integration ubiq_broker_int;
```

3. In a Snowflake worksheet, run the below commands to create external functions corresponding to the Ubiq broker endpoints. To obtain the Ubiq broker base URL, go to _All services_ within the Azure portal, find and click on _API Management services_, click _APIs_ and select the Ubiq broker API, click _Settings_ (top menubar) and copy the value of _Base URL_

```
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

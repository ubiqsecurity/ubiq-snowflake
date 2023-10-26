# Ubiq Encryption in Snowflake
The Ubiq Security Snowflake library provides a convenient interaction with the Ubiq Security Platform API from applications written to interact with the [Snowflake](https://www.snowflake.com/) Data Cloud. Included is a pre-defined set of functions and classes that will provide a simple interface to encrypt and decrypt data.

This repository contains Snowflake user-defined functions (UDFs) that wrap the Ubiq Python library to enable UDF-based encryption and decryption operations within Snowflake data platform. UDFs are defined and deployed using the Snowpark library, a Snowflake client API for interacting with Snowflake and defining/deploying Snowflake objects.

> **Note**: The Snowflake library is currently only supported for Azure- and AWS-hosted Snowflake environments.  If you are running Snowflake on GCP, please contact [Ubiq Support](mailto:support@ubiqsecurity.com).

## Configuration
### Previous Versions
If older versions of the Ubiq UDFs exist on snowflake, remove them with the following SQL queries:
```sql
-- Know your stage name! deploy_udfs.py uses `ubiq_package_stage`.
LIST @ubiq_package_stage PATTERN='.*ubiq.zip';
-- Once you are ready, either use this
REMOVE @ubiq_package_stage PATTERN='.*ubiq.zip';
-- Or specify individually with the NAME column, eg:
REMOVE @ubiq_package_stage/80661511034a408d96f01ae595b99e6e3251e59feebc8833442c303ba5a9cade/ubiq.zip;
```
Snowflake will keep older versions around and it is hard to tell which version of the `ubiq.zip` it will ultimately be using. Cleaning up old versions can help eliminate this obscurity.

### Dependencies

#### Requirements
- Python 3.8

#### Packages 
Install the required packages by running the following command from the top-level of the ubiq-udf project directory:
```
pip install -r requirements.txt
```

Ensure Anaconda packages have been enabled in Snowflake per https://docs.snowflake.com/en/developer-guide/udf/python/udf-python-packages.html#using-third-party-packages-from-anaconda

### Deployment
#### Python

To deploy the Snowflake Ubiq UDFs, run the following command (replace "\\" with "^" if running on Windows):
```shell
python deploy_udfs.py \
    --account="..." \
    --user="..." \
    --password="..." \
    --warehouse="..." \
    --database="..." \
    --schema="..."
```

Arguments are defined as follows:
* _account:_ snowflake account name (excluding https:// prefix)
* _user:_ snowflake username
* _password:_ snowflake password
* _warehouse:_ name of the Snowflake warehouse
* _database:_ name of the Snowflake database in which to create Ubiq UDFs
* _schema:_ name of the schema in which to create Ubiq UDFs

Below is an example invocation of the UDF deployment script using dummy values(replace "\\" with "^" if running on Windows):
```shell
python deploy_udfs.py \
    --account=pozvoni-dt53742 \
    --user=testuser \
    --password=testpassword \
    --warehouse=COMPUTE_WH \
    --database=UBIQ_SANDBOX \
    --schema=UBIQ
```

If the user has multiple roles, you will need to adjust the `deployment.py` to include a role as appropriate

#### Snowflake (SQL)

You will need to run all of the statements listed in both [`initialize_ubiq_external_functions.sql`](/initialize_external_ubiq_functions.sql) and [`ubiq_functions.sql`](/ubiq_functions.sql).

> **Note**: For **Azure-hosted** Snowflake environments, a mutual consent between Azure and your Snowflake tenant needs to be granted.  Please contact [Ubiq Support](mailto:support@ubiqsecurity.com) to provide environmental information to produce the consent link and to grant Azure consent.
>
>Ubiq will provide you with a tenant id, application id, and broker URL to use during set up.

> **Note**: For **AWS-hosted** Snowflake environments, a mutual consent between AWS  and your Snowflake tenant needs to be granted.  Please contact [Ubiq Support](mailto:support@ubiqsecurity.com) to provide environmental information.
>
>Ubiq will provide you with a `api_aws_role_arn` and broker URL to use during setup. You will need to provide the `API_AWS_IAM_USER_ARN` and `API_AWS_EXTERNAL_ID`` given by Snowflake to be authorized to use the external (broker) functions.

[`initialize_ubiq_external_functions.sql`](/initialize_external_ubiq_functions.sql)  - Creates the external (broker) functions needed for Snowflake to communicate with Ubiq. These perform the following functions:

1. Consumes REST request from Snowflake data platform
2. Converts them to a format expected by the intended Ubiq API and queries the applicable Ubiq API
3. Parses the Ubiq API response and returns the data in an array format consumable by Snowflake

[`ubiq_functions.sql`](/ubiq_functions.sql) - Defines the functions for interacting with the Ubiq encryption service. Ties the user defined functions to aliases that ensure consistent usage of the platform and handle communication with credentials stored in the current session.

## Credentials
The Client Library needs to be configured with your API Key Credentials which are available in the Ubiq Dashboard when you [create a Dataset](https://dev.ubiqsecurity.com/docs/create-datasets). Credentials will be used when setting up the environment to use the Ubiq functions.

> **In a production deployment, it is critical to maintain the secrecy of Ubiq API Key Credentials (SECRET_CRYPTO_ACCESS_KEY and SECRET_SIGNING_KEY) and API tokens (ACCESS_KEY_ID).**
>
>These items SHOULD be stored in a secrets management server or password vault. They should NOT be stored in a standard data file, embedded in source code, committed to a source code repository, or insecurely used in environmental variables.

## Usage
All Ubiq functions take as input the Ubiq secret crypto access key and the encrypted private key, along with other attributes returned from the respective Ubiq API endpoint. Encrypt functions expect plain text while decrypt functions expect encrypted data, which is binary data for standard decryption or cipher text for Format Preserving Encryption (FPE) decryption.  Additionally, FPE functions expect the Dataset names. Examples of each encrypt/decrypt UDF is provided below.

### Format Preserving Encryption (FPE) Setup
Before running encryption/decryption operations, the database session will need to be initialized. This is done by calling the following procedure:
```sql
CALL ubiq_begin_session(
    dataset_names, 
    access_key,
    secret_signing_key,
    secret_crypto_access_key
)
```

Arguments are defined as follows:
* _dataset_names:_ The datasets to use FPE encryption with. Datasets should be accessible by the API Key. These should be in a single string, separated by commas. eg `'SSN,TELEPHONE_NUMBER,FULL_NAME'` 
* _access_key, secret_signing_key, secret_crypto_access_key:_ Ubiq API Key Credentials available from the Ubiq Dashboard

### FPE Encryption
The below command performs FPE encryption by calling the Ubiq API to get Dataset metadata corresponding to the given Dataset name (e.g., 'SSN') and an FPE encryption key.
```sql
select ubiq_encrypt(
    plain_text, 
    dataset_name
)
from table
```

### FPE Decryption
The below command performs FPE decryption by calling the Ubiq API to get Dataset metadata corresponding to the given Dataset name (e.g., 'SSN') and an FPE encryption key. 
```sql
select ubiq_decrypt(
    cipher_text, 
    dataset_name
)
from table
```

### FPE Encrypt for Search
Encrypt For Search is a function set provided to search your database for a value that has been encrypted.

#### Example
There are two available functions:
1. `ubiq_encrypt_for_search_array(plain_text varchar, ffs_name varchar)` - Returns an array representation, eg `['cipher text 1', 'cipher text 2', ...]`
1. `ubiq_encrypt_for_search_table(plain_text varchar, ffs_name varchar)` - Returns a table representation with 1 column, `cipher_text`, where each row contains a separate cipher text. This is a **table function** and should be prefixed with `table()` when used in FROM and WHERE clauses.

This gives you flexibility when searching to build the query that best suits your situation.


###### Sql IN statement
```sql
SELECT * 
FROM user_data 
WHERE encrypted_data IN (
    SELECT * 
    FROM table(ubiq_encrypt_for_search_table(
        'hello world', 
        'UTF8_STRING_COMPLEX'
        )
    )
);
```
IN statements require a list of values or a subquery. An array will not work in this situation.

##### Sql JOIN statement
```sql
SELECT * 
FROM user_data s 
JOIN (
    SELECT * 
    FROM table(ubiq_encrypt_for_search_table(
        'hello world', 
        'UTF8_STRING_COMPLEX'
        )
    )
) t ON s.encrypted_data = t.cipher_text;
```

##### Snowflake Sql ARRAY_CONTAINS statement
```sql
SELECT * 
from user_data 
WHERE 
  ARRAY_CONTAINS (
    encrypted_data :: variant, 
    (SELECT ubiq_encrypt_for_search_array(
        'hello world', 
        'UTF8_STRING_COMPLEX'
    ))
  );

```

`ARRAY_CONTAINS` takes two arguments, `(VARIANT, ARRAY)`. Casting the encrypted data to a variant makes this work.

### Ending the Ubiq Session
After encrypting/decrypting, you will need to call this function. This will guarantee the environment has been cleaned up and report usage information.
```sql
call ubiq_close_session(
    access_key, 
    secret_signing_key
)
```

## Usage Example for High Volume-use Format Preserving Encryption

```sql
----------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------
-- sample encrypt/decrypt using format-preserving encryption of an SSN for high volume
--
-- this assumes that you
--      1) have credentials with access to a structured dataset called "SSN"
--      2) that the structured dataset called "SSN" has an input character set of [0-9]
--         and an output character set of [0-9a-zA-Z] and passthrough character of 
--         at least a dash [-]
--
-- this example pre-caches configuration and keys that will be used in the subsequent
-- encrypt/decrypt events to maximize performance for large datasets
----------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------


-- warm up configuration and key cache
call ubiq_begin_session('SSN', access_key, secret_signing_key, secret_crypto_access_key);

select * from sample_ssns

-- update column in table
update sample_ssns set ssn_encrypted = ubiq_encrypt(ssn_plaintext, 'SSN');
update sample_ssns set ssn_decrypted = ubiq_decrypt(ssn_encrypted, 'SSN');

-- query data from table
select id, ubiq_decrypt(ssn_encrypted, 'SSN') from sample_ssns;

call ubiq_close_session(access_key, secret_signing_key);
```

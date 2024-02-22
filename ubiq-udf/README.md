# Ubiq Encryption in Snowflake (BETA)
This repository contains BETA version snowflake user-defined functions (UDFs) that wrap the Ubiq Python library to enable UDF-based encryption and decryption operations within [Snowflake](https://www.snowflake.com/) data platform. UDFs are defined and deployed using the [Snowpark](https://www.snowflake.com/snowpark/) library, a Snowflake client API for interacting with Snowflake and defining/deploying Snowflake objects.

## Configuration
### Dependencies
Install the required packages by running the following command from the top-level of the ubiq-udf project directory:
```
pip install -r requirements.txt
```

Ensure Anaconda packages have been enabled in Snowflake per https://docs.snowflake.com/en/developer-guide/udf/python/udf-python-packages.html#using-third-party-packages-from-anaconda

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

### Deployment
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

### Requirements
- Python 3.8

## Usage
All Ubiq functions take as input the Ubiq secret crypto access key and the encrypted private key, along with other attributes returned from the respective Ubiq API endpoint. Encrypt functions expect plain text while decrypt functions expect encrypted data, which is binary data for standard decryption or cipher text for structured decryption.  Additionally, structured encryption functions expect the Dataset names. Examples of each encrypt/decrypt UDF is provided below. They assume that functions were created in the "ubiq" schema and are executing within the context of the database to which the UDFs were deployed.

### structured Setup
Before running encryption/decryption operations, the database session will need to be initialized. This is done by calling the following procedure:
```sql
CALL ubiq.ubiq_begin_session(
    dataset_names, 
    access_key,
    secret_signing_key,
    secret_crypto_access_key
)
```

Arguments are defined as follows:
* _dataset_names:_ The datasets to use structured encryption with. Datasets should be accessible by the API Key. These should be in a single string, separated by commas. eg `'SSN,TELEPHONE_NUMBER,FULL_NAME'` 
* _access_key, secret_signing_key, secret_crypto_access_key:_ Ubiq API Key Credentials available from the Ubiq Dashboard

### Structured Encryption
The below command performs structured encryption by calling the Ubiq API to get Dataset metadata corresponding to the given Dataset name (e.g., 'SSN') and an encryption key.
```sql
select ubiq.ubiq_encrypt(
    plain_text, 
    dataset_name
)
from table
```

The below command calls the encryption function directly; it expects that the encryption key and Dataset metadata are cached locally and provided as arguments to the function.
```sql
select ubiq._ubiq_encrypt(    
    plain_text,
    'secret crypto access key',
    {
        'name': 'SSN'
        'encryption_algorithm': '...',
        'passthrough': '...',
        'input_character_set': '...',
        'output_character_set': '...',
        'msb_encoding_bits': '...',
        'tweak': '...',
        'tweak_min_len': '...',
        'tweak_max_len': '...'
    },
    {
        'encrypted_private_key': '...',
        'wrapped_data_key': '...',
        'key_number': 0
    }
)
from table
```

### Structured Decryption
The below command performs structured decryption by calling the Ubiq API to get Dataset metadata corresponding to the given Dataset name (e.g., 'SSN') and an encryption key. 
```sql
select ubiq.ubiq_decrypt(
    cipher_text, 
    dataset_name
)
from table
```

The below command calls the decryption function directly; it expects that the encryption key and Dataset metadata are cached locally and provided as arguments to the function.
```sql
select ubiq._ubiq_decrypt(
    cipher_text,
    'secret crypto access key',
    {
        'name': 'SSN'
        'encryption_algorithm': '...',
        'passthrough': '...',
        'input_character_set': '...',
        'output_character_set': '...',
        'msb_encoding_bits': '...',
        'tweak': '...',
        'tweak_min_len': '...',
        'tweak_max_len': '...'
    },
    {
        'encrypted_private_key': '...',
        'wrapped_data_key': '...',
        'key_number': 0
    }
)
from table
```

### Ending the Ubiq Session
After encrypting/decrypting, you will need to call this function. This will guarantee the environment has been cleaned up and report usage information.
```sql
call ubiq.ubiq_close_session(
    access_key, 
    secret_signing_key
)
```

## Usage Example for High Volume-use Format Preserving Encryption

```
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

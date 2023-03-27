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
```
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
```
python deploy_udfs.py \
    --account=pozvoni-dt53742 \
    --user=testuser \
    --password=testpassword \
    --warehouse=COMPUTE_WH \
    --database=UBIQ_SANDBOX \
    --schema=UBIQ
```

If the user has multiple roles, you will need to adjust the deployment .py to include a role as appropriate

### Requirements
- Python 3.8

## Usage
All Ubiq functions take as input the Ubiq secret crypto access key and the encrypted private key, along with other attributes returned from the respective Ubiq API endpoint. Encrypt functions expect plain text while decrypt functions expect encrypted data, which is binary data for standard decryption or cipher text for Format Preserving Encryption (FPE) decryption.  Additionally, FPE functions expect the Field Format Specification (FFS). Examples of each encrypt/decrypt UDF is provided below. They assume that functions were created in the "ubiq" schema and are executing within the context of the database to which the UDFs were deployed.

### Standard Encryption
The below command performs standard (i.e. non-FPE) encryption by calling the Ubiq API to get an encryption key. It assumes that the access key ID and secret signing key are stored in a table called ubiq_creds with column names access_key_id and secret_signing_key_id respectively.
```
select ubiq.ubiq_encrypt(
    plain_text
)
from table
```

The below command calls the Python encryption function directly; it expects that the encryption key is cached locally and provided as arguments to the function.
```
select ubiq._ubiq_python_encrypt(
    plain_text,
    'secret crypto access key',
    {
        'encrypted_private_key': '...',
        'key_fingerprint': '...',
        'encryption_session': '...',
        'security_model': '...',
        'max_uses': 1,
        'wrapped_data_key': '...',
        'encrypted_data_key': '...'
    }
)
from table
```

### Standard Decryption
The below command performs standard (i.e. non-FPE) decryption by calling the Ubiq API to get an encryption key. It assumes that the access key ID and secret signing key are stored in a table called ubiq_creds with column names access_key_id and secret_signing_key_id respectively.
```
select ubiq.ubiq_decrypt(
    encrypted_byte_array
)
from table
```

The below command calls the Python decryption function directly; it expects that the encryption key is cached locally and provided as arguments to the function.
```
select ubiq._ubiq_python_encrypt(
    encrypted_byte_array,
    'secret crypto access key',
    {
        'encrypted_private_key': '...',
        'key_fingerprint': '...',
        'encryption_session': '...',
        'wrapped_data_key': '...'
    }
)
from table
```

### FPE Encryption
The below command performs FPE encryption by calling the Ubiq API to get FFS metadata corresponding to the given FFS name (e.g., 'SSN') and an FPE encryption key. It assumes that the access key ID and secret signing key are stored in a table called ubiq_creds with column names access_key_id and secret_signing_key_id respectively.
```
select ubiq.ubiq_fpe_encrypt(
    plain_text, 
    ffs_name
)
from table
```

The below command calls the Python FPE encryption function directly; it expects that the encryption key and FFS metadata are cached locally and provided as arguments to the function.
```
select ubiq._ubiq_python_fpe_encrypt(    
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

### FPE Decryption
The below command performs FPE decryption by calling the Ubiq API to get FFS metadata corresponding to the given FFS name (e.g., 'SSN') and an FPE encryption key. It assumes that the access key ID and secret signing key are stored in a table called ubiq_creds with column names access_key_id and secret_signing_key_id respectively.
```
select ubiq.ubiq_fpe_decrypt(
    cipher_text, 
    ffs_name
)
from table
```

The below command calls the Python FPE decryption function directly; it expects that the encryption key and FFS metadata are cached locally and provided as arguments to the function.
```
select ubiq._ubiq_python_fpe_decrypt(
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

## Usage Example for single-use format preserving encryption

```
----------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------
-- sample encrypt/decrypt using format-preserving encryption of an SSN
--
-- this assumes that you
--      1) have credentials loaded in the ubiq_creds table
--      2) that those api credentials have access to a structured dataset called "SSN"
--      2) that the structured dataset called "SSN" has an input character set of [0-9]
--         and an output character set of [0-9a-zA-Z]
--
-- this example will not use any key caching between each query, so configuration
-- and data keys will be exchanged with the api backend during each encrypt
-- or decrypt udf call.  it will not perform well with large datasets
----------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------


-- encrypt a sample SSN
set plaintext = '041-04-1234';
set ciphertext = ubiq_fpe_encrypt($plaintext, 'SSN');

-- decrypt inline
select $plaintext, $ciphertext, ubiq_fpe_decrypt($ciphertext, 'SSN');
```


## Usage Example for valume-use format preserving encryption

```
----------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------
-- sample encrypt/decrypt using format-preserving encryption of an SSN for high volume
--
-- this assumes that you
--      1) have credentials loaded in the ubiq_creds table
--      2) that those api credentials have access to a structured dataset called "SSN"
--      2) that the structured dataset called "SSN" has an input character set of [0-9]
--         and an output character set of [0-9a-zA-Z] and passthrough character of 
--         at least a dash [-]
--
-- this example pre-caches configuration and keys that will be used in the subsequent
-- encrypt/decrypt events to maximize performance for large datasets
----------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------


-- warm up configuration and key cache
call ubiq_begin_fpe_session('SSN');

select * from sample_ssns

-- update column in table
update sample_ssns set ssn_encrypted = ubiq_fpe_encrypt_cache(ssn_plaintext, 'SSN');
update sample_ssns set ssn_decrypted = ubiq_fpe_decrypt_cache(ssn_encrypted, 'SSN');
```

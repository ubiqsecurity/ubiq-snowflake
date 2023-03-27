create or replace table ubiq_creds (
    access_key_id varchar(24),
    secret_signing_key varchar(44),
    secret_crypto_access_key varchar(44)
);

create or replace function ubiq_fpe_encrypt(plain_text varchar, ffs_name varchar)
returns varchar
as
$$
select _ubiq_python_fpe_encrypt(
    plain_text,
    (select secret_crypto_access_key from ubiq_creds),
    (select _ubiq_broker_fetch_ffs(ffs_name, (select access_key_id from ubiq_creds), (select secret_signing_key from ubiq_creds))),
    (select _ubiq_broker_fetch_fpe_key(ffs_name, (select access_key_id from ubiq_creds), (select secret_signing_key from ubiq_creds)))
)
$$;

create or replace function ubiq_fpe_decrypt(cipher_text varchar, ffs_name varchar)
returns varchar
as
$$
select _ubiq_python_fpe_decrypt(
    cipher_text,
    (select secret_crypto_access_key from ubiq_creds), 
    (select _ubiq_broker_fetch_ffs(ffs_name, (select access_key_id from ubiq_creds), (select secret_signing_key from ubiq_creds))),
    (select _ubiq_broker_fetch_fpe_key(ffs_name, (select access_key_id from ubiq_creds), (select secret_signing_key from ubiq_creds)))
)
$$;

create or replace function ubiq_get_encrypt_key("cache" object)
returns object
language javascript
as '
    for(const ffs_def in cache){
        cache[ffs_def].keys = [cache[ffs_def].keys[cache[ffs_def].current_key_number]]
    }
    
    return cache
';

create or replace temporary table ubiq_ffs_cache (cache object);

create or replace function ubiq_fpe_encrypt_cache("plain_text" varchar, "ffs_name" varchar)
returns varchar
language sql
as
$$
select _ubiq_python_fpe_encrypt_cache(
    plain_text,
    ffs_name,
    (select get_encrypt_key(cache) from ubiq_ffs_cache)
)
$$;

create or replace function ubiq_fpe_decrypt_cache("cipher_text" varchar, "ffs_name" varchar)
returns varchar
language sql
as
$$
select _ubiq_python_fpe_decrypt_cache(
    cipher_text,
    ffs_name,
    (select cache from ubiq_ffs_cache)
)
$$;

drop table ubiq_ffs_cache;

create or replace procedure ubiq_begin_fpe_session("ffs_names" varchar)
returns varchar
language javascript
execute as owner
as
$$
    var sql = `create or replace temporary table ubiq_ffs_cache (cache object) as 
    select _ubiq_broker_fetch_ffs_and_fpe_key( 
        '${ffs_names}', 
        (select access_key_id from ubiq_creds), 
        (select secret_signing_key from ubiq_creds)
    );`

    try {
        snowflake.execute({sqltext: sql});
        return "succeeded"
    }
    catch (err) {
        return "failed: " + err;
    }
$$;

-- Creates Cache without Reliance on Ubiq_creds table
-- Will still require keys to be unwrapped using above functions for use
CREATE OR REPLACE PROCEDURE UBIQ_BEGIN_FPE_SESSION("FFS_NAMES" VARCHAR(16777216), "ACCESS_KEY" VARCHAR(24), "SECRET_SIGNING_KEY" VARCHAR(44))
RETURNS VARCHAR(16777216)
LANGUAGE JAVASCRIPT
EXECUTE AS OWNER
AS
$$
    var sql = `create or replace temporary table ubiq_ffs_cache (cache object) as 
    SELECT _ubiq_broker_fetch_ffs_and_fpe_key( 
        '${FFS_NAMES}', 
        '${ACCESS_KEY}', 
        '${SECRET_SIGNING_KEY}'
    );`
    try {
        snowflake.execute({sqlText: sql});
        return "Succeeded"
    }
    catch (err) {
        return "Failed: " + err;
    }
$$;

-- Creates Cache with unwrapped keys; no Secret Crypto Key needed for enc/dec fpe cache functions.
CREATE OR REPLACE PROCEDURE UBIQ_BEGIN_FPE_SESSION("FFS_NAME" VARCHAR(16777216), "ACCESS_KEY" VARCHAR(24), "SECRET_SIGNING_KEY" VARCHAR(44), "SECRET_CRYPTO_ACCESS_KEY" VARCHAR(44))
RETURNS VARCHAR(16777216)
LANGUAGE JAVASCRIPT
AS
$$
    var sql = `create or replace temporary table ubiq_ffs_cache (cache object) as 
        select _ubiq_python_fetch_data_key(
            '${FFS_NAME}',
            '${SECRET_CRYPTO_ACCESS_KEY}',
            (select _ubiq_broker_fetch_ffs_and_fpe_key( 
                '${FFS_NAME}',
                '${ACCESS_KEY}', 
                '${SECRET_SIGNING_KEY}'
            ))
        );`
    try {
        snowflake.execute({sqlText: sql});
        return "Succeeded"
    }
    catch (err) {
        return "Failed: " + err;
    }
$$;
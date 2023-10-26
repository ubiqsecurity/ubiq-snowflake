create or replace table ubiq_creds (
    access_key_id varchar(24),
    secret_signing_key varchar(44),
    secret_crypto_access_key varchar(44)
);


create or replace function ubiq_get_encrypt_key("cache" object)
returns object
language javascript
as '
    for(const ffs_def in cache){
        cache[ffs_def].keys = [cache[ffs_def].keys[cache[ffs_def].current_key_number]];
        cache[ffs_def].current_key_only = true;
    }
    
    return cache
';

create or replace temporary table ubiq_ffs_cache (cache object);

create or replace function ubiq_encrypt("plain_text" varchar, "ffs_name" varchar)
returns varchar
language sql
as
$$
select _ubiq_encrypt(
    plain_text,
    ffs_name,
    (select get_encrypt_key(cache) from ubiq_ffs_cache)
)
$$;

-- Returns an Array ['encrypted value 1', 'encrypted value 2', ...]
create or replace function ubiq_encrypt_for_search_array("plain_text" varchar, "ffs_name" varchar)
returns array
language sql
as
$$
select _ubiq_encrypt_for_search_array(
    plain_text, 
    ffs_name,
    (select cache from ubiq_ffs_cache)
)
$$

-- Returns a multi-row table where each row is a separate encrypted value
create or replace function ubiq_encrypt_for_search_table(plain_text varchar, ffs_name varchar)
returns table (cipher_text varchar)
as
$$
select * 
from 
    table(
        _ubiq_encrypt_for_search_table(
            plain_text, 
            ffs_name, 
            (select cache from ubiq_ffs_cache)
        )
    )
$$;

create or replace function ubiq_fpe_decrypt("cipher_text" varchar, "ffs_name" varchar)
returns varchar
language sql
as
$$
select _ubiq_decrypt(
    cipher_text,
    ffs_name,
    (select cache from ubiq_ffs_cache)
)
$$;

drop table ubiq_ffs_cache;

create or replace procedure ubiq_begin_session("ffs_names" varchar)
returns varchar
language javascript
as
$$
    var sql = `create or replace temporary table ubiq_ffs_cache (cache object) as 
        select _ubiquser_data_fetch_data_key(
            '${ffs_names}',
            (select secret_crypto_access_key from ubiq_creds),
            (select _ubiq_broker_fetch_ffs_and_fpe_key( 
                '${ffs_names}', 
                (select access_key_id from ubiq_creds), 
                (select secret_signing_key from ubiq_creds)
            ))
        );`
    try {
        snowflake.execute({sqlText: sql});
        return "succeeded"
    }
    catch (err) {
        return "failed: " + err;
    }
$$;


-- Creates Cache with unwrapped keys; no Secret Crypto Key needed for enc/dec fpe cache functions.
create or replace procedure ubiq_begin_session("ffs_name" varchar, "access_key" varchar, "secret_signing_key" varchar, "secret_crypto_access_key" varchar)
returns varchar
language javascript
as
$$
    var sql = `create or replace temporary table ubiq_ffs_cache (cache object) as 
        select _ubiquser_data_fetch_data_key(
            '${ffs_name}',
            '${secret_crypto_access_key}',
            (select _ubiq_broker_fetch_ffs_and_fpe_key( 
                '${ffs_name}',
                '${access_key}', 
                '${secret_signing_key}'
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

-- Requires Access Key and Signing Key to authenticate with Ubiq Servers.
CREATE OR REPLACE PROCEDURE UBIQ_CLOSE_SESSION("ACCESS_KEY" VARCHAR, "SECRET_SIGNING_KEY" VARCHAR)
RETURNS variant
LANGUAGE JAVASCRIPT
execute as caller
AS
$$
    var sql = `
        SELECT 
        query_id, start_time, end_time, warehouse_size
        FROM TABLE(information_schema.query_history())
        WHERE (QUERY_TEXT LIKE '%ubiq_encrypt%' OR QUERY_TEXT LIKE '%ubiq_decrypt%')
        AND QUERY_TEXT NOT LIKE '%query_history%' -- exclude current query
        ORDER BY start_time DESC`;
    var cols = ['query_id', 'start_time', 'end_time', 'warehouse_size'];
    var queries = [];
    try {
        var db = snowflake.execute({ sqlText: sql });
        while (db.next()) {
            var row = {};
            for (var col_num = 0; col_num < cols.length; col_num = col_num + 1) {
                row[cols[col_num]] = db.getColumnValue(col_num + 1);
            }
            queries.push(row);
        }
        // return queries;
    }
    catch (err) {
        return "Failed: " + err;
    }
    var res = []
    queries.forEach(query => {
        try {
            var querySql = `
                SELECT
                    OPERATOR_STATISTICS:extension_functions.total_python_udf_handler_invocations,
                    OPERATOR_STATISTICS:extension_functions.total_python_udf_handler_execution_time
                FROM 
                    TABLE(get_query_operator_stats('${query.query_id}'))
                WHERE OPERATOR_TYPE = 'ExtensionFunction'
            `;
            var db2 = snowflake.execute({ sqlText: querySql });
            var executionCount = 0;
            var executionTime = 0;
            while (db2.next()) {
                executionCount = executionCount + db2.getColumnValue(1);
                executionTime = executionTime + db2.getColumnValue(2);
            }
            res.push({
                ...query,
                executionCount,
                executionTime
            });
        } catch (err) {
            res.push("Failed: " + err);
        }
    })
    // Call _ubiq_broker_submit_billing with res payload.
    snowflake.execute({
    sqlText: `SELECT _ubiq_broker_submit_events(
        PARSE_JSON('${JSON.stringify(res)}'),
        '${ACCESS_KEY}', 
        '${SECRET_SIGNING_KEY}'
    )`})

    // Drop the FFS cache
    snowflake.execute({sqlText: `DROP TABLE IF EXISTS ubiq_ffs_cache;`});
    return res;
$$;
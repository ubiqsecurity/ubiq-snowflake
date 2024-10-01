create or replace table ubiq_creds (
    access_key_id varchar(24),
    secret_signing_key varchar(44),
    secret_crypto_access_key varchar(44)
);


create or replace function _ubiq_get_encrypt_key("cache" object)
returns object
language javascript
as '
    for(const dataset_def in cache){
        cache[dataset_def].keys = [cache[dataset_def].keys[cache[dataset_def].current_key_number]];
        cache[dataset_def].current_key_only = true;
    }
    
    return cache
';

create or replace temporary table ubiq_cache (cache object);

create or replace function ubiq_encrypt("dataset_name" varchar, "plain_text" varchar)
returns varchar
language sql
as
$$
select _ubiq_encrypt(
    dataset_name,
    plain_text,
    (select _ubiq_get_encrypt_key(cache) from ubiq_cache)
)
$$;

-- Returns an Array ['encrypted value 1', 'encrypted value 2', ...]
create or replace function ubiq_encrypt_for_search_array("dataset_name" varchar, "plain_text" varchar)
returns array
language sql
as
$$
select _ubiq_encrypt_for_search_array(
    dataset_name,
    plain_text, 
    (select cache from ubiq_cache)
)
$$;

-- Returns a multi-row table where each row is a separate encrypted value
create or replace function ubiq_encrypt_for_search_table("dataset_name" varchar, "plain_text" varchar)
returns table (cipher_text varchar)
as
$$
select * 
from 
    table(
        _ubiq_encrypt_for_search_table(
            dataset_name, 
            plain_text, 
            (select cache from ubiq_cache)
        )
    )
$$;

create or replace function ubiq_decrypt("dataset_name" varchar, "cipher_text" varchar)
returns varchar
language sql
as
$$
select _ubiq_decrypt(
    dataset_name,
    cipher_text,
    (select cache from ubiq_cache)
)
$$;

drop table ubiq_cache;


-- Creates Cache with unwrapped keys; no Secret Crypto Key needed for enc/dec functions.
create or replace procedure ubiq_begin_session("dataset_name" varchar, "access_key" varchar, "secret_signing_key" varchar, "secret_crypto_access_key" varchar)
returns varchar
language javascript
as
$$
    var sql = `create or replace temporary table ubiq_cache (cache object) as 
        select _ubiq_fetch_data_key(
            '${dataset_name}',
            '${secret_crypto_access_key}',
            (select _ubiq_broker_fetch_dataset_and_structured_key( 
                '${dataset_name}',
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

    // Drop the cache
    snowflake.execute({sqlText: `DROP TABLE IF EXISTS ubiq_cache;`});
    return res;
$$;
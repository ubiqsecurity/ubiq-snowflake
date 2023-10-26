import os
import sys

from datetime import datetime
from dateutil import tz

import snowflake.connector

def print_exception(stage, ex):
    print(f'FAILURE: {stage}')
    template = "An exception of type {0} occurred. Arguments:\n{1!r}"
    message = template.format(type(ex).__name__, ex.args)
    print(message)
    sys.exit(1)

def evaluate_threshold(threshold, reality, label):
    if not threshold:
        print (f'NOTE: No maximum allowed {label} threshold supplied')
        # didn't violate threshold
        return True
    
    if reality < int(threshold):
        print(f'PASSED: Maximum allowed {label} threshold of {threshold} milliseconds')
        return True
    else:
        print(f'FAILED: Exceeded maximum allowed {label} threshold of {threshold} milliseconds')
        return False

# Pull Credentials
ACCOUNT = os.getenv('SNOWSQL_ACCOUNT')
USERNAME = os.getenv('SNOWSQL_USER')
PASSWORD = os.getenv('SNOWSQL_PASSWORD')
WAREHOUSE = os.getenv('SNOWSQL_WAREHOUSE')
DATABASE = os.getenv('SNOWSQL_DATABASE')
SCHEMA = os.getenv('SNOWSQL_SCHEMA')

# Pull Thresholds
MAX_ENCRYPT=os.getenv('MAX_ENCRYPT')
MAX_DECRYPT=os.getenv('MAX_DECRYPT')
AVG_ENCRYPT=os.getenv('AVG_ENCRYPT')
AVG_DECRYPT=os.getenv('AVG_DECRYPT')

EXEC_LIMIT=os.getenv('EXEC_LIMIT')

conn = snowflake.connector.connect(
    user=USERNAME,
    password=PASSWORD,
    account=ACCOUNT,
    warehouse=WAREHOUSE,
    database=DATABASE,
    schema=SCHEMA
)

cursor = conn.cursor()

encrypt_query_id = ''
decrypt_query_id = ''

success = True

try:
    # Load Session
    cursor.execute("CALL ubiq_begin_fpe_session('BIRTH_DATE,SSN,ALPHANUM_SSN,UTF8_STRING_COMPLEX');")
except Exception as ex:
    print_exception('Begin FPE Session', ex)
    

try:
    # Perform Decrypt Load test
    query = 'SELECT t.dataset, t.ciphertext, ubiq_fpe_encrypt_cache(t.plaintext, t.dataset) as encrypted, t.plaintext FROM ubiq_load_test t'
    if EXEC_LIMIT:
        query = query + f' LIMIT {EXEC_LIMIT}'
    query = query + ';'
    cursor.execute(query)
    valid = True
    for (dataset, ciphertext, encrypted, plaintext) in cursor:
        if (not ciphertext == encrypted):
            valid = False
        if(not valid):
            print(f'Encrypt failure, mismatch found: plaintext: {plaintext} | ciphertext: {ciphertext} | encrypted: {encrypted}')
            break
    # Save query ID to retrieve Results
    encrypt_query_id = cursor.sfqid
except Exception as ex:
    print_exception('Encrypt Query', ex)

if not success:
    sys.exit(success)

try:
    query = 'SELECT t.dataset, t.plaintext, ubiq_fpe_decrypt_cache(t.ciphertext, t.dataset) as decrypted, t.ciphertext FROM ubiq_load_test t'
    if EXEC_LIMIT:
        query = query + f' LIMIT {EXEC_LIMIT}'
    query = query + ';'
    # Perform Load test
    cursor.execute(query)
    for (dataset, plaintext, decrypted, ciphertext) in cursor:
        if (not plaintext == decrypted):
            valid = False
        if(not valid):
            print(f'Encrypt failure, mismatch found: ciphertext: {ciphertext} | plaintext: {plaintext} | decrypted: {decrypted}')
            break
    # Save query ID to retrieve Results
    decrypt_query_id = cursor.sfqid
except Exception as ex:
    print_exception('Decrypt Query', ex)

if not success:
    sys.exit(success)


res = []
try: 
    # Encrypt
    cursor.execute('''SELECT 
        QUERY_ID, ROWS_PRODUCED, EXECUTION_TIME, START_TIME, END_TIME
        FROM TABLE(information_schema.query_history())
        WHERE QUERY_ID = \''''+ encrypt_query_id +'\'')
    for (query_id, rows_produced, execution_time, start_time, end_time) in cursor:
        avg_encrypt = execution_time / rows_produced
        print(f'Encrypt records count: {rows_produced} (times in Milliseconds)')
        print(f'   Average: {avg_encrypt}, Total: {execution_time}')
        res.append(evaluate_threshold(AVG_ENCRYPT, avg_encrypt, 'average encrypt'))
        res.append(evaluate_threshold(MAX_ENCRYPT, execution_time, 'total encrypt'))
except Exception as ex:
    print_exception('Encrypt Query Info', ex)
try: 
    # Decrypt
    cursor.execute('''SELECT 
        QUERY_ID, ROWS_PRODUCED, EXECUTION_TIME, START_TIME, END_TIME
        FROM TABLE(information_schema.query_history())
        WHERE QUERY_ID = \''''+ decrypt_query_id +'\'')
    for (query_id, rows_produced, execution_time, start_time, end_time) in cursor:
        avg_decrypt = execution_time / rows_produced
        print(f'Decrypt records count: {rows_produced} (times in Milliseconds)')
        print(f'   Average: {avg_decrypt}, Total: {execution_time}')
        res.append(evaluate_threshold(AVG_DECRYPT, avg_decrypt, 'average encrypt'))
        res.append(evaluate_threshold(MAX_DECRYPT, execution_time, 'total encrypt'))
except Exception as ex:
    print_exception('Decrypt Query Info', ex)

sys.exit(all(res))



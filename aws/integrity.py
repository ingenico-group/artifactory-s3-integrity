#!/usr/bin/env python3
import sys
import boto3
import time
import logging
import os

from botocore.config import Config
from botocore.exceptions import ClientError

def exec_query(max_retry, base_period, query_start) -> str:
    status = ""
    retries = 0
    period = base_period
    while retries <= max_retry and status != 'SUCCEEDED':
        logging.debug(f"Retry: {retries}, period: {period}")
        q = athena.get_query_execution(QueryExecutionId=query_start['QueryExecutionId'])
        print(q)
        status = q['QueryExecution']['Status']['State']
        if status == 'SUCCEEDED':
            logging.info(f"Query was successful, optional reason: {q['QueryExecution']['Status'].get('StateChangeReason', 'No reason')}")
            continue
        if status  == 'CANCELED':
            logging.error(f"Query was interrupted, optional reason: {q['QueryExecution']['Status'].get('StateChangeReason', 'No reason')}")
            exit(1)
        logging.debug(f"Got {status} with optional reason: {q['QueryExecution']['Status'].get('StateChangeReason','No reason')}. Retrying in {period}s")
        time.sleep(period)
        retries += 1
        period *= 2
    logging.debug(f"Retried {retries} times")
    return status
    

if "@job.loglevel@" == "DEBUG":
   logging.basicConfig( level=logging.DEBUG )
else:
   logging.basicConfig( level=logging.INFO )
 
athena_db = os.getenv('ATHENA_DB', 'inventory')
catalog = os.getenv('ATHENA_CATALOG', 'AwsDataCatalog')
workgroup = os.getenv('ATHENA_WORKGROUP', 'primary')
table = os.getenv('ATHENA_TABLE', 'artifactory')
inventory_source = os.getenv('INVENTORY_SOURCE')

max_retry = int(os.getenv('MAX_RETRY', '10'))
base_period = int(os.getenv('BASE_PERIOD', '2'))
page = int(os.getenv('PAGE_SIZE', '50'))

db_user = os.getenv('DB_USER', 'root')
db_password = os.getenv('DB_PASS','')
db_host = os.getenv('DB_HOST',"localhost")
db_port = int(os.getenv('DB_PORT', "3306"))
database = os.getenv('DB_DATABASE',"artifactory")

bucket_name = os.getenv('BUCKET_NAME', '')

athena = boto3.client('athena')

context = {
    'Database': athena_db,
    'Catalog' : catalog
}

ddl = f"""
CREATE EXTERNAL TABLE IF NOT EXISTS {table}(
        bucket string,
        key string,
        version_id string,
        is_latest boolean,
        is_delete_marker boolean
) PARTITIONED BY (
    dt string
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
    STORED AS INPUTFORMAT 'org.apache.hadoop.hive.ql.io.SymlinkTextInputFormat'
    OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.IgnoreKeyTextOutputFormat'
    LOCATION '{inventory_source}';
"""
query_start = athena.start_query_execution(
    QueryString = ddl,
    WorkGroup = workgroup,
    QueryExecutionContext = context
)
status = exec_query(max_retry, base_period, query_start)
if status != 'SUCEEDED':
    logging.error(f"Create table query did not succeed: {status}")

repair = f'MSCK REPAIR TABLE {table};'
query_start = athena.start_query_execution(
    QueryString = repair,
    WorkGroup = workgroup,
    QueryExecutionContext = context
)
status = exec_query(max_retry, base_period, query_start)
if status != 'SUCEEDED':
        logging.error(f"Repair table query did not succeed.")

# Connect to MariaDB Platform
try:
    conn = mariadb.connect(
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port,
        database=database
    )
    cur = conn.cursor()
    base = "0000000000000000000000000000000000000000"
    s3 = boto3.resource('s3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name = region_name,
        config = Config(
            proxies = {
                'http': proxy,
                'https': proxy
            }
        )
    )
    issues = []
    total_count = 0
    while True:
        try:
            cur.execute("SELECT sha1 FROM binaries WHERE sha1 > ? ORDER BY sha1 ASC LIMIT ?", (base, page))
            query_start = athena.start_query_execution(
                QueryString = f"""
                    SELECT bucket, key, max(dt) FROM "{athena_db}"."{athena_table}" 
                        WHERE key > 'filestore/{base[0:2]}/{base}'
                            AND is_delete_marker = false
                            AND bucket = '{bucket_name}'
                        GROUP BY bucket, key
                        ORDER BY key ASC
                        LIMIT {page * 2};
                """,
                WorkGroup = workgroup,
                QueryExecutionContext = context
            )
            status = exec_query(max_retry, base_period, athena, query_start)
            if status != 'SUCCEEDED':
                logging.error("Select query did not succeed.")
                sys.exit(5)
            inventory_keys = set(map(lambda tuple: tuple['Data'][1]['VarCharValue'], athena.get_query_results(
                QueryExecutionId = query_start['QueryExecutionId'],
                MaxResults = page * 2
            )['ResultSet']['Rows'][1:]))
            local_count = 0
            for col in cur:
                total_count += 1
                local_count += 1
                sha1 = col[0]
                base = sha1
                logging.debug(f'Got {sha1} from Artifactory\'s DB.')
                object_key = f"filestore/{sha1[0:2]}/{sha1}"
                logging.debug(f'Trying to get {object_key} from Athena inventory.')
                if object_key not in inventory_keys:
                    logging.debug(f'{object_key} not in Athena inventory, trying to get it directly from S3.')
                    try:
                        s3.ObjectSummary(bucket_name, object_key).load()
                    except ClientError as err:
                        logging.debug(f'Got issue while trying to retrieve object from S3 {err}')
                        if err.response['Error']['Code'] == "404":
                            logging.warn(f'Integrity issue. SHA1: {sha1}, KEY: {object_key}')
                            issues.append(sha1)
                        else:
                            logging.error('Error is not handled by this program, exiting...')
                            logging.error(err)
                            sys.exit(3)
            logging.debug(f'This iteration handled {local_count} items')
            logging.debug(f'Page size was {page}')
            if local_count < page:
                logging.debug(f'We have less rows ({local_count}) for this iteration than the size of a page ({page}). Job\'s done')
                break
        except mariadb.Error as e:
            logging.error(f'Error while querying MariaDB: {e}')
            logging.error(f'Last valid position was {base} in case you want to retry.')
            sys.exit(2)
    logging.info(f'Finished processing {total_count} objects for Artifactory database')
    if len(issues) > 0:
        logging.warn(f'Some binaries ({len(issues)}) failed integrity check')
        logging.warn(f'Integrity score is {round((100 * (total_count - len(issues)))/total_count,2)} %')
        for issue in issues:
            print(f'SHA1: {issue}, KEY: filestore/{issue[0:2]}/{issue}')
        sys.exit(4)
    else:
        logging.info('No integrity check failed, nice !')
        logging.info('Integrity score is well over 100%.')
        sys.exit(0)
except mariadb.Error as e:
    logging.error(f'Error connecting to MariaDB Platform: {e}')
    sys.exit(1)
finally:
    if (conn):
        cur.close()
        conn.close()
        logging.debug('MariaDB connection is closed')
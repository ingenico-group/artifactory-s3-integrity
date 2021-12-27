#!/usr/bin/env python3
import sys
import boto3
import botocore
import mariadb
import logging
import os

from botocore.config import Config
from botocore.exceptions import ClientError
log_level=os.getenv("LOG_LEVEL","INFO")
if log_level == "INFO":
    logging.basicConfig(level=logging.INFO)
elif log_level == "DEBUG":
    logging.basicConfig(level=logging.DEBUG)

page = int(os.getenv('PAGE_SIZE', '50'))

db_user = os.getenv('DB_USER', 'root')
db_password = os.getenv('DB_PASS','')
db_host = os.getenv('DB_HOST',"localhost")
db_port = int(os.getenv('DB_PORT', "3306"))
database = os.getenv('DB_DATABASE',"artifactory")

bucket_name = os.getenv('BUCKET_NAME', '')

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

    s3 = boto3.resource('s3')

    issues = []
    total_count = 0
    while True:
        try:
            cur.execute("SELECT sha1 FROM binaries WHERE sha1 > ? ORDER BY sha1 ASC LIMIT ?", (base, page))
            local_count = 0
            for col in cur:
                total_count += 1
                local_count += 1
                sha1 = col[0]
                base = sha1
                logging.debug(f'Got {sha1} from Artifactory\'s DB.')
                object_key = f"filestore/{sha1[0:2]}/{sha1}"
                logging.debug(f'Trying to get {object_key} from S3.')
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
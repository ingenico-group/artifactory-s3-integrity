# artifactory-s3-integrity
Scripts to check Artifactory filestore integrity on S3

This is a very simple version.

This scripts incurs costs on AWS.

## Standalone

The standalone version will basically do one HEAD request per binary.

Thus most of the price will be about the amount of requests.

Depending on the deduplication from Artifactory and the lifecycle policy of the bucket,
it can be estimated roughly at the amount of objects in the bucket.

Data rate should be low.

## AWS

This version is slightly more complicated but more efficient.

The TF files can be modifies and used to create a daily bucket inventory for Artifactory.

An Athena DB and tables are then created on the said inventory.

An IAM user is also created with the necessary policies to use Athena.

The python script can then be used.

It'll create the table, repair it if needed (after a new inventory has been created).

Afterwards, it'll query Artifactory DB and try to find the corresponding key in Athena table.

Both side are being paged.

If there're more items in the Athena table page than in Artifactory DB you might see some inconsistencies.

That's why we use a page two times the size of the Artifactory DB one.

This allows us to avoid shift in keys.

Feel free to handle that more intelligently.

If the key is not found in the Athena table (if the binary is more recent than the last inventory for instance), the script checks directly on S3.

If after that the binary is still not found, it's reported as inconsistent.

## Informations

These scripts are inspired from: https://jfrog.com/knowledge-base/how-to-check-integrity-of-binaries-in-artifactory-database-against-filestore/

The script offered by JFrog for S3 is not efficient as it'll get ALL artifacts from Artifactory.

This is suited for small installations but not for bigger instances.

This also means that it can only check integrity on the bucket currently mounted.

This script will allow querying an S3 bucket not currently used by Artifactory.

In the case of S3 replication for instance.


## Requirements

Python libraries:

* mariadb
* boto3

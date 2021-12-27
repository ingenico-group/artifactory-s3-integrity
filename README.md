# artifactory-s3-integrity
Scripts to check Artifactory filestore integrity on S3

This is a very simple version.

This scripts incurs costs on AWS.

The standalone version will basically do one HEAD request per binary.

Thus most of the price will be about the amount of requests.

Depending on the deduplication from Artifactory and the lifecycle policy of the bucket,
it can be estimated roughly at the amount of objects in the bucket.

Data rate should be low.

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

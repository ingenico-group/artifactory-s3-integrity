resource "aws_s3_bucket" "inventory" {
  bucket_prefix = "inventory-"


  lifecycle_rule {
    enabled = true
    noncurrent_version_expiration {
      days = 30
    }

    expiration {
      expired_object_delete_marker = true
    }
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
  tags = {
    Role = "Inventory"
  }
}

resource "aws_s3_bucket_public_access_block" "inventory_public_access_setting" {

  bucket = aws_s3_bucket.inventory.id

  # Using Amazon S3 Block Public Access
  # https://docs.aws.amazon.com/AmazonS3/latest/dev/access-control-block-public-access.html
  block_public_acls = true

  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "athena-results" {
  bucket_prefix = "athena-results-"



  lifecycle_rule {
    enabled = true
    noncurrent_version_expiration {
      days = 30
    }

    expiration {
      expired_object_delete_marker = true
    }
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
  tags = {
    Role = "Athena"
  }
}

resource "aws_s3_bucket_public_access_block" "athena_public_access_setting" {

  bucket = aws_s3_bucket.athena-results.id

  # Using Amazon S3 Block Public Access
  # https://docs.aws.amazon.com/AmazonS3/latest/dev/access-control-block-public-access.html
  block_public_acls = true

  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_inventory" "inventory" {
  bucket                   = "artifactory"
  name                     = "DailyFullBinaries"
  included_object_versions = "All"
  schedule {
    frequency = "Daily"
  }

  destination {
    bucket {
      format     = "Parquet"
      bucket_arn = aws_s3_bucket.inventory.arn
      prefix     = "inventory"
    }
  }
}

resource "aws_s3_bucket_policy" "inventory" {
  bucket = aws_s3_bucket.inventory.id
  policy = data.aws_iam_policy_document.inventory-svc-policy.json
}
data "aws_iam_policy_document" "inventory-policy" {
  statement {
    # Allow RO to:
    # Artifactory bucket for realtime inventory
    # Artifactory inventory for daily inventory
    # Athena output bucket
    actions = [
      "s3:ListBucket",
      "s3:GetObject"
    ]

    resources = [
      "arn:aws:s3:::artifactory/*",
      "arn:aws:s3:::artifactory"
      aws_s3_bucket.inventory.arn,
      "${aws_s3_bucket.inventory.arn}/*",
      aws_s3_bucket.athena-results.arn,
      "${aws_s3_bucket.athena-results.arn}/*"
    ]
  }
  statement {
    # Give more permissions on output bucket
    # As users needs to write results to it
    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucketMultipartUploads",
      "s3:AbortMultipartUpload",
      "s3:PutObject",
      "s3:ListMultipartUploadParts",
      "glue:GetTable",
      "glue:CreateTable",
      "glue:GetPartitions",
      "glue:GetDatabase",
    ]
    resources = [
      aws_s3_bucket.athena-results.arn,
      "${aws_s3_bucket.athena-results.arn}/*",
      "arn:aws:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:database/${aws_athena_database.inventory.name}",
      "arn:aws:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:catalog",
    ]
  }
  statement {
    actions = [
      "athena:CreatePreparedStatement",
      "athena:StartQueryExecution",
      "athena:GetQueryResultsStream",
      "athena:UpdatePreparedStatement",
      "athena:GetQueryResults",
      "athena:DeletePreparedStatement",
      "athena:GetPreparedStatement",
      "athena:ListQueryExecutions",
      "athena:GetWorkGroup",
      "athena:StopQueryExecution",
      "athena:GetQueryExecution",
      "athena:ListPreparedStatements",
      "athena:BatchGetQueryExecution",
      "glue:GetTable",
      "glue:GetDatabase",
      "glue:BatchCreatePartition",
      "glue:GetPartitions",
      "s3:ListBucket",
      "s3:GetObject",
    ]
    resources = [
      aws_athena_workgroup.inventory.arn,
      aws_s3_bucket.inventory.arn,
      "${aws_s3_bucket.inventory.arn}/*",
      aws_s3_bucket.bucket.arn,
      "${aws_s3_bucket.bucket.arn}/*",
      aws_s3_bucket.athena-results.arn,
      "${aws_s3_bucket.athena-results.arn}/*",
      "arn:aws:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:catalog",
      "arn:aws:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:database/default",
      "arn:aws:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:database/${aws_athena_database.inventory.name}",
      "arn:aws:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:table/${aws_athena_database.inventory.name}/artifactory"
    ]
  }
  statement {
    # Absolutely not sure about that one
    actions = [
      "athena:GetDatabase"
    ]
    resources = [
      "*"
    ]
  }
  statement {
    actions = [
      "glue:CreateTable",
      "glue:GetTable"
    ]
    resources = [
      "arn:aws:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:table/${aws_athena_database.inventory.name}/artifactory",
      "arn:aws:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:database/default"
    ]
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_iam_policy_document" "inventory-svc-policy" {
  statement {
    principals {
      type        = "Service"
      identifiers = ["s3.amazonaws.com"]
    }
    actions = [
      "s3:PutObject"
    ]
    resources = [
      "${aws_s3_bucket.inventory.arn}/*"
    ]

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values = [
        "arn:aws:s3:::artifactory"
      ]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values = [
        data.aws_caller_identity.current.account_id
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values = [
        "bucket-owner-full-control"
      ]
    }
  }
}


resource "aws_iam_policy" "inventory-policy" {
  name        = "inventory"
  path        = "/"
  description = "Policy used mainly to get Artifactory inventory"
  policy      = data.aws_iam_policy_document.inventory-policy.json
  tags = {
    Role = "Integrity"
  }
}

resource "aws_iam_group" "inventory" {
  name = "inventory"
}

resource "aws_iam_group_policy_attachment" "inventory" {
  group      = aws_iam_group.inventory.name
  policy_arn = aws_iam_policy.inventory-policy.arn
}


resource "aws_iam_user" "inventory" {
  name = "inventory"
  tags = {
    Type = "IAMUser",
    Role = "Integrity"
  }
}

resource "aws_iam_group_membership" "inventory" {
  name = "inventory"
  users = [
    aws_iam_user.inventory.name
  ]
  group = aws_iam_group.inventory.name
}

resource "aws_iam_access_key" "inventory" {
  user    = aws_iam_user.inventory.name
  pgp_key = var.pgp_key
}

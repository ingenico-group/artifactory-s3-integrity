resource "aws_athena_workgroup" "inventory" {
  #checkov:skip=CKV_AWS_159:No need for encryption ?
  name        = "inventory"
  description = "Workgroup for inventory related buckets"
  configuration {
    enforce_workgroup_configuration = true
    result_configuration {
      #tfsec:ignore:AWS059
      output_location = "s3://${aws_s3_bucket.artifactory-athena-results.id}/output/"
    }
  }
  tags = {
    Role = "Storage"
  }
}

resource "aws_athena_database" "inventory" {
  name   = "inventory"
  bucket = aws_s3_bucket.athena-results.id
}

# We can't easily create Ahtena table by hand : https://github.com/hashicorp/terraform-provider-aws/issues/12129
# It'll have to wait for that to avoid creating all the glue things ourselves
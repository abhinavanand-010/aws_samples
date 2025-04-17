"""
Question 1: Multi-Region S3 Replication Setup
DevOps Role Mock Exam - Question 1

Tasks:
  a) Create source and destination buckets in different regions.
  b) Enable versioning on both buckets.
  c) Create and attach an IAM role for replication.
  d) Configure cross-region replication policy.
  e) Upload a sample file and validate replication.
"""

# File: scripts/setup_s3_replication.py
import boto3
import os
import json
from dotenv import load_dotenv

# .env environment variables (commented here for reference):
# AWS_REGION=us-east-1
# DEST_AWS_REGION=us-west-1
# SOURCE_BUCKET=yourname-source-bucket
# DEST_BUCKET=yourname-dest-bucket

load_dotenv()

# Load environment variables\ SOURCE_REGION = os.getenv("AWS_REGION")
DEST_REGION = os.getenv("DEST_AWS_REGION")
SOURCE_BUCKET = os.getenv("SOURCE_BUCKET")
DEST_BUCKET = os.getenv("DEST_BUCKET")
REPLICATION_ROLE_NAME = "s3-replication-role"

# Initialize clients
s3_source = boto3.client("s3", region_name=SOURCE_REGION)
s3_dest = boto3.client("s3", region_name=DEST_REGION)
iam = boto3.client("iam")

def create_bucket(bucket_name, region, client):
    """Create an S3 bucket in the specified region."""
    client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={'LocationConstraint': region}
    )
    print(f"Bucket created: {bucket_name} in {region}")

def enable_versioning(bucket_name, client):
    """Enable versioning on the specified S3 bucket."""
    client.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={"Status": "Enabled"}
    )
    print(f"Versioning enabled on: {bucket_name}")

def create_replication_role():
    """Create an IAM role and policy for S3 replication."""
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "s3.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }

    role = iam.create_role(
        RoleName=REPLICATION_ROLE_NAME,
        AssumeRolePolicyDocument=json.dumps(assume_role_policy)
    )

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:GetReplicationConfiguration", "s3:ListBucket"],
                "Resource": f"arn:aws:s3:::{SOURCE_BUCKET}"
            },
            {
                "Effect": "Allow",
                "Action": ["s3:GetObjectVersion", "s3:GetObjectVersionAcl"],
                "Resource": f"arn:aws:s3:::{SOURCE_BUCKET}/*"
            },
            {
                "Effect": "Allow",
                "Action": ["s3:ReplicateObject", "s3:ReplicateDelete"],
                "Resource": f"arn:aws:s3:::{DEST_BUCKET}/*"
            }
        ]
    }

    iam.put_role_policy(
        RoleName=REPLICATION_ROLE_NAME,
        PolicyName="S3ReplicationPolicy",
        PolicyDocument=json.dumps(policy)
    )

    print(f"IAM replication role created: {REPLICATION_ROLE_NAME}")
    return role['Role']['Arn']

def setup_replication(role_arn):
    """Configure cross-region replication for the source bucket."""
    config = {
        "Role": role_arn,
        "Rules": [
            {
                "Status": "Enabled",
                "Prefix": "",
                "Destination": {
                    "Bucket": f"arn:aws:s3:::{DEST_BUCKET}"
                },
                "Priority": 1,
                "DeleteMarkerReplication": {"Status": "Disabled"}
            }
        ]
    }

    s3_source.put_bucket_replication(
        Bucket=SOURCE_BUCKET,
        ReplicationConfiguration=config
    )
    print("Replication configuration applied.")

if __name__ == '__main__':
    # Step 1: Create buckets
    create_bucket(SOURCE_BUCKET, SOURCE_REGION, s3_source)
    create_bucket(DEST_BUCKET, DEST_REGION, s3_dest)

    # Step 2: Enable versioning
    enable_versioning(SOURCE_BUCKET, s3_source)
    enable_versioning(DEST_BUCKET, s3_dest)

    # Step 3: Create IAM role for replication
    role_arn = create_replication_role()

    # Step 4: Apply replication configuration
    setup_replication(role_arn)

    # Step 5: Upload and test replication
    with open("sample.txt", "w") as f:
        f.write("Hello from replication test!")
    s3_source.upload_file("sample.txt", SOURCE_BUCKET, "sample.txt")
    print("Sample file uploaded to source bucket.")

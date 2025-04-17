# 📁 aws_day2_project/scripts/

# ---------- Question 1A: Create S3 Bucket and Upload File using boto3 ----------

# File: scripts/create_s3_upload.py
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
FILE_NAME = "yourname_sample.txt"

s3 = boto3.client("s3", region_name=AWS_REGION)

def create_bucket():
    s3.create_bucket(
        Bucket=BUCKET_NAME,
        CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
    )
    print(f"Bucket {BUCKET_NAME} created")

def enable_versioning():
    s3.put_bucket_versioning(
        Bucket=BUCKET_NAME,
        VersioningConfiguration={'Status': 'Enabled'}
    )
    print("Versioning enabled")

def upload_file():
    with open(FILE_NAME, 'w') as f:
        f.write("This is a test file upload")
    s3.upload_file(FILE_NAME, BUCKET_NAME, FILE_NAME)
    print(f"Uploaded {FILE_NAME}")

def tag_bucket():
    s3.put_bucket_tagging(
        Bucket=BUCKET_NAME,
        Tagging={"TagSet": [
            {"Key": "k1", "Value": "v1"},
            {"Key": "k2", "Value": "v2"}
        ]}
    )
    print("Tags added")

if __name__ == '__main__':
    create_bucket()
    enable_versioning()
    upload_file()
    tag_bucket()

# Run it using:
# python scripts/create_s3_upload.py


# ---------- Question 1B: PowerShell CLI Script to list VPC and subnets ----------

# File: scripts/list_vpc_subnets.ps1

$region = "us-east-1"
$output = "YourName_vpc_subnet.csv"

$vpcs = aws ec2 describe-vpcs --region $region | ConvertFrom-Json
$subnets = aws ec2 describe-subnets --region $region | ConvertFrom-Json

$result = @()
foreach ($vpc in $vpcs.Vpcs) {
    foreach ($subnet in $subnets.Subnets | Where-Object { $_.VpcId -eq $vpc.VpcId }) {
        $result += [PSCustomObject]@{
            VpcId = $vpc.VpcId
            CidrBlock = $vpc.CidrBlock
            SubnetId = $subnet.SubnetId
            SubnetCidr = $subnet.CidrBlock
        }
    }
}

$result | Export-Csv -Path $output -NoTypeInformation
aws s3 cp $output s3://$env:S3_BUCKET_NAME/$output --region $region

# Run using:
# powershell scripts/list_vpc_subnets.ps1


# ---------- Question 2: ECS Fargate Deployment with Nginx Image ----------

# File: scripts/deploy_ecs.py
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

region = os.getenv("AWS_REGION")
repo_name = "yourname-nginx"
cluster_name = "yourname-ecs-cluster"
service_name = "yourname-nginx-service"
task_family = "yourname-nginx-task"
container_name = "nginx-container"

# 1. Create ECS cluster
ecs = boto3.client('ecs', region_name=region)
response = ecs.create_cluster(clusterName=cluster_name)
print(f"ECS Cluster Created: {response['cluster']['clusterName']}")

# 2. Register Task Definition
ecr_url = f"<your-account-id>.dkr.ecr.{region}.amazonaws.com/{repo_name}:latest"

task_def_response = ecs.register_task_definition(
    family=task_family,
    networkMode='awsvpc',
    requiresCompatibilities=['FARGATE'],
    cpu='256',
    memory='512',
    executionRoleArn='<your-execution-role-arn>',
    containerDefinitions=[
        {
            'name': container_name,
            'image': ecr_url,
            'portMappings': [
                {
                    'containerPort': 80,
                    'hostPort': 80,
                    'protocol': 'tcp'
                }
            ],
            'essential': True
        }
    ]
)
print("Task Definition registered")

# 3. Create Service
subnet_ids = ['subnet-xxxxxx']
security_group_ids = ['sg-xxxxxx']

service_response = ecs.create_service(
    cluster=cluster_name,
    serviceName=service_name,
    taskDefinition=task_family,
    desiredCount=1,
    launchType='FARGATE',
    networkConfiguration={
        'awsvpcConfiguration': {
            'subnets': subnet_ids,
            'securityGroups': security_group_ids,
            'assignPublicIp': 'ENABLED'
        }
    }
)
print(f"ECS Service Created: {service_response['service']['serviceName']}")

# Run:
# python scripts/deploy_ecs.py


# ---------- Question 3: Lambda Triggered by SQS ----------

# File: scripts/deploy_lambda_sqs.py
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

lambda_client = boto3.client('lambda')
sqs_client = boto3.client('sqs')

queue_name = 'yourname-lambda-queue'
function_name = 'yourname-sqs-lambda'
role_arn = '<your-lambda-execution-role-arn>'

# Create SQS Queue
queue_url = sqs_client.create_queue(QueueName=queue_name)['QueueUrl']
print(f"SQS Queue Created: {queue_url}")
queue_arn = sqs_client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=['QueueArn'])['Attributes']['QueueArn']

# Create Lambda Function (Assumes zip and role already prepared)
with open("function.zip", "rb") as f:
    zipped_code = f.read()

lambda_client.create_function(
    FunctionName=function_name,
    Runtime='python3.9',
    Role=role_arn,
    Handler='lambda_function.lambda_handler',
    Code={'ZipFile': zipped_code},
    Timeout=30,
    MemorySize=128
)

# Add Permission
lambda_client.add_permission(
    FunctionName=function_name,
    StatementId='SQSInvokePermission',
    Action='lambda:InvokeFunction',
    Principal='sqs.amazonaws.com',
    SourceArn=queue_arn
)

# Create Event Source Mapping
lambda_client.create_event_source_mapping(
    EventSourceArn=queue_arn,
    FunctionName=function_name,
    BatchSize=1
)

print("Lambda connected to SQS")

# Run using:
# python scripts/deploy_lambda_sqs.py


# ---------- Question 4: CloudFormation for Infra ----------

# File: infra/template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: AWS Day 2 Infra
Resources:
  MyS3Bucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub '${AWS::StackName}-bucket'
      VersioningConfiguration:
        Status: Enabled
      Tags:
        - Key: k1
          Value: v1
        - Key: k2
          Value: v2

# Deploy using:
# aws cloudformation deploy --template-file infra/template.yaml --stack-name awsday2infra --capabilities CAPABILITY_IAM


# ---------- Question 5: Cleanup Script ----------

# File: scripts/cleanup_by_tags.py
import boto3
from dotenv import load_dotenv

load_dotenv()

tags = [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}]

resourcegroup = boto3.client("resourcegroupstaggingapi")
s3 = boto3.client("s3")

def delete_tagged_resources():
    resources = resourcegroup.get_resources(
        TagFilters=tags,
        ResourcesPerPage=50
    )
    for resource in resources['ResourceTagMappingList']:
        arn = resource['ResourceARN']
        print(f"Deleting: {arn}")
        if ":s3:::" in arn:
            bucket_name = arn.split(":::")[1]
            delete_s3_bucket(bucket_name)

def delete_s3_bucket(bucket):
    try:
        objs = s3.list_objects_v2(Bucket=bucket)
        if 'Contents' in objs:
            for obj in objs['Contents']:
                s3.delete_object(Bucket=bucket, Key=obj['Key'])
        s3.delete_bucket(Bucket=bucket)
        print(f"Deleted bucket {bucket}")
    except Exception as e:
        print(e)

if __name__ == '__main__':
    delete_tagged_resources()

# Run using:
# python scripts/cleanup_by_tags.py

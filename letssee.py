import boto3
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# ---- QUESTION 2: CI/CD Pipeline using CodePipeline (GitHub to ECS Fargate) ----

# Environment Variables (Load these from .env file)
# AWS_REGION - AWS region, e.g., us-east-1
# GITHUB_TOKEN - GitHub personal access token
# GITHUB_REPO_NAME - Your GitHub repository name
# ECS_CLUSTER_NAME - ECS cluster name where Fargate is deployed
# ECS_SERVICE_NAME - ECS service name
# ECS_TASK_DEFINITION - ECS task definition name

region = os.getenv("AWS_REGION")
github_token = os.getenv("GITHUB_TOKEN")
github_repo_name = os.getenv("GITHUB_REPO_NAME")
ecs_cluster_name = os.getenv("ECS_CLUSTER_NAME")
ecs_service_name = os.getenv("ECS_SERVICE_NAME")
ecs_task_definition = os.getenv("ECS_TASK_DEFINITION")

# Clients for AWS services
codepipeline = boto3.client("codepipeline", region_name=region)
codebuild = boto3.client("codebuild", region_name=region)
ecs = boto3.client("ecs", region_name=region)
iam = boto3.client("iam", region_name=region)

# Step 1: Create IAM Role for CodePipeline
def create_codepipeline_role():
    """
    Creates an IAM role for CodePipeline with necessary permissions
    """
    role_name = "CodePipeline-Service-Role"
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "codepipeline.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    # Create the role
    response = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust_policy)
    )
    print(f"CodePipeline Role {role_name} created successfully")
    return response['Role']['Arn']

# Step 2: Create CodeBuild Project for ECS Build
def create_codebuild_project():
    """
    Creates CodeBuild project that will build and push the Docker image to ECR
    """
    project_name = "ECS-Build-Project"
    build_spec = """version: 0.2
    phases:
      install:
        runtime-versions:
          python: 3.8
      build:
        commands:
          - echo Build started on `date`
          - docker build -t $REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION .
          - docker push $REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION
    """
    response = codebuild.create_project(
        name=project_name,
        source={
            "type": "GITHUB",
            "location": f"https://github.com/{github_repo_name}.git",
            "auth": {"gitCloneDepth": 1, "gitSubmodulesConfig": {"fetchSubmodules": True}},
            "buildspec": build_spec
        },
        environment={
            "type": "LINUX_CONTAINER",
            "image": "aws/codebuild/standard:4.0",
            "computeType": "BUILD_GENERAL1_SMALL"
        },
        serviceRole="arn:aws:iam::your-account-id:role/CodeBuild-Role",
    )
    print(f"CodeBuild project {project_name} created successfully")

# Step 3: Setup CodePipeline to trigger on GitHub push
def create_codepipeline():
    """
    Creates a CodePipeline that connects GitHub and ECS Fargate for automatic deployment
    """
    pipeline_name = "ECS-Pipeline"
    role_arn = create_codepipeline_role()
    response = codepipeline.create_pipeline(
        pipeline={
            "name": pipeline_name,
            "roleArn": role_arn,
            "artifactStore": {
                "type": "S3",
                "location": "your-s3-bucket-name"
            },
            "stages": [
                {
                    "name": "Source",
                    "actions": [
                        {
                            "name": "GitHub-Source",
                            "actionTypeId": {
                                "category": "Source",
                                "owner": "ThirdParty",
                                "provider": "GitHub",
                                "version": "1"
                            },
                            "outputArtifacts": [{"name": "source_output"}],
                            "configuration": {
                                "Owner": "your-github-username",
                                "Repo": github_repo_name,
                                "Branch": "main",
                                "OAuthToken": github_token
                            }
                        }
                    ]
                },
                {
                    "name": "Build",
                    "actions": [
                        {
                            "name": "CodeBuild",
                            "actionTypeId": {
                                "category": "Build",
                                "owner": "AWS",
                                "provider": "CodeBuild",
                                "version": "1"
                            },
                            "inputArtifacts": [{"name": "source_output"}],
                            "outputArtifacts": [{"name": "build_output"}],
                            "configuration": {
                                "ProjectName": "ECS-Build-Project"
                            }
                        }
                    ]
                },
                {
                    "name": "Deploy",
                    "actions": [
                        {
                            "name": "ECS-Deploy",
                            "actionTypeId": {
                                "category": "Deploy",
                                "owner": "AWS",
                                "provider": "ECS",
                                "version": "1"
                            },
                            "inputArtifacts": [{"name": "build_output"}],
                            "configuration": {
                                "ClusterName": ecs_cluster_name,
                                "ServiceName": ecs_service_name,
                                "FileName": "imagedefinitions.json"
                            }
                        }
                    ]
                }
            ]
        }
    )
    print(f"CodePipeline {pipeline_name} created successfully")

# ---- QUESTION 3: Serverless Function for File Upload Triggered by S3 ----

# Environment Variables:
# AWS_REGION - AWS region, e.g., us-east-1
# S3_BUCKET_NAME - The name of the S3 bucket that will trigger the Lambda function

def create_lambda_function():
    """
    Creates a Lambda function that is triggered by S3 object upload
    """
    lambda_client = boto3.client('lambda', region_name=region)
    s3_client = boto3.client('s3', region_name=region)

    # Create Lambda function
    with open("lambda_function.zip", "rb") as f:
        zipped_code = f.read()

    function_name = "file-upload-trigger-function"
    role_arn = "arn:aws:iam::your-account-id:role/lambda-role"

    lambda_client.create_function(
        FunctionName=function_name,
        Runtime='python3.8',
        Role=role_arn,
        Handler='lambda_function.lambda_handler',
        Code={'ZipFile': zipped_code},
        Timeout=30,
        MemorySize=128
    )

    # Create an S3 bucket notification to trigger Lambda
    s3_client.put_bucket_notification_configuration(
        Bucket=os.getenv("S3_BUCKET_NAME"),
        NotificationConfiguration={
            "LambdaFunctionConfigurations": [
                {
                    "LambdaFunctionArn": f"arn:aws:lambda:{region}:your-account-id:function:{function_name}",
                    "Events": ["s3:ObjectCreated:*"]
                }
            ]
        }
    )
    print(f"Lambda function {function_name} created and linked to S3 upload events.")

# ---- QUESTION 4: CloudFormation Template for an EC2 Instance and S3 Bucket ----

# Environment Variables:
# AWS_REGION - AWS region, e.g., us-east-1
# EC2_INSTANCE_TYPE - EC2 instance type, e.g., t2.micro

def create_cloudformation_template():
    """
    Creates a CloudFormation template to deploy EC2 instance and S3 bucket
    """
    cloudformation_client = boto3.client('cloudformation', region_name=region)

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "CloudFormation template to create EC2 and S3",
        "Resources": {
            "MyEC2Instance": {
                "Type": "AWS::EC2::Instance",
                "Properties": {
                    "InstanceType": os.getenv("EC2_INSTANCE_TYPE"),
                    "ImageId": "ami-0c55b159cbfafe1f0",  # Example AMI for Ubuntu 20.04
                    "KeyName": "your-keypair-name"
                }
            },
            "MyS3Bucket": {
                "Type": "AWS::S3::Bucket",
                "Properties": {
                    "BucketName": "your-unique-bucket-name"
                }
            }
        }
    }

    # Create the CloudFormation stack
    cloudformation_client.create_stack(
        StackName="ec2-s3-stack",
        TemplateBody=json.dumps(template)
    )
    print("CloudFormation stack created with EC2 and S3.")

# ---- QUESTION 5: Cleanup AWS Resources by Tagging ----

# Environment Variables:
# RESOURCE_TAGS - Tags to identify resources for deletion

def delete_resources_by_tags():
    """
    Deletes resources (EC2, S3, etc.) by tags
    """
    resourcegroup = boto3.client("resourcegroupstaggingapi", region_name=region)

    # Example tags to look for
    tags = [{"Key": "Env", "Value": "Test"}]

    resources = resourcegroup.get_resources(
        TagFilters=tags,
        ResourcesPerPage=50
    )

    for resource in resources['ResourceTagMappingList']:
        arn = resource['ResourceARN']
        print(f"Deleting resource: {arn}")
        if ":s3:::" in arn:
            bucket_name = arn.split(":::")[1]
            delete_s3_bucket(bucket_name)

# Cleanup S3 bucket by ARN
def delete_s3_bucket(bucket_name):
    """
    Deletes an S3 bucket
    """
    s3 = boto3.client("s3")
    s3.delete_bucket(Bucket=bucket_name)
    print(f"Deleted S3 bucket {bucket_name}.")

# ---- END OF FILE ----

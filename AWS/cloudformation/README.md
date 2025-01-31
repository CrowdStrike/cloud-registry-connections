# AWS ECR Registry Connections

This CloudFormation will create a Lambda function which interacts with the CrowdStrike API to register ECR registries with Image Assessment.

This deployment provisions the following:

- Stores your Falcon API credentials in Secrets Manager.
- Creates an IAM Role for Lambda Execution.
- Creates a Lambda Function to interact with CrowdStrike API.
- Creates an IAM Role for Registry Connections.

## Prerequisites

### Falcon API Client Scope
Falcon Container Image: Read & Write

### Lambda Package
1. Run the following commands:

```
cd /source/lambda
pip install -t . -r requirements.txt
zip lambda_function.zip .
```

2. Upload lambda_function.zip to the root of an S3 Bucket in the region you will launch the template.

## Single Account

Launch this template in your account as a stack.

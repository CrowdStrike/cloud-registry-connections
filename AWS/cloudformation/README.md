# AWS ECR Registry Connections

This CloudFormation will create a Lambda function which interacts with the CrowdStrike API to register ECR registries with Image Assessment.

This deployment provisions the following:

- Stores your Falcon API credentials in Secrets Manager.
- Creates an IAM Role for Lambda Execution.
- Creates a Lambda Function to interact with CrowdStrike API.
- Creates an IAM Role for Registry Connections.

This solution creates an ECR registry connection in each active AWS Region in the account to ensure all potential ECR Repositories will be protected with Image Assessment.

## Prerequisites

### Generate API Keys

The distributor package uses the CrowdStrike API to download the sensor onto the target instance. It is highly recommended that you create a dedicated API client for the distributor package.

1. In the CrowdStrike console, navigate to **Support and resources** > **API Clients & Keys**. Click **Add new API Client**.
2. Add the following api scopes:

    | Scope                  | Permission | Description                                                  |
    | ---------------------- | ---------- | -------------------------------------------------------------|
    | Falcon Container Image | *READ*     | List registry connections, view registry connection details. |
    | Falcon Container Image | *WRITE*    | Create, update, or delete a registry connection.             |

3. Click **Add** to create the API client. The next screen will display the API **CLIENT ID**, **SECRET**, and **BASE URL**. You will need all three for the next step.

    <details><summary>picture</summary>
    <p>

    ![api-client-keys](./assets/api-client-keys.png)

    </p>
    </details>

> Note: This page is only shown once. Make sure you copy **CLIENT ID**, **SECRET**, and **BASE URL** to a secure location.

Falcon Container Image: Read & Write

### Lambda Package
The lambda package in this repo must be packaged and uploaded to an S3 Bucket.

1. Run the following commands:

```
cd /source/lambda
pip install -t . -r requirements.txt
zip lambda_function.zip *
```

2. Upload lambda_function.zip to the root of an S3 Bucket in the region you will launch the template.

## Single Account Deployment

Launch this template in your account as a stack and configure the following parameters:

| Name  | Description   | Type  | Default | Required |
| ----- | ------------- | ----- | ------- | :------: |
| S3Bucket  | Location of templates and lambda.zip package. | `string` | `[]`  |    yes    |
| FalconClientID  | Your Falcon OAuth2 Client ID. | `string` | `[]`  |    yes    |
| FalconSecret  | Your Falcon OAuth2 API Secret. | `string` | `[]`  |    yes    |
| SecretsManagerSecretName  | Secrets Manager Secret Name that will contain the Falcon ClientId, ClientSecret, and Cloud for the CrowdStrike APIs. | `string` | `crowdstrike-ecr-api-credentials`  |    yes    |
| ECRExecutionRoleName  | The name of the role that will be used for Lambda execution. | `string` | `crowdstrike-ecr-lambda-role`  |    yes    |
| PermissionsBoundary  | The name of the policy used to set the permissions boundary for IAM roles. | `string` | `[]`  |    no    |
| ECRLambdaName  | The name of the lambda function used to register ECR registry connections. | `string` | `crowdstrike-ecr-function`  |    yes    |

The template includes a trigger to invoke the lambda function on create.  It may take 5-10 minutes for the stack to fully complete and see Registry Connections in Falcon Cloud Security Image assessment settings.

## Organization Deployment

Launch this template in your account as a Service Managed **StackSet**.  For more information on StackSets see [AWS Documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-orgs-associate-stackset-with-org.html)

> Note: To deploy this solution against an AWS Organization the S3 Bucket must allow organization access.  Please see this example bucket policy for guidance:

```yaml
PolicyDocument:
    Version: 2012-10-17
    Statement:
        - Sid: AllowDeploymentRoleGetObject
        Effect: Allow
        Action: s3:GetObject
        Principal: '*'
        Resource: !Sub arn:${AWS::Partition}:s3:::${OrganizationS3Bucket}/*
        Condition:
            ArnLike:
            aws:PrincipalArn:
                - !Sub arn:${AWS::Partition}:iam::*:role/${StackSetExecutionRole}
                - !Sub arn:${AWS::Partition}:iam::*:role/stacksets-exec-*
        - Sid: DenyExternalPrincipals
        Effect: Deny
        Action: 's3:*'
        Principal: '*'
        Resource:
            - !Sub arn:${AWS::Partition}:s3:::${OrganizationS3Bucket}
            - !Sub arn:${AWS::Partition}:s3:::${OrganizationS3Bucket}/*
        Condition:
            StringNotEquals:
            aws:PrincipalOrgID: !GetAtt OrgIdLambdaCustomResource.organization_id
        - Sid: SecureTransport
        Effect: Deny
        Action: 's3:*'
        Principal: '*'
        Resource:
            - !Sub arn:${AWS::Partition}:s3:::${OrganizationS3Bucket}
            - !Sub arn:${AWS::Partition}:s3:::${OrganizationS3Bucket}/*
        Condition:
            Bool:
            aws:SecureTransport: False
```

## Deleting the Stack
By default, when you delete the Stack, the AWS resources provisioned will be deleted but the Registry Connections will remain.  To delete the stack and registry connections, uncomment the following code in the lambda function before deleting the stack.

```python
elif event['RequestType'] in ['Delete']:
    local_entities = get_entities(falcon_client_id, falcon_secret, account)
    delete_entities(falcon_client_id, falcon_secret, local_entities)
    delete_role()
    print("Complete!")
    cfnresponse_send(event, SUCCESS, response, "CustomResourcePhysicalID")
```

> [!IMPORTANT]
> If you choose to uncomment this function, when deleting the stack:
> All ECR Registry connections for this AWS account will be removed from Falcon.

## Troubleshooting
If you experience any failures please review the logs in CloudWatch > Log groups /aws/lambda/crowdstrike-ecr-function
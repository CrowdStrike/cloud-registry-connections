# AWS ECR Registry Connections

Create an ECR registry connection in each active AWS Region in the account to ensure all ECR Repositories will be protected with Image Assessment.

## ✨ Features

- **🌐  Multi-Region Support**: Automatically registers ECR connections across multiple AWS regions or specific regions based on configuration
- **🏛️  GovCloud Compatibility**: Full support for AWS GovCloud environments with appropriate security principals
- **🏷️  Flexible Resource Naming**: Customizable resource prefixes and suffixes for organizational compliance
- **🧹  Automatic Cleanup**: Optional automatic disconnection of registry connections when the stack is deleted
- **🔐  Secure Credential Management**: API credentials stored securely in AWS Secrets Manager
- **🏢  Organization Deployment**: Support for AWS Organizations via CloudFormation StackSets
- **📊  Comprehensive Logging**: Detailed CloudWatch logging for troubleshooting and monitoring

## ⚙️ How it Works

1. **Stack Deployment**: When the CloudFormation stack is deployed, it provisions the necessary AWS resources including Lambda function, IAM roles, and Secrets Manager secret.

2. **Credential Storage**: Your CrowdStrike Falcon API credentials are securely stored in AWS Secrets Manager.

3. **Lambda Execution**: A Lambda function is automatically triggered during stack creation that:
   - Retrieves Falcon API credentials from Secrets Manager
   - Creates the required IAM role for CrowdStrike ECR access
   - Registers ECR registry connections with the specified regions in your Falcon environment

4. **Registry Connection**: The Lambda function establishes connections between your ECR registries and CrowdStrike's Image Assessment service, enabling continuous container image scanning.

5. **Cleanup (Optional)**: If the `DisconnectUponDelete` parameter is set to `True`, the Lambda function will automatically remove all ECR registry connections from Falcon when the stack is deleted.

## 📋 Prerequisites

### Generate API Keys

The distributor package uses the CrowdStrike API to download the sensor onto the target instance. It is highly recommended that you create a dedicated API client for the distributor package.

1. In the CrowdStrike console, navigate to **Support and resources** > **API Clients & Keys**. Click **Add new API Client**.
2. Add the following api scopes:

    | Scope                  | Permission | Description                                                  |
    | ---------------------- | ---------- | -------------------------------------------------------------|
    | Falcon Container Image | *READ*     | List registry connections, view registry connection details. |
    | Falcon Container Image | *WRITE*    | Create, update, or delete a registry connection.             |

3. Click **Add** to create the API client. The next screen will display the API **CLIENT ID**, **SECRET**, and **BASE URL**.

> Note: This page is only shown once. Make sure you copy **CLIENT ID**, **SECRET**, and **BASE URL** to a secure location.

Falcon Container Image: Read & Write

### Lambda Package
The lambda package in this repo must be packaged and uploaded to an S3 Bucket.

1. Run the following commands:

```
cd /source/lambda
pip install -t . -r requirements.txt
zip -r lambda_function.zip .
```

2. Upload lambda_function.zip to the root of an S3 Bucket in the region you will launch the template.

## 🚀 Single Account Deployment

Launch the [template](./cloudformation/ecr-registration-stack.yml) in your account as a stack and configure the following parameters:

### AWS Configuration Parameters
| Name  | Description   | Type  | Default | Required |
| ----- | ------------- | ----- | ------- | :------: |
| S3Bucket  | Location of templates and lambda.zip package. | `string` | `[]`  |    yes    |
| PermissionsBoundary  | The name of the policy used to set the permissions boundary for IAM roles. | `string` | `[]`  |    no    |
| GovCloud  | Whether this is a GovCloud AWS Account. | `string` | `False`  |    yes    |
| CommToGovCloud  | Whether this is a commercial AWS Account connecting to GovCloud Falcon. | `string` | `False`  |    yes    |

### Deployment Scope Parameters
| Name  | Description   | Type  | Default | Required |
| ----- | ------------- | ----- | ------- | :------: |
| Regions  | Which regions to register ECR Connections. | `string` | `[]`  |    yes    |

### Falcon API Credentials Parameters
| Name  | Description   | Type  | Default | Required |
| ----- | ------------- | ----- | ------- | :------: |
| FalconClientId  | Your Falcon OAuth2 Client ID. | `string` | `[]`  |    yes    |
| FalconSecret  | Your Falcon OAuth2 API Secret. | `string` | `[]`  |    yes    |
| FalconCloud  | CrowdStrike Falcon Cloud (us-1, us-2, eu-1, us-gov-1, us-gov-2). | `string` | `[]`  |    yes    |

### Resource Names Parameters
| Name  | Description   | Type  | Default | Required |
| ----- | ------------- | ----- | ------- | :------: |
| ResourcePrefix  | The prefix to be added to all resource names. | `string` | `crowdstrike-ecr`  |    yes    |
| ResourceSuffix  | The suffix to be added to all resource names. | `string` | `[]`  |    no    |

### Additional Parameters
| Name  | Description   | Type  | Default | Required |
| ----- | ------------- | ----- | ------- | :------: |
| DisconnectUponDelete  | Whether to automatically disconnect all ECR Registries from CrowdStrike upon deletion of this stack. | `string` | `False`  |    yes    |

The template includes a trigger to invoke the lambda function on create.  It may take 5-10 minutes for the stack to fully complete and see Registry Connections in Falcon Cloud Security Image assessment settings.

## 🏢 Organization Deployment

Launch the [template](./cloudformation/ecr-registration-stack.yml) in your account as a Service Managed **StackSet** against a **single region**.  For more information on StackSets see [AWS Documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-orgs-associate-stackset-with-org.html)

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

## 🗑️ Deleting the Stack
By default, when you delete the Stack, the AWS resources provisioned will be deleted but the Registry Connections will remain.

### Automatic Disconnect Option
To automatically disconnect ECR Registry connections when the stack is deleted, set the `DisconnectUponDelete` parameter to `True` when deploying the stack. This is the recommended approach for managing registry connection cleanup.

If you have already deployed the stack with `DisconnectUponDelete` parameter set to `False`, and wish to delete the stack and disconnect ECR Registry Connections, first update the stack with `DisconnectUponDelete` parameter set to `True`.  Once the update is complete, you may now continue with deleting the stack.

### Manual Disconnect Option (Legacy)
Alternatively, you can manually uncomment the following code in the lambda function before deleting the stack:

```python
elif event['RequestType'] in ['Delete']:
    local_entities = get_entities(falcon_client_id, falcon_secret, account)
    delete_entities(falcon_client_id, falcon_secret, local_entities)
    delete_role()
    print("Complete!")
    cfnresponse_send(event, SUCCESS, response, "CustomResourcePhysicalID")
```

> [!IMPORTANT]
> When using either the `DisconnectUponDelete` parameter or manually uncommenting the delete function:
> All ECR Registry connections for this AWS account will be removed from Falcon when the stack is deleted.

## 🔍 Troubleshooting
If you experience any failures please review the logs in CloudWatch > Log groups `/aws/lambda/{ResourcePrefix}-function{ResourceSuffix}` (default: `/aws/lambda/crowdstrike-ecr-function`).

## 🏛️ GovCloud Support
This template now supports deployment in AWS GovCloud environments:

- Set the `GovCloud` parameter to `True` when deploying in a GovCloud account
- Set the `CommToGovCloud` parameter to `True` when deploying from a commercial AWS account that needs to connect to GovCloud Falcon
- The template will automatically configure the appropriate CrowdStrike principals and policies for GovCloud environments

## 🌍 Region Configuration
The `Regions` parameter allows you to specify which AWS regions should have ECR registry connections created. This provides flexibility to only register ECR repositories in specific regions where they are actively used, rather than all active regions in the account.  If this parameter is left blank, all active regions will be registered.

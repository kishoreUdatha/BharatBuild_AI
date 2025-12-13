# GitHub Secrets Setup for CI/CD

This document describes the GitHub secrets required for the CI/CD pipeline to work.

## Required Secrets

### AWS Credentials

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `AWS_ACCOUNT_ID` | Your AWS account ID | `930030325663` |
| `AWS_ACCESS_KEY_ID` | AWS access key for deployment | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for deployment | `wJalr...` |

### Application Secrets

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `ANTHROPIC_API_KEY` | Claude AI API key | `sk-ant-api03-...` |
| `DOMAIN_NAME` | Production domain name | `bharatbuild.ai` |

### Optional Secrets

| Secret Name | Description | Used For |
|-------------|-------------|----------|
| `CLOUDFRONT_DISTRIBUTION_ID` | CloudFront distribution ID | Cache invalidation |
| `SLACK_WEBHOOK_URL` | Slack webhook URL | Deployment notifications |

## How to Add Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret listed above

## AWS IAM Policy

Create an IAM user with the following permissions for CI/CD:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:PutImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecs:DescribeTaskDefinition",
                "ecs:RegisterTaskDefinition",
                "ecs:DescribeServices",
                "ecs:UpdateService",
                "ecs:ListTasks",
                "ecs:DescribeTasks",
                "ecs:ExecuteCommand"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "cloudfront:CreateInvalidation"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:PassRole"
            ],
            "Resource": [
                "arn:aws:iam::*:role/bharatbuild-*"
            ]
        }
    ]
}
```

## GitHub Environments

The pipeline uses GitHub environments for deployment protection:

### `staging`
- Used for `develop` branch deployments
- No required reviewers (optional)

### `production`
- Used for `main` and `production` branch deployments
- **Recommended**: Add required reviewers for production approval
- **Recommended**: Add deployment protection rules

## Setting Up Environments

1. Go to **Settings** → **Environments**
2. Create `staging` and `production` environments
3. For production:
   - Enable "Required reviewers"
   - Add team members who can approve deployments
   - Enable "Wait timer" (optional, e.g., 5 minutes)

## Workflow Triggers

| Branch | Action |
|--------|--------|
| `develop` | Deploy to staging |
| `main` | Deploy to production |
| `production` | Deploy to production |
| Pull Request | Run tests only |
| Manual dispatch | Choose environment |

## Manual Deployment

You can manually trigger deployments from the Actions tab:

1. Go to **Actions** → **Deploy to AWS ECS**
2. Click **Run workflow**
3. Select:
   - Environment (staging/production)
   - Skip tests (for emergency deployments)
   - Force rebuild (bypass cache)

## Troubleshooting

### ECR Login Failed
- Verify `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are correct
- Ensure IAM user has ECR permissions

### ECS Deployment Failed
- Check ECS service exists in the cluster
- Verify task definition name matches
- Check CloudWatch logs for container errors

### Task Definition Not Found
- Ensure task definition is registered in ECS
- Verify the task definition family name matches

## Local Testing

Before pushing, you can test the deployment locally:

```bash
# Set AWS credentials
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_REGION=ap-south-1

# Run deployment script
./scripts/deploy-aws.sh status
./scripts/deploy-aws.sh deploy v42
```

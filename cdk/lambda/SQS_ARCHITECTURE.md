# Build Checker - SQS Internal Tool

## Overview

The Build Checker is an internal security auditing tool that analyzes GitHub repositories for automated build and deployment processes. It's designed for batch processing via SQS, making it perfect for organization-wide compliance audits.

## Architecture

```
┌─────────────────────┐
│  Submit Repos       │
│  (Python Script)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   SQS Queue         │
│  (build-check-      │
│   queue)            │
└──────────┬──────────┘
           │ Trigger (batch=1)
           ▼
┌──────────────────────────────┐
│  Lambda Function             │
│  ├─ Strands Agent            │
│  ├─ GitHub MCP Server        │
│  └─ Claude 3.5 Sonnet        │
└──────────┬───────────────────┘
           │
           ├─────────────┬──────────────┐
           ▼             ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ DynamoDB │  │  GitHub  │  │ Bedrock  │
    │  Table   │  │   API    │  │          │
    └──────────┘  └──────────┘  └──────────┘
```

## Components

### 1. SQS Queue (`build-check-queue`)

- **Purpose**: Decouples repository submission from analysis
- **Visibility Timeout**: 6 minutes (Lambda timeout + buffer)
- **Retention**: 14 days
- **Dead Letter Queue**: `build-check-dlq` (3 retries)
- **Batch Size**: 1 (process repositories sequentially)

### 2. Lambda Function

- **Runtime**: Python 3.11 on ARM64
- **Memory**: 1024 MB
- **Timeout**: 5 minutes
- **Concurrency**: Limited to 5 (respects GitHub API rate limits)
- **Trigger**: SQS with batch size of 1

### 3. DynamoDB Table (`build-check-results`)

- **Partition Key**: `repository` (string)
- **Sort Key**: `timestamp` (string)
- **TTL**: 90 days (automatic cleanup)
- **GSI**: `BuildProcessIndex` for querying by build status
- **Point-in-Time Recovery**: Enabled

## Usage

### Submit Repositories for Analysis

```bash
# Single repository
python submit_repos.py awslabs/aws-cdk

# Multiple repositories
python submit_repos.py awslabs/aws-cdk awslabs/strands microsoft/vscode

# From a file (one repo per line)
python submit_repos.py --file repos.txt

# Custom queue URL
python submit_repos.py --queue-url https://sqs... awslabs/aws-cdk
```

**repos.txt example:**

```
awslabs/aws-cdk
awslabs/strands
microsoft/vscode
# Comments are supported
TeslaFreak/study-buddy
```

### Query Results

```bash
# Get results for specific repository
python query_results.py awslabs/aws-cdk

# List repositories without builds
python query_results.py --no-builds

# List repositories with builds
python query_results.py --has-builds

# Get latest N results
python query_results.py --latest 10

# Export all results to JSON
python query_results.py --export results.json

# Scan all results (summary)
python query_results.py
```

### Direct Lambda Invocation (Testing)

```bash
# Test with direct invocation
aws lambda invoke \
  --function-name <BuildCheckerLambdaName> \
  --payload '{"repository": "awslabs/aws-cdk"}' \
  response.json

cat response.json
```

## Deployment

```bash
cd cdk

# Build CDK
npm run build

# Deploy with GitHub token
cdk deploy -c githubToken=ghp_your_token_here
```

**Outputs:**

- `BuildCheckQueueUrl` - SQS queue URL for submissions
- `BuildCheckQueueName` - Queue name
- `BuildCheckerLambdaName` - Lambda function name
- `ResultsTableName` - DynamoDB table name

## SQS Message Format

Messages sent to the queue must follow this format:

```json
{
  "repository": "owner/repo-name"
}
```

The Lambda automatically handles:

- SQS batch records
- Message parsing
- Error handling
- Result storage

## DynamoDB Schema

### Primary Keys

- **Partition Key**: `repository` (e.g., "awslabs/aws-cdk")
- **Sort Key**: `timestamp` (ISO 8601 format)

### Attributes

```json
{
  "repository": "awslabs/aws-cdk",
  "timestamp": "2025-12-12T10:30:00.123456",
  "hasBuildProcess": "true",
  "hasBuildProcessBool": true,
  "buildSystemsFound": ["GitHub Actions", "CDK Pipelines"],
  "confidenceLevel": "high",
  "evidence": [
    ".github/workflows/build.yml: Comprehensive CI/CD",
    "lib/pipeline-stack.ts: CDK Pipeline construct"
  ],
  "recommendations": [
    "Add automated security scanning",
    "Implement staging deployments"
  ],
  "summary": "Repository has robust build automation...",
  "ttl": 1733994600
}
```

### Global Secondary Index (BuildProcessIndex)

- **Partition Key**: `hasBuildProcess` (string: "true"/"false")
- **Sort Key**: `timestamp`
- **Use**: Query all repos by build status

## Monitoring

### CloudWatch Metrics

**Lambda Metrics:**

- `Invocations` - Number of repositories processed
- `Errors` - Failed analyses
- `Duration` - Processing time per repository
- `Throttles` - Concurrent execution limit hits

**SQS Metrics:**

- `NumberOfMessagesSent` - Repos queued
- `NumberOfMessagesReceived` - Repos processed
- `ApproximateAgeOfOldestMessage` - Queue lag
- `NumberOfMessagesDeleted` - Successful completions

**DynamoDB Metrics:**

- `ConsumedWriteCapacityUnits` - Write usage
- `ConsumedReadCapacityUnits` - Read usage

### CloudWatch Logs Insights Queries

**Find repositories without builds:**

```sql
fields @timestamp, repository
| filter @message like /❌/
| stats count() by repository
| sort count desc
```

**Analysis duration:**

```sql
fields @timestamp, repository, @duration
| filter @message like /Successfully analyzed/
| stats avg(@duration) as avg_ms, max(@duration) as max_ms, min(@duration) as min_ms
```

**Error patterns:**

```sql
fields @timestamp, repository, @message
| filter @message like /ERROR/ or @message like /Failed/
| stats count() by repository
```

## Cost Analysis

### Per Repository Analysis

- **Lambda**: ~$0.0003 (300s @ 1024MB ARM64)
- **Bedrock (Sonnet)**: ~$0.015 (avg 5K input, 2K output tokens)
- **DynamoDB**: ~$0.0000025 (1 write, 25KB)
- **SQS**: $0.0000004 (1 message)
- **Total per repo**: ~$0.0153

### Monthly Estimates

| Repositories/Month | Lambda | Bedrock | DynamoDB | SQS      | Total       |
| ------------------ | ------ | ------- | -------- | -------- | ----------- |
| 100                | $0.03  | $1.50   | $0.00025 | $0.00004 | **$1.53**   |
| 1,000              | $0.30  | $15.00  | $0.0025  | $0.0004  | **$15.30**  |
| 10,000             | $3.00  | $150.00 | $0.025   | $0.004   | **$153.03** |

**Note:** Bedrock is the dominant cost (~98%).

## Rate Limits

### GitHub API

- **Authenticated**: 5,000 requests/hour
- **Unauthenticated**: 60 requests/hour
- **Strategy**: Lambda concurrency limited to 5 to stay within limits

### AWS Service Limits

- **Lambda Concurrent Executions**: 5 (reserved for this function)
- **SQS Messages in Flight**: 120,000 (default)
- **DynamoDB Throughput**: On-demand (auto-scales)
- **Bedrock**: Regional limits apply

## Error Handling

### Retry Strategy

1. **Lambda Failure**: Message returns to SQS
2. **SQS Redelivery**: After visibility timeout (6 min)
3. **Max Retries**: 3 attempts
4. **Dead Letter Queue**: Failed messages after 3 retries

### Common Errors

| Error                   | Cause                        | Solution                        |
| ----------------------- | ---------------------------- | ------------------------------- |
| `GitHub API rate limit` | Too many concurrent requests | Wait or reduce concurrency      |
| `Repository not found`  | Invalid repo name or private | Check permissions/name          |
| `Timeout`               | Large repository             | Increase Lambda timeout         |
| `Permission denied`     | Invalid GitHub token         | Update token with proper scopes |
| `MCP server failed`     | Node.js bundling issue       | Redeploy Lambda                 |

### Accessing DLQ

```bash
# Get DLQ URL
QUEUE_URL=$(aws cloudformation describe-stacks \
  --stack-name StudyBuddyStack \
  --query 'Stacks[0].Outputs[?OutputKey==`BuildCheckDLQUrl`].OutputValue' \
  --output text)

# Receive messages from DLQ
aws sqs receive-message \
  --queue-url $QUEUE_URL \
  --max-number-of-messages 10
```

## Security Best Practices

### GitHub Token Management

**Development:**

```bash
cdk deploy -c githubToken=ghp_dev_token
```

**Production (Recommended):**
Store in AWS Secrets Manager:

```bash
# Store token
aws secretsmanager create-secret \
  --name github-token \
  --secret-string '{"token":"ghp_your_token"}'

# Grant Lambda permission
aws iam put-role-policy \
  --role-name BuildCheckerLambdaRole \
  --policy-name SecretsManagerPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:*:*:secret:github-token-*"
    }]
  }'
```

Update Lambda to fetch from Secrets Manager:

```python
import boto3
import json

secrets = boto3.client('secretsmanager')
response = secrets.get_secret_value(SecretId='github-token')
GITHUB_TOKEN = json.loads(response['SecretString'])['token']
```

### IAM Least Privilege

The Lambda role only has:

- ✅ CloudWatch Logs (write)
- ✅ Bedrock (invoke model)
- ✅ DynamoDB (write to specific table)
- ✅ SQS (receive/delete messages)
- ❌ No S3 access
- ❌ No other AWS services

### Network Security

For production:

```typescript
// Deploy Lambda in VPC
vpc: ec2.Vpc.fromLookup(this, 'VPC', { isDefault: false }),
vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
securityGroups: [securityGroup],

// Add VPC endpoint for Bedrock
new ec2.InterfaceVpcEndpoint(this, 'BedrockEndpoint', {
  vpc,
  service: new ec2.InterfaceVpcEndpointService('com.amazonaws.us-east-1.bedrock-runtime'),
});
```

## Operational Runbooks

### Daily Operations

1. **Monitor Queue Depth**

   ```bash
   aws sqs get-queue-attributes \
     --queue-url <queue-url> \
     --attribute-names ApproximateNumberOfMessages
   ```

2. **Check for Failed Analyses**

   ```bash
   python query_results.py --export daily-report.json
   # Review failures
   ```

3. **Review DLQ**
   ```bash
   aws sqs receive-message --queue-url <dlq-url> --max-number-of-messages 10
   ```

### Weekly Operations

1. **Generate Compliance Report**

   ```bash
   python query_results.py --no-builds > non-compliant-repos.txt
   # Send to security team
   ```

2. **Cost Analysis**
   - Check CloudWatch Logs Insights for processing stats
   - Review Cost Explorer for Bedrock/Lambda costs

### Monthly Operations

1. **Re-scan All Repositories**

   ```bash
   python query_results.py --export all-repos.json
   # Extract unique repos and resubmit
   ```

2. **Archive Results**
   - Export DynamoDB table to S3 for long-term storage
   - Results auto-expire after 90 days (TTL)

## Troubleshooting

### Queue Not Processing

**Check Lambda:**

```bash
aws lambda get-function-configuration --function-name <name>
# Verify event source mapping exists
aws lambda list-event-source-mappings --function-name <name>
```

**Check IAM:**

```bash
# Ensure Lambda role can read from SQS
aws iam simulate-principal-policy \
  --policy-source-arn <lambda-role-arn> \
  --action-names sqs:ReceiveMessage sqs:DeleteMessage \
  --resource-arns <queue-arn>
```

### High Error Rate

**Common causes:**

1. GitHub token expired → Rotate token
2. Rate limit hit → Reduce submission rate
3. Invalid repository names → Validate before submission

### Results Not Appearing

**Check DynamoDB:**

```bash
aws dynamodb scan --table-name build-check-results --limit 5
```

**Check Lambda logs:**

```bash
aws logs tail /aws/lambda/<function-name> --follow
```

## Future Enhancements

- [ ] Webhook integration for automatic re-checks on repo updates
- [ ] Slack/email notifications for non-compliant repos
- [ ] Historical trend analysis dashboard
- [ ] Custom compliance rulesets per organization
- [ ] Integration with AWS Security Hub
- [ ] Support for GitLab and Bitbucket
- [ ] Automated remediation suggestions (PR creation)
- [ ] Pipeline quality scoring beyond presence/absence

## Related Documentation

- [Main CDK README](../README.md)
- [Lambda Implementation Details](BUILD_CHECKER_IMPLEMENTATION.md)
- [API Quick Reference](../API_QUICK_REFERENCE.md)
- [Strands Agents SDK](https://github.com/awslabs/strands)
- [GitHub MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/github)

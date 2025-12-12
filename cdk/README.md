# Study Buddy - AWS CDK Infrastructure

This CDK app deploys the complete serverless infrastructure for Study Buddy using **Strands Agents SDK** with Amazon Bedrock Knowledge Base integration.

## 🏗️ Architecture

### Study Buddy Agent (API Gateway + S3 Sessions)

```
┌─────────────────┐
│  React Frontend │
└────────┬────────┘
         │ HTTPS
         ▼
┌──────────────────────────────────┐
│      API Gateway (REST)          │
│  ├─ /chat (POST)                 │
│  └─ /materials (GET)             │
└────────┬─────────────────────────┘
         │
         ▼
┌─────────────────────┐
│ Study Buddy Lambda  │
│ (Strands Agent)     │
│  ├─ Claude Haiku    │
│  ├─ KB Retrieval    │
│  └─ S3 Sessions     │
└─────┬───────────────┘
      │
      ├──────────┬───────────────┐
      ▼          ▼               ▼
┌──────────┐ ┌────────┐ ┌──────────────┐
│Materials │ │Sessions│ │  Bedrock KB  │
│   S3     │ │   S3   │ │              │
└──────────┘ └────────┘ └──────────────┘
```

### Build Checker Agent (SQS-Triggered Internal Tool)

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
│  Build Checker Lambda        │
│  (Strands Agent + GitHub MCP)│
│  ├─ Claude Sonnet            │
│  ├─ GitHub MCP Server        │
│  └─ Repo Analysis            │
└──────────┬───────────────────┘
           │
           ├─────────────┬──────────────┐
           ▼             ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ DynamoDB │  │  GitHub  │  │ Bedrock  │
    │  Table   │  │   API    │  │          │
    └──────────┘  └──────────┘  └──────────┘
```

## 📦 What's Deployed

### Lambda Functions

1. **Study Buddy Chat Handler** (`agent_handler.py`)

   - Socratic tutoring assistant for biology
   - Uses Bedrock Knowledge Base for grounded responses
   - Maintains conversation history in S3

2. **Build Process Security Checker** (`build_checker_handler.py`) - **NEW**
   - **Internal tool** triggered by SQS queue (not via API Gateway)
   - Analyzes GitHub repos for automated build processes
   - Uses GitHub MCP server for repository access
   - Stores results in DynamoDB with 90-day retention
   - Provides security recommendations and compliance reporting

### API Endpoints

- `POST /chat` - Chat with Study Buddy agent
- `GET /materials` - Retrieve study materials

### Internal Services

- **SQS Queue** (`build-check-queue`) - Queues repositories for analysis
- **DynamoDB Table** (`build-check-results`) - Stores analysis results with TTL
- **Dead Letter Queue** (`build-check-dlq`) - Captures failed analyses after 3 retries

## 📋 Prerequisites

1. **AWS Account** with CLI configured
2. **AWS CDK** installed: `npm install -g aws-cdk`
3. **Python 3.12** installed
4. **Node.js 18+** and pnpm installed
5. **Bedrock Model Access**: Request access to Claude 3.5 Haiku and Sonnet in AWS Console
6. **GitHub Token** (for Build Checker): Personal access token with repo/public_repo scope

## 🚀 Quick Start

### 1. Install CDK Dependencies

```bash
cd cdk
pnpm install
```

### 2. Install Python Lambda Dependencies

```bash
# Install dependencies with ARM64 architecture for Lambda
npm run install-deps
```

This installs Strands Agents SDK and dependencies compatible with Lambda's ARM64 runtime.

### 3. Package Lambda Function

```bash
# Create deployment packages (app.zip and dependencies.zip)
npm run package
```

### 4. Bootstrap CDK (First Time Only)

```bash
npx cdk bootstrap
```

### 5. Deploy Infrastructure

#### Basic Deployment (Study Buddy only)

```bash
npx cdk deploy
```

#### Full Deployment (with Build Checker)

```bash
# Set GitHub token for Build Checker Lambda
npx cdk deploy -c githubToken=ghp_your_github_token_here
```

**Note the outputs:**

- `SessionBucketName` - Auto-managed conversation storage
- `ApiUrl` - Your API endpoint
- `ChatLambdaName` - Study Buddy Lambda function name
- `BuildCheckerLambdaName` - Build Checker Lambda function name (NEW)
- `BuildCheckQueueUrl` - SQS queue URL for submitting repos (NEW)
- `BuildCheckQueueName` - Queue name (NEW)
- `ResultsTableName` - DynamoDB table name (NEW)

### 6. Configure Knowledge Base ID

After creating your Bedrock Knowledge Base, update the Lambda environment variable:

```bash
aws lambda update-function-configuration \
  --function-name <ChatLambdaName-from-outputs> \
  --environment Variables="{KNOWLEDGE_BASE_ID=<your-kb-id>,SESSION_BUCKET=<session-bucket-name>,AWS_REGION=us-east-1}"
```

Or set it during deployment via CDK context:

```bash
npx cdk deploy --context knowledgeBaseId=<your-kb-id>
```

## 📁 Project Structure

```
cdk/
├── bin/
│   ├── study-buddy.ts              # CDK app entry point
│   ├── install_dependencies.sh     # Install Python deps for Lambda
│   └── package_for_lambda.py       # Package Lambda deployment zips
├── lib/
│   └── study-buddy-stack.ts        # Main CDK stack
├── lambda/
│   ├── agent_handler.py            # Strands Agent Lambda handler
│   └── requirements.txt            # Python dependencies
├── packaging/                       # Generated deployment packages
│   ├── app.zip                     # Lambda function code
│   ├── dependencies.zip            # Lambda layer dependencies
│   └── _dependencies/              # Installed Python packages
├── cdk.json                        # CDK configuration
├── package.json                    # Node.js dependencies
└── tsconfig.json                   # TypeScript configuration
```

## 🧠 How It Works

### Strands Agent Implementation

The Lambda handler (`lambda/agent_handler.py`) implements a Socratic tutoring assistant using:

1. **BedrockModel** - Claude 3.5 Haiku for cost-effective, intelligent responses
2. **S3SessionManager** - Automatic conversation persistence across sessions
3. **SlidingWindowConversationManager** - Manages context window (keeps last 20 messages)
4. **Custom KB Retrieval Tool** - Fetches relevant study materials from Bedrock Knowledge Base

### Key Features

- ✅ **Session Persistence**: Conversations automatically saved to S3
- ✅ **Socratic Teaching**: Guides students with questions, not direct answers
- ✅ **Knowledge Grounding**: Retrieves accurate information from study materials
- ✅ **Context Management**: Handles long conversations without token overflow
- ✅ **CORS Enabled**: Frontend can call the API directly

### API Usage

**Endpoint**: `POST {ApiUrl}/chat`

**Request**:

```json
{
  "message": "What is photosynthesis?",
  "sessionId": "user-123"
}
```

**Response**:

```json
{
  "response": "Great question! Before I explain, what do you already know about how plants get energy?",
  "sessionId": "user-123",
  "context_used": "Knowledge Base retrieval available via tool"
}
```

## 🔍 Build Process Security Checker (NEW)

The Build Checker Lambda analyzes GitHub repositories to ensure they have proper automated build and deployment processes in place.

### Features

- **Multi-System Detection**: Identifies GitHub Actions, CDK Pipelines, GitLab CI, Jenkins, and more
- **Project Type Awareness**: Analyzes CDK, frontend, backend, containerized, and Terraform projects
- **Confidence Scoring**: Provides high/medium/low confidence levels based on evidence quality
- **Actionable Recommendations**: Suggests specific improvements for build automation
- **Security Focus**: Flags repositories with manual deployments as security risks

### API Usage

**Endpoint**: `POST {ApiUrl}/build-check`

**Request**:

```json
{
  "repository": "awslabs/aws-cdk"
}
```

**Response**:

```json
{
  "repository": "awslabs/aws-cdk",
  "hasBuildProcess": true,
  "buildSystemsFound": ["GitHub Actions"],
  "confidenceLevel": "high",
  "evidence": [
    ".github/workflows/build.yml: Comprehensive CI/CD workflow",
    ".github/workflows/release.yml: Automated release process"
  ],
  "recommendations": [
    "Consider adding automated security scanning (SAST/DAST)",
    "Implement multi-stage deployments (dev → staging → prod)"
  ],
  "summary": "Repository has robust build automation with GitHub Actions. Well-established processes with opportunities for enhanced security."
}
```

### Setup Requirements

1. **GitHub Token**: Create a personal access token at https://github.com/settings/tokens

   - Scope: `repo` (for private repos) or `public_repo` (public only)
   - Set during deployment: `-c githubToken=ghp_your_token`

2. **Bedrock Model Access**: Ensure Claude 3.5 Sonnet is enabled in your AWS account

3. **Node.js in Lambda**: The Lambda bundles Node.js for the GitHub MCP server

### Testing

Use the provided test script:

```bash
cd cdk/lambda
python test_build_checker.py awslabs/aws-cdk
# Enter your API URL when prompted
```

Or use curl:

```bash
curl -X POST https://your-api-url/build-check \
  -H "Content-Type: application/json" \
  -d '{"repository": "awslabs/aws-cdk"}'
```

### Use Cases

1. **Security Audits**: Identify repositories lacking automated builds
2. **Compliance Reporting**: Track CI/CD adoption across teams
3. **Onboarding Validation**: Ensure new projects have proper automation
4. **Best Practices**: Promote build automation organization-wide

For detailed documentation, see [lambda/BUILD_CHECKER_README.md](lambda/BUILD_CHECKER_README.md)

## 🗄️ Bedrock Knowledge Base Setup

You mentioned your KB is already created. Here's what the Lambda needs:

### Required Environment Variables

- `KNOWLEDGE_BASE_ID` - Your Bedrock KB ID (e.g., `BOHUN6SA6J`)
- `SESSION_BUCKET` - S3 bucket for sessions (set by CDK)
- `AWS_REGION` - AWS region (e.g., `us-east-1`)

### Knowledge Base Configuration

The Lambda's `retrieve_study_materials` tool calls:

- `bedrock-agent-runtime:Retrieve` API
- Retrieves top 5 relevant chunks
- Returns content with source attribution and relevance scores

**IAM Permissions** (already configured in CDK):

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream",
    "bedrock-agent-runtime:Retrieve"
  ],
  "Resource": "*"
}
```

## 💰 Cost Estimates

| Component                   | Monthly Cost (10K queries) |
| --------------------------- | -------------------------- |
| Lambda (ARM64, 512MB)       | ~$2                        |
| Claude 3.5 Haiku            | ~$15                       |
| S3 Session Storage          | <$1                        |
| S3 Materials Storage        | <$1                        |
| API Gateway                 | ~$1                        |
| **S3 Express Vector Store** | ~$30                       |
| **Total**                   | **~$49/month**             |

_Much cheaper than OpenSearch Serverless ($345/month)!_

## 🔧 Development Workflow

### Update Lambda Code

1. Edit `lambda/agent_handler.py`
2. Run `npm run package`
3. Run `npx cdk deploy`

### Update CDK Infrastructure

1. Edit `lib/study-buddy-stack.ts`
2. Run `npm run build` (compile TypeScript)
3. Run `npx cdk synth` (validate)
4. Run `npx cdk deploy`

### Add Python Dependencies

1. Add to `lambda/requirements.txt`
2. Run `npm run install-deps`
3. Run `npm run package`
4. Run `npx cdk deploy`

## 🧪 Testing

### Test Lambda Locally

```bash
# Invoke Lambda directly (after deployment)
aws lambda invoke \
  --function-name <ChatLambdaName> \
  --cli-binary-format raw-in-base64-out \
  --payload '{"body": "{\"message\": \"What is photosynthesis?\", \"sessionId\": \"test-123\"}"}' \
  output.json

# View response
cat output.json | jq -r '.body' | jq
```

### Test API Gateway

```bash
# Test via API Gateway endpoint
curl -X POST <ApiUrl>/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is ATP?", "sessionId": "test-456"}'
```

### Check Session Storage

```bash
# List session files in S3
aws s3 ls s3://<SessionBucketName>/study-buddy-sessions/ --recursive
```

## 🔍 Debugging

### View Lambda Logs

```bash
# Watch CloudWatch logs
aws logs tail /aws/lambda/<ChatLambdaName> --follow
```

### Common Issues

**"Knowledge Base not configured"**

- Ensure `KNOWLEDGE_BASE_ID` env var is set on Lambda

**"No module named 'strands'"**

- Run `npm run install-deps` and redeploy

**"Access denied" for S3 Session Bucket**

- Check Lambda IAM role has S3 read/write permissions

**"Context window exceeded"**

- SlidingWindowConversationManager should handle this automatically
- Check that it's configured with `window_size=20`

## 📚 Resources

- [Strands Agents Documentation](https://strandsagents.com/latest/documentation/)
- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [Bedrock Knowledge Base Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [Lambda Python Runtime](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)

## 🎯 Next Steps

1. ✅ Deploy infrastructure with `npx cdk deploy`
2. ✅ Set `KNOWLEDGE_BASE_ID` environment variable
3. ✅ Upload study materials to `MaterialsBucketName`
4. ✅ Test the API endpoint
5. ✅ Integrate with frontend

---

**Questions?** The Lambda handler includes detailed inline comments explaining how each component works!

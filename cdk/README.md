# Study Buddy - AWS CDK Infrastructure

This CDK app deploys the complete serverless infrastructure for Study Buddy using **Strands Agents SDK** with Amazon Bedrock Knowledge Base integration.

## 🏗️ Architecture

```
┌─────────────────┐
│  React Frontend │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────────────┐
│  API Gateway (REST)     │
└────────┬────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│  Lambda (Strands Agent Handler)  │
│  ├─ Strands Agents SDK            │
│  ├─ BedrockModel (Claude 3.5 Haiku)│
│  ├─ S3SessionManager              │
│  └─ KB Retrieval Tool             │
└────────┬─────────────────────────┘
         │
         ├──────────────┬───────────────┬──────────────┐
         ▼              ▼               ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────┐
│ S3 Materials │ │ S3 Vector│ │ S3 Sessions  │ │ Bedrock  │
│    Bucket    │ │  Store   │ │   Bucket     │ │    KB    │
└──────────────┘ └──────────┘ └──────────────┘ └──────────┘
```

## 📋 Prerequisites

1. **AWS Account** with CLI configured
2. **AWS CDK** installed: `npm install -g aws-cdk`
3. **Python 3.12** installed
4. **Node.js 18+** and pnpm installed
5. **Bedrock Model Access**: Request access to Claude 3.5 Haiku in AWS Console

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

```bash
npx cdk deploy
```

**Note the outputs:**

- `MaterialsBucketName` - Upload your study materials here
- `SessionBucketName` - Auto-managed conversation storage
- `ApiUrl` - Your API endpoint
- `ChatLambdaName` - Lambda function name

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

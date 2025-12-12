# Study Buddy API Quick Reference

## 🎯 Overview

This stack provides two independent AI agents via API Gateway:

1. **Study Buddy** - Socratic tutoring for biology students
2. **Build Checker** - Security auditing for GitHub repositories

## 📡 Endpoints

Base URL: `https://{api-id}.execute-api.{region}.amazonaws.com/prod`

### Study Buddy Endpoints

| Method | Path         | Purpose                     |
| ------ | ------------ | --------------------------- |
| POST   | `/chat`      | Chat with Study Buddy agent |
| GET    | `/materials` | Get study materials JSON    |
| GET    | `/health`    | Health check                |

### Build Checker Endpoints

| Method | Path           | Purpose                          |
| ------ | -------------- | -------------------------------- |
| POST   | `/build-check` | Analyze repository build process |

## 💬 Study Buddy (`/chat`)

### Request

```json
{
  "message": "What is photosynthesis?",
  "sessionId": "student-123"
}
```

### Response

```json
{
  "response": "Photosynthesis is the process...",
  "sessionId": "student-123",
  "relevantMaterialId": "photosynthesis",
  "sources": [
    {
      "content": "...",
      "score": 0.95,
      "source": "s3://...",
      "documentName": "biology_textbook.pdf"
    }
  ]
}
```

### Features

- Socratic teaching method (guides with questions)
- Knowledge Base grounding for accuracy
- Session persistence across conversations
- Adaptive teaching (question mode vs practice mode)
- Material recommendations

### Example Usage

```bash
# Bash
curl -X POST https://your-api-url/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain cellular respiration",
    "sessionId": "user-456"
  }'

# Python
import requests

response = requests.post(
    "https://your-api-url/chat",
    json={
        "message": "What are the stages of mitosis?",
        "sessionId": "user-789"
    }
)
print(response.json()["response"])
```

## 🔍 Build Checker (`/build-check`)

### Request

```json
{
  "repository": "awslabs/aws-cdk"
}
```

### Response

```json
{
  "repository": "awslabs/aws-cdk",
  "hasBuildProcess": true,
  "buildSystemsFound": ["GitHub Actions"],
  "confidenceLevel": "high",
  "evidence": [".github/workflows/build.yml: Comprehensive CI/CD"],
  "recommendations": [
    "Add automated security scanning",
    "Implement staging deployments"
  ],
  "summary": "Repository has robust build automation..."
}
```

### Features

- Detects 10+ CI/CD systems
- Identifies project types (CDK, frontend, etc.)
- Provides confidence scoring
- Security-focused recommendations
- Evidence-based analysis

### Example Usage

```bash
# Bash
curl -X POST https://your-api-url/build-check \
  -H "Content-Type: application/json" \
  -d '{"repository": "TeslaFreak/study-buddy"}'

# Python
import requests

response = requests.post(
    "https://your-api-url/build-check",
    json={"repository": "awslabs/strands"}
)

result = response.json()
if result["hasBuildProcess"]:
    print(f"✅ Build automation found: {result['buildSystemsFound']}")
else:
    print("❌ No build process detected")
    print("Recommendations:")
    for rec in result["recommendations"]:
        print(f"  - {rec}")
```

## ⚙️ Configuration

### Study Buddy Environment Variables

```bash
KNOWLEDGE_BASE_ID=BOHUN6SA6J
SESSION_BUCKET=study-buddy-sessions-xyz
AWS_REGION=us-east-1
```

### Build Checker Environment Variables

```bash
GITHUB_TOKEN=ghp_your_token_here
AWS_REGION=us-east-1
```

## 🚀 Quick Start

### 1. Get API URL

```bash
# After deployment
aws cloudformation describe-stacks \
  --stack-name StudyBuddyStack \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text
```

### 2. Test Study Buddy

```bash
API_URL=$(aws cloudformation describe-stacks ...)

curl -X POST $API_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!", "sessionId": "test-123"}'
```

### 3. Test Build Checker

```bash
curl -X POST $API_URL/build-check \
  -H "Content-Type: application/json" \
  -d '{"repository": "awslabs/aws-cdk"}'
```

## 🔐 Security Best Practices

### Production Checklist

- [ ] Store GitHub token in AWS Secrets Manager
- [ ] Implement API authentication (API keys or Cognito)
- [ ] Enable CloudWatch logging and monitoring
- [ ] Set up CloudWatch alarms for errors
- [ ] Use least-privilege IAM roles
- [ ] Enable X-Ray tracing for debugging
- [ ] Implement rate limiting
- [ ] Add request validation

### Secrets Manager Integration

Update Lambda to fetch GitHub token from Secrets Manager:

```python
import boto3
import json

secrets_client = boto3.client('secretsmanager')

def get_github_token():
    response = secrets_client.get_secret_value(
        SecretId='github-token'
    )
    return json.loads(response['SecretString'])['token']

GITHUB_TOKEN = get_github_token()
```

## 📊 Monitoring

### CloudWatch Metrics

Study Buddy:

- `Lambda Invocations` - Number of chat requests
- `Duration` - Response time
- `Errors` - Failed requests
- Custom: `SessionCount` - Active sessions

Build Checker:

- `Lambda Invocations` - Repository checks
- `Duration` - Analysis time (typically 30-60s)
- `Errors` - Failed analyses
- Custom: `RepositoriesChecked` - Total analyzed

### Useful CloudWatch Insights Queries

```sql
# Study Buddy - Average response time by session
fields @timestamp, sessionId, @duration
| filter @message like /session/
| stats avg(@duration) by sessionId

# Build Checker - Repositories without builds
fields @timestamp, repository, hasBuildProcess
| filter hasBuildProcess = false
| stats count() by repository
```

## 💰 Cost Optimization

### Study Buddy

- Use Haiku for cost-effective responses (~$15/10K queries)
- Implement caching for common questions
- Set reasonable session TTL (30 days)
- Monitor KB retrieval costs

### Build Checker

- Batch repository analyses
- Cache results for repositories (update weekly)
- Use public repos to avoid API costs
- Consider reserved Lambda capacity for high volume

## 🐛 Troubleshooting

### Study Buddy Issues

| Issue                  | Cause              | Solution                         |
| ---------------------- | ------------------ | -------------------------------- |
| No KB results          | Invalid KB ID      | Check KNOWLEDGE_BASE_ID env var  |
| Session not persisting | S3 permissions     | Verify Lambda role has S3 access |
| Slow responses         | Large KB retrieval | Reduce numberOfResults in query  |

### Build Checker Issues

| Issue             | Cause                    | Solution                            |
| ----------------- | ------------------------ | ----------------------------------- |
| Rate limit errors | Too many GitHub requests | Implement request throttling        |
| Timeout           | Large repository         | Increase Lambda timeout             |
| Permission denied | Invalid GitHub token     | Update token with proper scopes     |
| MCP server failed | Node.js not bundled      | Check Lambda bundling configuration |

## 📚 Additional Resources

- [Strands Agents Documentation](https://github.com/awslabs/strands)
- [Build Checker Full README](BUILD_CHECKER_README.md)
- [CDK Stack README](../README.md)
- [Model Context Protocol](https://modelcontextprotocol.io/)

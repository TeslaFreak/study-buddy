# Build Process Security Checker

## Overview

This Lambda function implements a security auditing agent that uses the Strands Agents SDK with the official GitHub MCP server to analyze repositories for automated build and deployment processes.

## Purpose

As part of organizational security and best practices initiatives, this agent helps:

- **Identify repositories lacking automated builds** - Flag projects with manual deployment processes
- **Assess build maturity** - Evaluate the completeness of CI/CD implementations
- **Provide actionable recommendations** - Suggest improvements for build automation
- **Document evidence** - Collect specific files and configurations as proof

## Architecture

```
API Gateway → Lambda (Python 3.11) → Strands Agent → GitHub MCP Server → GitHub API
                                    ↓
                              Bedrock (Claude 3.5 Sonnet)
```

### Key Components

1. **Strands Agent**: Orchestrates the analysis workflow
2. **GitHub MCP Server**: Provides tools to access GitHub repositories via the official MCP server
3. **Amazon Bedrock**: Powers the AI analysis with Claude 3.5 Sonnet
4. **Structured Output**: Uses Pydantic models for consistent response formatting

## Capabilities

### Build System Detection

The agent can identify various CI/CD systems:

- **GitHub Actions** - `.github/workflows/*.yml`
- **AWS CDK Pipelines** - CDK Pipeline constructs in stack files
- **GitLab CI** - `.gitlab-ci.yml`
- **CircleCI** - `.circleci/config.yml`
- **Jenkins** - `Jenkinsfile`
- **Travis CI** - `.travis.yml`
- **Azure Pipelines** - `azure-pipelines.yml`
- **AWS CodeBuild** - `buildspec.yml`
- And more...

### Project Type Recognition

Analyzes different project structures:

- **AWS CDK Projects** - Infrastructure as Code with pipeline automation
- **Frontend Apps** - React, Vue, Vite, Next.js projects
- **Backend APIs** - Node.js, Python, Go services
- **Containerized Apps** - Docker-based deployments
- **Terraform** - Infrastructure automation
- **Serverless** - Lambda, SAM applications

## API Usage

### Endpoint

```
POST /build-check
```

### Request

```json
{
  "repository": "owner/repo-name"
}
```

### Response

```json
{
  "repository": "owner/repo-name",
  "hasBuildProcess": true,
  "buildSystemsFound": ["GitHub Actions", "AWS CDK Pipelines"],
  "confidenceLevel": "high",
  "evidence": [
    ".github/workflows/deploy.yml: Automated deployment workflow",
    "lib/pipeline-stack.ts: CDK Pipeline with self-mutating deployment"
  ],
  "recommendations": [
    "Add automated security scanning (SAST/DAST)",
    "Implement multi-stage deployments (dev → staging → prod)",
    "Consider adding approval gates for production"
  ],
  "summary": "Repository has robust build automation with GitHub Actions and CDK Pipelines. Well-established processes with opportunities for enhanced security."
}
```

### Response Fields

- `hasBuildProcess` (boolean): Whether automated build/deployment exists
- `buildSystemsFound` (array): List of detected CI/CD systems
- `confidenceLevel` (string): "high", "medium", or "low"
- `evidence` (array): Specific files and configurations found
- `recommendations` (array): Actionable improvement suggestions
- `summary` (string): Executive summary of findings

## Environment Variables

| Variable       | Description                                 | Required                   |
| -------------- | ------------------------------------------- | -------------------------- |
| `GITHUB_TOKEN` | GitHub Personal Access Token for API access | Yes                        |
| `AWS_REGION`   | AWS region for Bedrock access               | No (defaults to us-east-1) |

## CDK Configuration

Set the GitHub token in CDK context:

```bash
# Set in cdk.json
{
  "context": {
    "githubToken": "ghp_your_token_here"
  }
}

# Or via CLI
cdk deploy -c githubToken=ghp_your_token_here
```

## GitHub Token Requirements

The GitHub token needs:

- `repo` scope for private repositories
- `public_repo` scope for public repositories only

Create a token at: https://github.com/settings/tokens

## Example Use Cases

### 1. Security Audit Dashboard

```typescript
// Audit multiple repositories
const repos = ["org/frontend", "org/backend", "org/infra"];
const results = await Promise.all(
  repos.map((repo) =>
    fetch(`${API_URL}/build-check`, {
      method: "POST",
      body: JSON.stringify({ repository: repo }),
    }).then((r) => r.json())
  )
);

// Filter repos without builds
const noBuildProcess = results.filter((r) => !r.hasBuildProcess);
console.log(`${noBuildProcess.length} repos need build automation`);
```

### 2. Pre-Deployment Validation

```bash
# Check if repo has build process before onboarding
curl -X POST https://api-url/build-check \
  -H "Content-Type: application/json" \
  -d '{"repository": "myorg/new-project"}'
```

### 3. Compliance Reporting

Generate reports for security compliance:

- Track which teams have proper CI/CD
- Monitor adoption of build automation
- Identify high-risk manual deployments

## Limitations

- **Rate Limits**: Subject to GitHub API rate limits
- **Private Repos**: Requires appropriate token permissions
- **Large Repos**: May timeout on extremely large repositories (increase Lambda timeout if needed)
- **Analysis Depth**: Focuses on configuration files; doesn't execute or validate build scripts

## Error Handling

Common errors and solutions:

| Error                                       | Cause                 | Solution                                           |
| ------------------------------------------- | --------------------- | -------------------------------------------------- |
| `Repository must be in format 'owner/repo'` | Invalid format        | Use `owner/repo` format                            |
| `GitHub API rate limit`                     | Too many requests     | Wait or use authenticated token with higher limits |
| `Timeout`                                   | Large repository      | Increase Lambda timeout or optimize analysis       |
| `Permission denied`                         | Invalid/expired token | Update GitHub token with proper scopes             |

## Development

### Local Testing

```bash
# Install dependencies
cd cdk/lambda
pip install -r requirements.txt

# Set environment variables
export GITHUB_TOKEN=ghp_your_token
export AWS_REGION=us-east-1

# Test locally (requires AWS credentials)
python -c "
from build_checker_handler import handler
event = {'body': '{\"repository\": \"owner/repo\"}'}
print(handler(event, None))
"
```

### Deployment

```bash
cd cdk
npm run build
cdk deploy -c githubToken=ghp_your_token
```

## Security Considerations

1. **Token Security**: Store GitHub token in AWS Secrets Manager for production
2. **Least Privilege**: Use read-only GitHub tokens
3. **Network Security**: Lambda runs in VPC if configured
4. **Audit Logging**: All API calls are logged to CloudWatch
5. **Data Privacy**: No repository code is stored; only metadata analyzed

## Future Enhancements

- [ ] Support for additional CI/CD systems (Spinnaker, ArgoCD)
- [ ] Deeper analysis of pipeline quality (testing coverage, deployment frequency)
- [ ] Integration with AWS Security Hub for findings
- [ ] Slack/email notifications for repos without builds
- [ ] Historical tracking of build adoption trends
- [ ] Support for monorepo analysis
- [ ] Custom ruleset configuration per organization

## Related Documentation

- [Strands Agents SDK](https://github.com/awslabs/strands)
- [GitHub MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/github)
- [AWS CDK Pipelines](https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.pipelines-readme.html)
- [GitHub Actions](https://docs.github.com/en/actions)

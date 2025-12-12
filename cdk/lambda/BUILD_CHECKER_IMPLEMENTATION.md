# Build Checker Lambda - Implementation Summary

## What Was Created

### 1. New Lambda Handler

**File**: `cdk/lambda/build_checker_handler.py`

A complete Strands Agent implementation that:

- Uses the official GitHub MCP server to access repositories
- Analyzes project structures for CI/CD configurations
- Identifies build systems (GitHub Actions, CDK Pipelines, Jenkins, etc.)
- Provides structured security recommendations
- Uses Claude 3.5 Sonnet for sophisticated analysis

### 2. CDK Stack Updates

**File**: `cdk/lib/study-buddy-stack.ts`

Added:

- New Lambda function with appropriate IAM role
- Bedrock model invocation permissions
- Node.js installation in bundling (for GitHub MCP server)
- API Gateway `/build-check` endpoint
- CloudFormation outputs for the new Lambda
- Longer timeout (300s) and more memory (1024MB) for repo analysis

### 3. Updated Dependencies

**File**: `cdk/lambda/requirements.txt`

Added:

- `mcp>=1.0.0` - Model Context Protocol SDK for MCP server integration

### 4. Documentation

**Files**:

- `cdk/lambda/BUILD_CHECKER_README.md` - Comprehensive Lambda documentation
- `cdk/lambda/test_build_checker.py` - Test script for the API
- `cdk/README.md` - Updated with Build Checker section

## Key Features

### Agent Implementation

- **Strands Agent**: Uses the same patterns as your Study Buddy agent
- **GitHub MCP Integration**: Leverages the official `@modelcontextprotocol/server-github` npm package
- **Structured Output**: Returns typed Pydantic models with validation
- **Comprehensive Analysis**: Checks for 10+ different CI/CD systems
- **Project Type Detection**: Identifies CDK, frontend, backend, containerized apps

### Architecture Patterns

- **Same Lambda patterns**: Follows your existing agent_handler.py structure
- **MCP Client Usage**: Uses `MCPClient` with `stdio_client` for GitHub server
- **No session management**: Each request is independent (no S3 sessions needed)
- **Higher timeout**: 5 minutes for GitHub API calls and deep analysis

### Security & Best Practices

- **GitHub Token**: Configurable via CDK context (secure in production with Secrets Manager)
- **Least Privilege**: Read-only GitHub access
- **Error Handling**: Graceful failures with detailed error messages
- **CORS Enabled**: Frontend-ready API endpoints

## How It Works

1. **Request received**: API Gateway forwards to Lambda
2. **Agent creation**: Initializes Strands Agent with GitHub MCP tools
3. **MCP Server**: Launches Node.js GitHub MCP server in-process
4. **Repository analysis**: Agent uses MCP tools to explore repo structure
5. **AI analysis**: Claude 3.5 Sonnet analyzes findings
6. **Structured response**: Returns typed JSON with assessment

## Deployment Steps

### 1. Set GitHub Token

```bash
export GITHUB_TOKEN=ghp_your_token_here
```

Or in `cdk.json`:

```json
{
  "context": {
    "githubToken": "ghp_your_token_here"
  }
}
```

### 2. Deploy

```bash
cd cdk
npm run build
cdk deploy -c githubToken=$GITHUB_TOKEN
```

### 3. Test

```bash
cd lambda
python test_build_checker.py awslabs/aws-cdk
```

## Differences from Study Buddy Lambda

| Aspect                   | Study Buddy         | Build Checker       |
| ------------------------ | ------------------- | ------------------- |
| **Purpose**              | Socratic tutoring   | Security auditing   |
| **Model**                | Claude 3.5 Haiku    | Claude 3.5 Sonnet   |
| **Temperature**          | 0.7 (creative)      | 0.3 (consistent)    |
| **Session Management**   | S3SessionManager    | None (stateless)    |
| **External Integration** | Bedrock KB          | GitHub MCP Server   |
| **Timeout**              | 60 seconds          | 300 seconds         |
| **Memory**               | 512 MB              | 1024 MB             |
| **Tools**                | Custom KB retrieval | GitHub MCP tools    |
| **Response Type**        | Conversational      | Structured analysis |

## Cost Considerations

Per repository analysis:

- **Lambda execution**: ~$0.0003 (300s @ 1024MB ARM64)
- **Bedrock (Sonnet)**: ~$0.015 per analysis (avg 5K input, 2K output tokens)
- **GitHub API**: Free (within rate limits)

**Total per analysis**: ~$0.015 (1.5 cents)

For 1000 repositories/month: ~$15

## Environment Variables

| Variable       | Required | Default   | Description                  |
| -------------- | -------- | --------- | ---------------------------- |
| `GITHUB_TOKEN` | Yes      | -         | GitHub personal access token |
| `AWS_REGION`   | No       | us-east-1 | AWS region for Bedrock       |

## Future Enhancements

Potential improvements:

- [ ] Batch repository analysis endpoint
- [ ] Historical tracking of build adoption
- [ ] Integration with AWS Security Hub
- [ ] Slack/email notifications for non-compliant repos
- [ ] Custom ruleset configuration
- [ ] Support for additional VCS providers (GitLab, Bitbucket)
- [ ] Pipeline quality scoring beyond presence/absence

## Testing Recommendations

1. **Public repos first**: Test with public repos to validate functionality
2. **Various project types**: Test CDK, frontend, backend, Terraform projects
3. **Edge cases**: Test repos without builds, incomplete setups, etc.
4. **Error scenarios**: Test invalid repo names, rate limiting, etc.

## Related Documentation

- [Strands Agents SDK](https://github.com/awslabs/strands)
- [GitHub MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/github)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Build Checker README](BUILD_CHECKER_README.md)

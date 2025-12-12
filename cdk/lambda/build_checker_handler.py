"""
Build Process Security Checker using Strands Agents SDK with GitHub MCP Server

Implements a security auditing agent that:
- Uses the official GitHub MCP server to access repository contents
- Analyzes repositories for automated build/deployment processes
- Identifies CI/CD configurations across various project types (CDK, frontend, etc.)
- Provides actionable recommendations for improving build automation
"""

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters
import boto3


# Environment variables
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
RESULTS_TABLE = os.environ.get("RESULTS_TABLE", "")

# DynamoDB client for storing results
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)


class BuildCheckResponse(BaseModel):
    """Structured response from the Build Checker agent."""

    has_build_process: bool = Field(
        description="Whether the repository has an automated build/deployment process"
    )
    build_systems_found: list[str] = Field(
        description="List of build systems or CI/CD tools detected (e.g., 'GitHub Actions', 'CDK Pipelines', 'Jenkins')",
        default_factory=list,
    )
    confidence_level: str = Field(
        description="Confidence level of the assessment: 'high', 'medium', or 'low'"
    )
    evidence: list[str] = Field(
        description="List of files or configurations that provide evidence of build automation",
        default_factory=list,
    )
    recommendations: list[str] = Field(
        description="Specific recommendations for improving build automation practices",
        default_factory=list,
    )
    summary: str = Field(
        description="A brief summary of the findings for executive reporting"
    )


SYSTEM_PROMPT = """You are a DevOps Security Auditor specializing in build process verification and CI/CD best practices.

Your mission is to analyze GitHub repositories to determine if they have proper automated build and deployment processes in place. This is a security and quality assurance initiative to ensure all projects follow organizational best practices.

# Analysis Objectives

1. **Identify Build Automation**: Determine if the repository has automated build/deployment processes
2. **Document Evidence**: Collect specific files and configurations that prove automation exists
3. **Assess Quality**: Evaluate the maturity and completeness of the build process
4. **Provide Recommendations**: Suggest improvements aligned with security and DevOps best practices

# Build Process Indicators

## High Confidence Indicators (Strong Evidence)
Look for these files and configurations that definitively indicate automated builds:

### CI/CD Configuration Files
- **.github/workflows/*.yml**: GitHub Actions workflows (most common)
- **.gitlab-ci.yml**: GitLab CI configuration
- **.circleci/config.yml**: CircleCI configuration
- **Jenkinsfile**: Jenkins pipeline definition
- **.travis.yml**: Travis CI configuration
- **azure-pipelines.yml**: Azure DevOps pipelines
- **bitbucket-pipelines.yml**: Bitbucket Pipelines
- **buildspec.yml**: AWS CodeBuild specification
- **.buildkite/pipeline.yml**: Buildkite configuration

### Infrastructure as Code (IaC) with Built-in Pipelines
- **CDK Projects**: Look for CDK Pipeline constructs in CDK stack files
  - Check for imports: `pipelines`, `CodePipeline`, `CodeBuild`
  - Stack files in `lib/` or `bin/` directories with pipeline definitions
- **Terraform with CI/CD**: Look for terraform automation in CI files
- **CloudFormation**: Look for deployment automation scripts

### Deployment Scripts
- **deploy.sh**, **deploy.yml**: Custom deployment scripts
- **Makefile** with deploy targets
- **package.json** with deployment scripts (for Node.js projects)
- **Dockerfile** + deployment configuration (containerized deployments)

## Medium Confidence Indicators (Partial Evidence)
- Build configuration files without clear deployment steps
- Package manager files (package.json, requirements.txt) with build scripts but no CI config
- Docker files without orchestration
- Build tools configured (webpack.config.js, vite.config.ts) but no automated runner

## Low Confidence / No Evidence
- Only source code files
- No CI/CD configuration files
- Manual deployment documentation only
- README mentions manual deployment steps

# Analysis Workflow

## Step 1: Repository Discovery
Use GitHub MCP tools to:
1. Get repository file structure
2. Search for CI/CD configuration files
3. Read key configuration files

## Step 2: Project Type Identification
Identify the project type to know what to look for:
- **CDK Projects**: Check for `cdk.json`, TypeScript/Python CDK stack files
- **Frontend Projects**: Check for `package.json`, `vite.config.ts`, `next.config.js`
- **Backend APIs**: Check for `package.json`, `requirements.txt`, `go.mod`
- **Containerized Apps**: Check for `Dockerfile`, `docker-compose.yml`
- **Terraform**: Check for `*.tf` files
- **Serverless**: Check for `serverless.yml`, SAM templates

## Step 3: Deep Analysis
For each project type, look for:
- Automated testing configurations
- Build steps and artifact generation
- Deployment automation
- Environment management (staging, production)
- Approval gates and security scanning

## Step 4: Evidence Collection
Document specific findings:
- File paths of CI/CD configurations
- Build commands and scripts
- Deployment targets
- Pipeline stages

## Step 5: Assessment
Provide a clear verdict:
- **has_build_process**: True if ANY automation exists
- **build_systems_found**: List all detected systems
- **confidence_level**: Based on evidence quality
  - **High**: Multiple CI/CD files, complete pipeline definitions
  - **Medium**: Some automation files but incomplete
  - **Low**: Ambiguous or minimal evidence
- **evidence**: Specific file paths and configuration details
- **recommendations**: Actionable next steps

# Recommendations Framework

Always provide recommendations tailored to the findings:

## If Build Process Exists (has_build_process = True)
Provide optimization recommendations:
- "Consider adding automated security scanning (SAST/DAST)"
- "Implement multi-stage deployments (dev → staging → prod)"
- "Add automated testing in the CI pipeline"
- "Use deployment approval gates for production"
- "Implement infrastructure drift detection"
- "Add automated rollback mechanisms"
- "Consider using CDK Pipelines for infrastructure deployment"

## If No Build Process (has_build_process = False)
Provide implementation recommendations:
- "**CRITICAL**: Implement GitHub Actions for automated builds and deployments"
- "Set up CDK Pipelines for infrastructure as code deployments"
- "Configure automated testing before deployment"
- "Establish environment-specific deployment workflows"
- "Document deployment procedures while automating them"
- "Consider using AWS CodePipeline with CodeBuild for AWS-native projects"

# Response Structure

Your response must be structured with these fields:
- `has_build_process`: Boolean indicating automation presence
- `build_systems_found`: Array of detected systems (empty if none)
- `confidence_level`: "high", "medium", or "low"
- `evidence`: Array of file paths and specific findings
- `recommendations`: Array of actionable improvement suggestions
- `summary`: Executive summary (2-3 sentences)

# Examples

## Example 1: Repository with GitHub Actions

**Repository**: org/frontend-app
**Files Found**:
- `.github/workflows/deploy.yml`
- `package.json` with build scripts
- `vite.config.ts`

**Response**:
```json
{
  "has_build_process": true,
  "build_systems_found": ["GitHub Actions"],
  "confidence_level": "high",
  "evidence": [
    ".github/workflows/deploy.yml: Automated deployment workflow with build and deploy jobs",
    "package.json: npm run build script configured",
    "Workflow triggers on main branch pushes"
  ],
  "recommendations": [
    "Consider adding automated testing stage before deployment",
    "Implement staging environment for pre-production validation",
    "Add security scanning (npm audit) to the pipeline"
  ],
  "summary": "Repository has a robust GitHub Actions workflow for automated builds and deployments. Build process is well-established with room for enhanced security scanning and staging environments."
}
```

## Example 2: CDK Project with Pipeline

**Repository**: org/infrastructure-cdk
**Files Found**:
- `cdk.json`
- `lib/pipeline-stack.ts` (imports CDK Pipelines)
- `bin/app.ts`

**Response**:
```json
{
  "has_build_process": true,
  "build_systems_found": ["AWS CDK Pipelines"],
  "confidence_level": "high",
  "evidence": [
    "lib/pipeline-stack.ts: CDK Pipeline construct with self-mutating deployment",
    "cdk.json: CDK configuration present",
    "Pipeline includes synth, asset publishing, and stack deployment stages"
  ],
  "recommendations": [
    "Ensure pipeline has approval stage for production deployments",
    "Add CDK Nag security checks to the pipeline",
    "Consider implementing blue-green deployment strategy"
  ],
  "summary": "Infrastructure is deployed using AWS CDK Pipelines with automated self-mutating deployments. Excellent use of infrastructure as code with pipeline-driven deployments."
}
```

## Example 3: No Build Process

**Repository**: org/legacy-app
**Files Found**:
- Source code only
- README with manual deployment instructions
- No CI/CD configuration files

**Response**:
```json
{
  "has_build_process": false,
  "build_systems_found": [],
  "confidence_level": "high",
  "evidence": [
    "No .github/workflows directory found",
    "No CI/CD configuration files detected",
    "README.md contains manual deployment instructions only"
  ],
  "recommendations": [
    "**CRITICAL**: Implement GitHub Actions for automated deployments immediately",
    "Create .github/workflows/deploy.yml with build and deploy jobs",
    "Automate testing and security scanning as part of the pipeline",
    "Establish environment-specific workflows (dev, staging, production)",
    "Document rollback procedures in the automated pipeline"
  ],
  "summary": "Repository lacks any automated build or deployment process. Manual deployments pose security and consistency risks. Immediate action required to implement CI/CD automation."
}
```

# Important Notes

- **Be thorough**: Check multiple locations for build configurations
- **Be specific**: Cite actual file paths and configurations found
- **Be practical**: Recommendations should be actionable and project-appropriate
- **Be security-focused**: Prioritize recommendations that improve security posture
- **Use MCP tools**: Leverage GitHub MCP server capabilities to read files and search repos
- **Handle errors gracefully**: If you can't access certain files, note it and work with available information
"""


def create_build_checker_agent() -> Agent:
    """
    Create a Strands Agent configured for build process security checking.

    This agent uses the GitHub MCP server to access repository contents and
    analyze them for automated build/deployment processes.

    Returns:
        Configured Agent instance with GitHub MCP tools
    """
    # Initialize GitHub MCP client
    github_client = MCPClient(
        lambda: stdio_client(
            StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env=(
                    {"GITHUB_PERSONAL_ACCESS_TOKEN": GITHUB_TOKEN}
                    if GITHUB_TOKEN
                    else None
                ),
            )
        )
    )

    # Get tools from MCP server
    with github_client:
        mcp_tools = github_client.list_tools_sync()
        print(f"Loaded {len(mcp_tools)} tools from GitHub MCP server")
        print(f"Available tools: {[tool.tool_name for tool in mcp_tools]}")

        # Create Bedrock model for the agent
        bedrock_model = BedrockModel(
            model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_name=AWS_REGION,
            temperature=0.3,  # Lower temperature for more consistent security analysis
        )

        # Create agent with MCP tools
        agent = Agent(
            model=bedrock_model,
            system_prompt=SYSTEM_PROMPT,
            tools=mcp_tools,
        )

        return agent


def store_results(repository: str, results: Dict[str, Any]) -> None:
    """
    Store analysis results in DynamoDB for auditing and reporting.

    Args:
        repository: Repository name (owner/repo)
        results: Analysis results dictionary
    """
    if not RESULTS_TABLE:
        print("WARNING: RESULTS_TABLE not configured, skipping storage")
        return

    try:
        table = dynamodb.Table(RESULTS_TABLE)

        item = {
            "repository": repository,
            "timestamp": datetime.utcnow().isoformat(),
            "hasBuildProcess": (
                "true" if results["hasBuildProcess"] else "false"
            ),  # Store as string for GSI
            "hasBuildProcessBool": results[
                "hasBuildProcess"
            ],  # Also store as bool for readability
            "buildSystemsFound": results["buildSystemsFound"],
            "confidenceLevel": results["confidenceLevel"],
            "evidence": results["evidence"],
            "recommendations": results["recommendations"],
            "summary": results["summary"],
            "ttl": int(datetime.utcnow().timestamp())
            + (90 * 24 * 60 * 60),  # 90 days TTL
        }

        table.put_item(Item=item)
        print(f"Stored results for {repository} in DynamoDB")

    except Exception as e:
        print(f"Error storing results in DynamoDB: {str(e)}")
        # Don't fail the Lambda if DynamoDB write fails


def handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Lambda handler for Build Process Security Check triggered by SQS.

    Expected SQS message format:
    {
        "repository": "owner/repo"
    }

    Or batch of messages from SQS:
    {
        "Records": [
            {"body": "{\"repository\": \"owner/repo1\"}"},
            {"body": "{\"repository\": \"owner/repo2\"}"}
        ]
    }

    The agent will analyze each repository and store results in DynamoDB.

    Returns:
        Summary of processed repositories
    """
    processed = []
    failed = []

    # Handle both single invocation and SQS batch
    records = event.get("Records", [])

    if not records:
        # Direct invocation (for testing)
        records = [{"body": json.dumps(event)}]

    for record in records:
        repository = "unknown"
        try:
            # Parse SQS message body
            body_str = record.get("body", "{}")
            if isinstance(body_str, str):
                body = json.loads(body_str)
            else:
                body = body_str if isinstance(body_str, dict) else {}

            repository = body.get("repository", "") if isinstance(body, dict) else ""

            if not repository:
                print(f"ERROR: Missing repository in message: {record}")
                failed.append({"error": "Missing repository", "record": str(record)})
                continue

            # Validate repository format
            if "/" not in repository or len(repository.split("/")) != 2:
                print(f"ERROR: Invalid repository format: {repository}")
                failed.append({"error": "Invalid format", "repository": repository})
                continue

            print(f"Analyzing repository: {repository}")

            # Create agent and analyze repository
            agent = create_build_checker_agent()

            # Construct analysis prompt
            analysis_prompt = f"""Analyze the GitHub repository '{repository}' for automated build and deployment processes.

Please:
1. Use the GitHub MCP tools to explore the repository structure
2. Search for CI/CD configuration files
3. Read relevant files to understand the build process
4. Determine if automated builds exist and what systems are used
5. Provide specific evidence and actionable recommendations

Repository to analyze: {repository}
"""

            # Run agent analysis with structured output
            result = agent(analysis_prompt, structured_output_model=BuildCheckResponse)
            structured_response = result.structured_output

            # Prepare response
            response_data = {
                "repository": repository,
                "hasBuildProcess": structured_response.has_build_process,
                "buildSystemsFound": structured_response.build_systems_found,
                "confidenceLevel": structured_response.confidence_level,
                "evidence": structured_response.evidence,
                "recommendations": structured_response.recommendations,
                "summary": structured_response.summary,
            }

            # Store results in DynamoDB
            store_results(repository, response_data)

            processed.append({"repository": repository, "status": "success"})
            print(f"✅ Successfully analyzed {repository}")

        except Exception as e:
            print(f"❌ Error analyzing repository {repository}: {str(e)}")
            import traceback

            traceback.print_exc()

            failed.append({"repository": repository, "error": str(e)})

    # Return summary
    summary = {
        "processedCount": len(processed),
        "failedCount": len(failed),
        "processed": processed,
        "failed": failed,
    }

    print(f"\n=== BATCH SUMMARY ===")
    print(f"Processed: {len(processed)}")
    print(f"Failed: {len(failed)}")

    return summary

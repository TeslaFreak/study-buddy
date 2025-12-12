#!/usr/bin/env python3
"""
Submit repositories to the Build Checker SQS queue for analysis.

Usage:
    # Single repository
    python submit_repos.py awslabs/aws-cdk

    # Multiple repositories
    python submit_repos.py awslabs/aws-cdk awslabs/strands

    # From file (one repo per line)
    python submit_repos.py --file repos.txt

    # With custom queue URL
    python submit_repos.py --queue-url https://sqs.us-east-1.amazonaws.com/123/build-check-queue awslabs/aws-cdk
"""

import sys
import argparse
import json
import boto3
from typing import List


def get_queue_url_from_stack(stack_name: str = "StudyBuddyStack") -> str:
    """
    Get the SQS queue URL from CloudFormation stack outputs.

    Args:
        stack_name: Name of the CloudFormation stack

    Returns:
        Queue URL
    """
    cf = boto3.client("cloudformation")

    try:
        response = cf.describe_stacks(StackName=stack_name)
        outputs = response["Stacks"][0]["Outputs"]

        for output in outputs:
            if output["OutputKey"] == "BuildCheckQueueUrl":
                return output["OutputValue"]

        raise Exception(f"BuildCheckQueueUrl not found in stack {stack_name} outputs")

    except Exception as e:
        print(f"Error getting queue URL from stack: {str(e)}")
        print("Please provide --queue-url manually")
        sys.exit(1)


def submit_repositories(queue_url: str, repositories: List[str]) -> dict:
    """
    Submit repositories to the SQS queue for analysis.

    Args:
        queue_url: SQS queue URL
        repositories: List of repository names (owner/repo format)

    Returns:
        Summary of submitted repositories
    """
    sqs = boto3.client("sqs")

    submitted = []
    failed = []

    for repo in repositories:
        # Validate format
        if "/" not in repo or len(repo.split("/")) != 2:
            print(f"❌ Invalid format: {repo} (must be 'owner/repo')")
            failed.append({"repository": repo, "error": "Invalid format"})
            continue

        try:
            message = {"repository": repo}

            response = sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message),
                MessageAttributes={
                    "Repository": {"StringValue": repo, "DataType": "String"}
                },
            )

            submitted.append({"repository": repo, "messageId": response["MessageId"]})
            print(f"✅ Queued: {repo} (Message ID: {response['MessageId']})")

        except Exception as e:
            print(f"❌ Failed to queue {repo}: {str(e)}")
            failed.append({"repository": repo, "error": str(e)})

    return {
        "submitted": submitted,
        "failed": failed,
        "submittedCount": len(submitted),
        "failedCount": len(failed),
    }


def read_repos_from_file(filepath: str) -> List[str]:
    """
    Read repository names from a file (one per line).

    Args:
        filepath: Path to file containing repository names

    Returns:
        List of repository names
    """
    try:
        with open(filepath, "r") as f:
            repos = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
        return repos
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {str(e)}")
        sys.exit(1)


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description="Submit repositories to Build Checker SQS queue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single repository
  %(prog)s awslabs/aws-cdk
  
  # Multiple repositories
  %(prog)s awslabs/aws-cdk awslabs/strands microsoft/vscode
  
  # From file
  %(prog)s --file repos.txt
  
  # Custom queue URL
  %(prog)s --queue-url https://sqs.us-east-1.amazonaws.com/123/queue awslabs/aws-cdk
        """,
    )

    parser.add_argument(
        "repositories", nargs="*", help="Repository names in owner/repo format"
    )

    parser.add_argument(
        "--file",
        "-f",
        dest="file",
        help="File containing repository names (one per line)",
    )

    parser.add_argument(
        "--queue-url",
        "-q",
        dest="queue_url",
        help="SQS queue URL (auto-detected from CloudFormation if not provided)",
    )

    parser.add_argument(
        "--stack-name",
        "-s",
        dest="stack_name",
        default="StudyBuddyStack",
        help="CloudFormation stack name (default: StudyBuddyStack)",
    )

    args = parser.parse_args()

    # Get repositories from args or file
    repositories = []

    if args.file:
        repositories.extend(read_repos_from_file(args.file))

    if args.repositories:
        repositories.extend(args.repositories)

    if not repositories:
        print("Error: No repositories specified")
        parser.print_help()
        sys.exit(1)

    # Get queue URL
    if args.queue_url:
        queue_url = args.queue_url
    else:
        print(f"Fetching queue URL from CloudFormation stack: {args.stack_name}")
        queue_url = get_queue_url_from_stack(args.stack_name)

    print(f"\nQueue URL: {queue_url}")
    print(f"Submitting {len(repositories)} repositories...\n")

    # Submit repositories
    result = submit_repositories(queue_url, repositories)

    # Print summary
    print("\n" + "=" * 60)
    print("SUBMISSION SUMMARY")
    print("=" * 60)
    print(f"✅ Successfully submitted: {result['submittedCount']}")
    print(f"❌ Failed: {result['failedCount']}")

    if result["failed"]:
        print("\nFailed repositories:")
        for item in result["failed"]:
            print(f"  - {item['repository']}: {item['error']}")

    print("\nRepositories are now queued for analysis.")
    print("Results will be stored in DynamoDB and can be queried later.")


if __name__ == "__main__":
    main()

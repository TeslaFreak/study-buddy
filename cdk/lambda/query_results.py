#!/usr/bin/env python3
"""
Query build check results from DynamoDB.

Usage:
    # Get results for a specific repository
    python query_results.py awslabs/aws-cdk

    # List all repositories without builds
    python query_results.py --no-builds

    # List all repositories with builds
    python query_results.py --has-builds

    # Export all results to JSON
    python query_results.py --export results.json

    # Get latest N results
    python query_results.py --latest 10
"""

import sys
import argparse
import json
import boto3
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal


# Custom JSON encoder for DynamoDB types
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def get_table_name_from_stack(stack_name: str = "StudyBuddyStack") -> str:
    """Get the DynamoDB table name from CloudFormation stack outputs."""
    cf = boto3.client("cloudformation")

    try:
        response = cf.describe_stacks(StackName=stack_name)
        outputs = response["Stacks"][0]["Outputs"]

        for output in outputs:
            if output["OutputKey"] == "ResultsTableName":
                return output["OutputValue"]

        raise Exception(f"ResultsTableName not found in stack {stack_name} outputs")

    except Exception as e:
        print(f"Error getting table name from stack: {str(e)}")
        print("Please provide --table-name manually")
        sys.exit(1)


def query_repository(table_name: str, repository: str) -> Optional[Dict[str, Any]]:
    """Query results for a specific repository (latest result)."""
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    try:
        response = table.query(
            KeyConditionExpression="repository = :repo",
            ExpressionAttributeValues={":repo": repository},
            ScanIndexForward=False,  # Sort descending by timestamp
            Limit=1,
        )

        if response["Items"]:
            return response["Items"][0]
        return None

    except Exception as e:
        print(f"Error querying repository {repository}: {str(e)}")
        return None


def query_by_build_status(
    table_name: str, has_build_process: bool
) -> List[Dict[str, Any]]:
    """Query all repositories by build process status using GSI."""
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    try:
        # Convert bool to string for querying (DynamoDB GSI uses string)
        status_str = "true" if has_build_process else "false"

        response = table.query(
            IndexName="BuildProcessIndex",
            KeyConditionExpression="hasBuildProcess = :status",
            ExpressionAttributeValues={":status": status_str},
            ScanIndexForward=False,  # Latest first
        )

        return response["Items"]

    except Exception as e:
        print(f"Error querying by build status: {str(e)}")
        return []


def scan_all_results(table_name: str) -> List[Dict[str, Any]]:
    """Scan all results from the table."""
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    try:
        items = []
        response = table.scan()
        items.extend(response["Items"])

        # Handle pagination
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response["Items"])

        return items

    except Exception as e:
        print(f"Error scanning table: {str(e)}")
        return []


def get_latest_results(table_name: str, limit: int) -> List[Dict[str, Any]]:
    """Get the latest N results across all repositories."""
    all_results = scan_all_results(table_name)

    # Sort by timestamp descending
    sorted_results = sorted(
        all_results, key=lambda x: x.get("timestamp", ""), reverse=True
    )

    return sorted_results[:limit]


def format_result(result: Dict[str, Any]) -> str:
    """Format a single result for display."""
    output = []
    output.append("=" * 80)
    output.append(f"Repository: {result['repository']}")
    output.append(f"Timestamp: {result.get('timestamp', 'N/A')}")
    output.append("=" * 80)

    # Handle both string and bool formats
    has_build = result.get("hasBuildProcessBool", result.get("hasBuildProcess"))
    if isinstance(has_build, str):
        has_build = has_build.lower() == "true"

    status = "✅ HAS BUILD PROCESS" if has_build else "❌ NO BUILD PROCESS"
    output.append(f"\nStatus: {status}")
    output.append(f"Confidence: {result.get('confidenceLevel', 'N/A').upper()}")

    if result.get("buildSystemsFound"):
        output.append("\nBuild Systems:")
        for system in result["buildSystemsFound"]:
            output.append(f"  • {system}")

    if result.get("evidence"):
        output.append("\nEvidence:")
        for item in result["evidence"]:
            output.append(f"  • {item}")

    output.append(f"\nSummary:")
    output.append(f"  {result.get('summary', 'N/A')}")

    if result.get("recommendations"):
        output.append("\nRecommendations:")
        for i, rec in enumerate(result["recommendations"], 1):
            output.append(f"  {i}. {rec}")

    output.append("")
    return "\n".join(output)


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description="Query build check results from DynamoDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "repository", nargs="?", help="Repository name to query (owner/repo format)"
    )

    parser.add_argument(
        "--no-builds",
        action="store_true",
        help="List all repositories without build processes",
    )

    parser.add_argument(
        "--has-builds",
        action="store_true",
        help="List all repositories with build processes",
    )

    parser.add_argument(
        "--latest", type=int, metavar="N", help="Get the latest N results"
    )

    parser.add_argument("--export", metavar="FILE", help="Export results to JSON file")

    parser.add_argument(
        "--table-name",
        "-t",
        dest="table_name",
        help="DynamoDB table name (auto-detected from CloudFormation if not provided)",
    )

    parser.add_argument(
        "--stack-name",
        "-s",
        dest="stack_name",
        default="StudyBuddyStack",
        help="CloudFormation stack name (default: StudyBuddyStack)",
    )

    args = parser.parse_args()

    # Get table name
    if args.table_name:
        table_name = args.table_name
    else:
        table_name = get_table_name_from_stack(args.stack_name)

    print(f"Table: {table_name}\n")

    # Execute query based on arguments
    results = []

    if args.repository:
        # Query specific repository
        result = query_repository(table_name, args.repository)
        if result:
            results = [result]
            print(format_result(result))
        else:
            print(f"No results found for repository: {args.repository}")

    elif args.no_builds:
        # Query repositories without builds
        results = query_by_build_status(table_name, False)
        print(f"Found {len(results)} repositories WITHOUT build processes:\n")
        for result in results:
            print(
                f"  • {result['repository']} (checked: {result.get('timestamp', 'N/A')})"
            )

    elif args.has_builds:
        # Query repositories with builds
        results = query_by_build_status(table_name, True)
        print(f"Found {len(results)} repositories WITH build processes:\n")
        for result in results:
            systems = ", ".join(result.get("buildSystemsFound", ["Unknown"]))
            print(
                f"  • {result['repository']} - {systems} (checked: {result.get('timestamp', 'N/A')})"
            )

    elif args.latest:
        # Get latest N results
        results = get_latest_results(table_name, args.latest)
        print(f"Latest {len(results)} results:\n")
        for result in results:
            status = "✅" if result.get("hasBuildProcess") else "❌"
            print(f"{status} {result['repository']} - {result.get('timestamp', 'N/A')}")

    else:
        # Default: scan all
        results = scan_all_results(table_name)
        print(f"Total results in table: {len(results)}\n")

        # Handle both string and bool formats for counting
        with_builds = sum(
            1
            for r in results
            if (
                r.get("hasBuildProcessBool")
                if "hasBuildProcessBool" in r
                else (
                    r.get("hasBuildProcess", "").lower() == "true"
                    if isinstance(r.get("hasBuildProcess"), str)
                    else r.get("hasBuildProcess")
                )
            )
        )
        without_builds = len(results) - with_builds

        print(f"  ✅ With builds: {with_builds}")
        print(f"  ❌ Without builds: {without_builds}")
        print("\nUse --help to see query options")

    # Export if requested
    if args.export and results:
        with open(args.export, "w") as f:
            json.dump(results, f, indent=2, cls=DecimalEncoder)
        print(f"\n✅ Exported {len(results)} results to {args.export}")


if __name__ == "__main__":
    main()

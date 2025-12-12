#!/usr/bin/env python3
"""
Example script to test the Build Process Security Checker

Usage:
    python test_build_checker.py <repository>

Example:
    python test_build_checker.py awslabs/aws-cdk
"""

import sys
import json
import requests
from typing import Dict, Any


def check_build_process(api_url: str, repository: str) -> Dict[str, Any]:
    """
    Check if a repository has automated build processes.

    Args:
        api_url: The API Gateway URL
        repository: Repository in format 'owner/repo'

    Returns:
        Analysis results
    """
    endpoint = f"{api_url}/build-check"

    payload = {"repository": repository}

    print(f"Analyzing repository: {repository}...")
    print(f"Endpoint: {endpoint}\n")

    response = requests.post(
        endpoint, json=payload, headers={"Content-Type": "application/json"}
    )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API Error: {response.status_code} - {response.text}")


def print_results(results: Dict[str, Any]) -> None:
    """Pretty print the analysis results."""

    print("=" * 80)
    print(f"Repository: {results['repository']}")
    print("=" * 80)
    print()

    # Status
    status = (
        "✅ HAS BUILD PROCESS" if results["hasBuildProcess"] else "❌ NO BUILD PROCESS"
    )
    print(f"Status: {status}")
    print(f"Confidence: {results['confidenceLevel'].upper()}")
    print()

    # Build systems found
    if results["buildSystemsFound"]:
        print("Build Systems Detected:")
        for system in results["buildSystemsFound"]:
            print(f"  • {system}")
        print()

    # Evidence
    if results["evidence"]:
        print("Evidence:")
        for item in results["evidence"]:
            print(f"  • {item}")
        print()

    # Summary
    print("Summary:")
    print(f"  {results['summary']}")
    print()

    # Recommendations
    if results["recommendations"]:
        print("Recommendations:")
        for i, rec in enumerate(results["recommendations"], 1):
            print(f"  {i}. {rec}")
        print()

    print("=" * 80)


def main():
    """Main execution."""

    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python test_build_checker.py <repository>")
        print("Example: python test_build_checker.py awslabs/aws-cdk")
        sys.exit(1)

    repository = sys.argv[1]

    # Get API URL (you'll need to update this after deployment)
    api_url = input(
        "Enter your API Gateway URL (e.g., https://abc123.execute-api.us-east-1.amazonaws.com): "
    ).strip()

    if not api_url:
        print("Error: API URL is required")
        sys.exit(1)

    try:
        # Check build process
        results = check_build_process(api_url, repository)

        # Print results
        print_results(results)

        # Export to JSON file
        output_file = f"{repository.replace('/', '_')}_build_check.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"\nResults saved to: {output_file}")

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

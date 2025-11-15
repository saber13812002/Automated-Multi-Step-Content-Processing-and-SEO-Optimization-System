#!/usr/bin/env python3
"""Simple Python client for testing the Chroma Search API."""

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

# Load .env file
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_ENV_PATH = os.path.join(_PROJECT_ROOT, ".env")
if os.path.exists(_ENV_PATH):
    load_dotenv(dotenv_path=_ENV_PATH, override=False)


def check_health(base_url: str) -> Dict[str, Any]:
    """Check service health status."""
    url = f"{base_url}/health"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        print(f"❌ Health check failed: {exc}", file=sys.stderr)
        if hasattr(exc, "response") and exc.response is not None:
            print(f"Response: {exc.response.text}", file=sys.stderr)
        sys.exit(1)


def search(
    base_url: str,
    query: str,
    top_k: int = 10,
    pretty: bool = True,
) -> Dict[str, Any]:
    """Perform semantic search."""
    url = f"{base_url}/search"
    payload = {"query": query, "top_k": top_k}

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        print(f"❌ Search failed: {exc}", file=sys.stderr)
        if hasattr(exc, "response") and exc.response is not None:
            print(f"Response: {exc.response.text}", file=sys.stderr)
        sys.exit(1)


def print_health(data: Dict[str, Any]) -> None:
    """Print health check results in a readable format."""
    print("=" * 80)
    print("Health Check Results")
    print("=" * 80)
    print(f"Overall Status: {data.get('status', 'unknown').upper()}")
    print(f"Timestamp: {data.get('timestamp', 'N/A')}")
    print()

    components = ["chroma", "collection", "redis"]
    for comp in components:
        info = data.get(comp, {})
        status = info.get("status", "unknown")
        status_icon = "✅" if status == "ok" else "❌"
        print(f"{status_icon} {comp.capitalize()}: {status.upper()}")
        if info.get("latency_ms"):
            print(f"   Latency: {info['latency_ms']:.2f} ms")
        if info.get("detail"):
            print(f"   Detail: {info['detail']}")
        extras = info.get("extras", {})
        if extras:
            for key, value in extras.items():
                print(f"   {key}: {value}")
        print()


def print_search_results(data: Dict[str, Any], show_full: bool = False) -> None:
    """Print search results in a readable format."""
    print("=" * 80)
    print("Search Results")
    print("=" * 80)
    print(f"Query: {data.get('query', 'N/A')}")
    print(f"Collection: {data.get('collection', 'N/A')}")
    print(f"Provider: {data.get('provider', 'N/A')}")
    print(f"Model: {data.get('model', 'N/A')}")
    print(f"Returned: {data.get('returned', 0)} / {data.get('top_k', 0)} requested")
    print(f"Time: {data.get('took_ms', 0):.2f} ms")
    print(f"Timestamp: {data.get('timestamp', 'N/A')}")
    print()

    results = data.get("results", [])
    if not results:
        print("No results found.")
        return

    for idx, result in enumerate(results, 1):
        print("-" * 80)
        print(f"[{idx}] ID: {result.get('id', 'N/A')}")
        if result.get("score") is not None:
            print(f"    Score: {result.get('score', 0):.4f} (distance: {result.get('distance', 0):.4f})")
        if result.get("document"):
            doc = result["document"]
            preview = doc[:200].replace("\n", " ") if len(doc) > 200 else doc
            print(f"    Document: {preview}")
            if len(doc) > 200:
                print(f"    ... ({len(doc) - 200} more characters)")

        metadata = result.get("metadata", {})
        if metadata:
            print(f"    Metadata:")
            for key, value in list(metadata.items())[:5]:  # Show first 5 fields
                print(f"      {key}: {value}")
            if len(metadata) > 5:
                print(f"      ... ({len(metadata) - 5} more fields)")

        if show_full and result.get("document"):
            print(f"    Full Document:")
            print(f"    {result['document']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Python client for Chroma Search API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Health check
  python web_client.py --health

  # Simple search
  python web_client.py --search "آموزش عقاید چیست؟"

  # Search with custom top_k
  python web_client.py --search "اعتقاد به آفریننده" --top-k 5

  # Full output
  python web_client.py --search "دین چیست" --full
        """,
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("API_BASE_URL", "http://localhost:8080"),
        help="API base URL (default: http://localhost:8080)",
    )
    parser.add_argument("--health", action="store_true", help="Check service health")
    parser.add_argument("--search", type=str, help="Search query text")
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of results to return (default: 10)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Show full document text in results",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted text",
    )

    args = parser.parse_args()

    if not args.health and not args.search:
        parser.print_help()
        sys.exit(1)

    if args.health:
        data = check_health(args.base_url)
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print_health(data)
        return

    if args.search:
        data = search(args.base_url, args.search, args.top_k)
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print_search_results(data, args.full)
        return


if __name__ == "__main__":
    main()


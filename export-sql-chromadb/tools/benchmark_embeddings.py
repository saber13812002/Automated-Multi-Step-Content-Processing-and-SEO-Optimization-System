"""Simple benchmarking utility for Chroma collections based on sample queries."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import chromadb


def create_client(args: argparse.Namespace):
    if args.persist_directory:
        return chromadb.PersistentClient(path=args.persist_directory)
    return chromadb.HttpClient(
        host=args.host,
        port=args.port,
        ssl=args.ssl,
        headers={"Authorization": args.api_key} if args.api_key else None,
    )


def load_queries(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Queries file must contain a JSON list.")
    for item in payload:
        if "query" not in item:
            raise ValueError("Each query entry must include a 'query' field.")
    return payload


def evaluate_query(collection, spec: Dict[str, Any]) -> Dict[str, Any]:
    n_results = int(spec.get("n_results", 5))
    start = time.perf_counter()
    response = collection.query(
        query_texts=[spec["query"]],
        n_results=n_results,
        where=spec.get("where"),
        include=["documents", "metadatas", "distances", "embeddings"],
    )
    latency_ms = (time.perf_counter() - start) * 1000.0

    ids = response.get("ids", [[]])[0]
    documents = response.get("documents", [[]])[0]
    metadatas = response.get("metadatas", [[]])[0]

    expected_ids = set(spec.get("expected_ids", []))
    expected_keywords = spec.get("expected_keywords", [])
    hit_id = bool(expected_ids.intersection(ids))
    hit_keyword = False
    for keyword in expected_keywords:
        if any(keyword in (doc or "") for doc in documents):
            hit_keyword = True
            break

    return {
        "query": spec["query"],
        "latency_ms": latency_ms,
        "ids": ids,
        "hit_expected_id": hit_id,
        "hit_expected_keyword": hit_keyword,
        "metadatas": metadatas,
    }


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    latencies = [item["latency_ms"] for item in results]
    id_hits = [1 if item["hit_expected_id"] else 0 for item in results]
    keyword_hits = [1 if item["hit_expected_keyword"] else 0 for item in results]

    return {
        "queries": len(results),
        "avg_latency_ms": statistics.fmean(latencies) if latencies else 0.0,
        "p95_latency_ms": statistics.quantiles(latencies, n=20)[-1] if len(latencies) >= 20 else max(latencies, default=0.0),
        "id_hit_rate": sum(id_hits) / len(id_hits) if id_hits else 0.0,
        "keyword_hit_rate": sum(keyword_hits) / len(keyword_hits) if keyword_hits else 0.0,
    }


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark queries against a Chroma collection.")
    parser.add_argument("--host", default="localhost", help="Chroma host")
    parser.add_argument("--port", type=int, default=8000, help="Chroma port")
    parser.add_argument("--ssl", action="store_true", help="Use HTTPS when connecting to Chroma.")
    parser.add_argument("--api-key", default="", help="API key header, if required.")
    parser.add_argument("--persist-directory", default="", help="Use PersistentClient if provided.")
    parser.add_argument("--collection", required=True, help="Collection name to benchmark.")
    parser.add_argument("--queries", type=Path, required=True, help="JSON file with queries and expectations.")
    parser.add_argument("--json-out", type=Path, help="Optional path to store raw results as JSON.")
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    client = create_client(args)
    try:
        collection = client.get_collection(args.collection)
    except Exception as exc:  # pragma: no cover - networking
        raise SystemExit(f"❌ Failed to load collection '{args.collection}': {exc}") from exc

    queries = load_queries(args.queries)
    results = []

    for spec in queries:
        result = evaluate_query(collection, spec)
        results.append(result)
        print(
            f"🔍 Query: {spec['query']} | latency={result['latency_ms']:.1f}ms | "
            f"id_hit={result['hit_expected_id']} | keyword_hit={result['hit_expected_keyword']}"
        )

    summary = summarize(results)
    print("\n📊 Summary:")
    print(
        f"   • Queries: {summary['queries']} | Avg latency: {summary['avg_latency_ms']:.1f} ms | "
        f"P95 latency: {summary['p95_latency_ms']:.1f} ms"
    )
    print(
        f"   • ID hit rate: {summary['id_hit_rate']*100:.1f}% | Keyword hit rate: {summary['keyword_hit_rate']*100:.1f}%"
    )

    if args.json_out:
        payload = {"summary": summary, "results": results}
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"   • Raw results saved to {args.json_out}")


if __name__ == "__main__":
    main()


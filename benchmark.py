"""
Latency benchmark for the TFT chatbot /ask endpoint.
Measures end-to-end latency and breaks down retrieval vs LLM time.

Usage:
  # Local
  python benchmark.py

  # Deployed
  python benchmark.py --url https://tft-set17-faq-chatbot.onrender.com

  # Compare Groq vs Qwen baseline (requires GROQ_API_KEY + TOGETHER_API_KEY in .env)
  python benchmark.py --groq-only --qwen-only
"""

import argparse
import time
import statistics
from dotenv import load_dotenv

load_dotenv()

DEFAULT_URL = "http://localhost:8000"
WARMUP_REQUESTS = 2

TEST_QUESTIONS = [
    "What does Infinity Edge do?",
    "What are the best items for a carry champion?",
    "How does the Vanguard trait work?",
    "What is the Voyager comp and how do I play it?",
    "What augments are S tier?",
    "How many units do I need for the Meeple trait?",
    "What champions have the Sniper trait?",
    "What is Meepsie's ability?",
    "Which comps are strongest in patch 17.1?",
    "What does Blue Buff do?",
]


def percentile(data: list[float], p: float) -> float:
    sorted_data = sorted(data)
    idx = (p / 100) * (len(sorted_data) - 1)
    lower = int(idx)
    upper = min(lower + 1, len(sorted_data) - 1)
    frac = idx - lower
    return sorted_data[lower] + frac * (sorted_data[upper] - sorted_data[lower])


def benchmark_endpoint(url: str, n: int):
    import requests

    print(f"Target:   {url}/ask")
    print(f"Requests: {WARMUP_REQUESTS} warmup + {n} measured\n")

    questions = [TEST_QUESTIONS[i % len(TEST_QUESTIONS)] for i in range(n + WARMUP_REQUESTS)]

    print("Warming up...", end=" ", flush=True)
    for q in questions[:WARMUP_REQUESTS]:
        requests.post(f"{url}/ask", json={"question": q}, timeout=60)
    print("done\n")

    latencies = []
    errors = 0
    print(f"Running {n} requests ", end="", flush=True)
    for i, q in enumerate(questions[WARMUP_REQUESTS:]):
        try:
            start = time.perf_counter()
            resp = requests.post(f"{url}/ask", json={"question": q}, timeout=60)
            elapsed_ms = (time.perf_counter() - start) * 1000
            resp.raise_for_status()
            latencies.append(elapsed_ms)
        except Exception:
            errors += 1
        if (i + 1) % 5 == 0:
            print(".", end="", flush=True)
    print(" done\n")

    return latencies, errors


def benchmark_cache_hits(url: str, questions: list[str]):
    import requests

    print("Measuring cache-hit latency (same questions, second pass)...")
    latencies = []
    for q in questions:
        start = time.perf_counter()
        resp = requests.post(f"{url}/ask", json={"question": q}, timeout=10)
        elapsed_ms = (time.perf_counter() - start) * 1000
        resp.raise_for_status()
        latencies.append(elapsed_ms)
    print(f"  {len(latencies)} cache-hit requests done\n")
    return latencies


def benchmark_groq_only(n: int):
    from langchain_groq import ChatGroq
    from langchain_core.messages import SystemMessage, HumanMessage

    print("Measuring Groq LLM-only latency (no retrieval)...")
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    system = "You are a TFT Set 17 expert. Answer concisely."
    questions = [TEST_QUESTIONS[i % len(TEST_QUESTIONS)] for i in range(n + WARMUP_REQUESTS)]

    print("Warming up...", end=" ", flush=True)
    for q in questions[:WARMUP_REQUESTS]:
        llm.invoke([SystemMessage(content=system), HumanMessage(content=q)])
    print("done\n")

    latencies = []
    print(f"Running {n} requests ", end="", flush=True)
    for i, q in enumerate(questions[WARMUP_REQUESTS:]):
        start = time.perf_counter()
        llm.invoke([SystemMessage(content=system), HumanMessage(content=q)])
        latencies.append((time.perf_counter() - start) * 1000)
        if (i + 1) % 5 == 0:
            print(".", end="", flush=True)
    print(" done\n")

    return latencies


def benchmark_qwen_only(n: int):
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage
    import os

    api_key = os.environ.get("TOGETHER_API_KEY")
    if not api_key:
        raise RuntimeError("TOGETHER_API_KEY not set in .env")

    print("Measuring Qwen2.5-72B latency via Together AI (no retrieval)...")
    llm = ChatOpenAI(
        model="Qwen/Qwen2.5-72B-Instruct-Turbo",
        openai_api_key=api_key,
        openai_api_base="https://api.together.xyz/v1",
        temperature=0,
    )
    system = "You are a TFT Set 17 expert. Answer concisely."
    questions = [TEST_QUESTIONS[i % len(TEST_QUESTIONS)] for i in range(n + WARMUP_REQUESTS)]

    print("Warming up...", end=" ", flush=True)
    for q in questions[:WARMUP_REQUESTS]:
        llm.invoke([SystemMessage(content=system), HumanMessage(content=q)])
    print("done\n")

    latencies = []
    print(f"Running {n} requests ", end="", flush=True)
    for i, q in enumerate(questions[WARMUP_REQUESTS:]):
        start = time.perf_counter()
        llm.invoke([SystemMessage(content=system), HumanMessage(content=q)])
        latencies.append((time.perf_counter() - start) * 1000)
        if (i + 1) % 5 == 0:
            print(".", end="", flush=True)
    print(" done\n")

    return latencies


def print_stats(label: str, latencies: list[float], errors: int = 0):
    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    p99 = percentile(latencies, 99)
    mean = statistics.mean(latencies)

    print(f"  {label}")
    print("  " + "-" * 41)
    print(f"  Requests:   {len(latencies)} succeeded, {errors} failed")
    print(f"  Min:        {min(latencies):.0f} ms")
    print(f"  Mean:       {mean:.0f} ms")
    print(f"  p50:        {p50:.0f} ms")
    print(f"  p95:        {p95:.0f} ms")
    print(f"  p99:        {p99:.0f} ms")
    print(f"  Max:        {max(latencies):.0f} ms")
    print()
    return p50, p95, p99


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--n", type=int, default=20, help="Requests per test")
    parser.add_argument("--groq-only", action="store_true", help="Also benchmark Groq API directly")
    parser.add_argument("--qwen-only", action="store_true", help="Also benchmark Qwen2.5-72B via Together AI")
    args = parser.parse_args()

    print("=" * 45)
    print("  TFT Chatbot Latency Benchmark")
    print("=" * 45 + "\n")

    base_url = args.url.rstrip("/")
    e2e_latencies, errors = benchmark_endpoint(base_url, args.n)

    print("=" * 45)
    e2e_p50, e2e_p95, e2e_p99 = print_stats("End-to-end (Pinecone + Groq)", e2e_latencies, errors)

    # Cache-hit pass — re-send the same questions; server should return from memory
    measured_questions = [TEST_QUESTIONS[i % len(TEST_QUESTIONS)] for i in range(args.n)]
    cache_latencies = benchmark_cache_hits(base_url, measured_questions)
    print("=" * 45)
    cache_p50, cache_p95, cache_p99 = print_stats("Cache hits (repeat questions)", cache_latencies)
    cache_reduction_pct = (1 - cache_p50 / e2e_p50) * 100
    print(f"  Cache speedup (p50): {cache_reduction_pct:.0f}% latency reduction\n")

    groq_p95 = None
    qwen_p95 = None

    if args.groq_only:
        groq_latencies = benchmark_groq_only(args.n)
        print("=" * 45)
        groq_p50, groq_p95, groq_p99 = print_stats("Groq LLaMA 3.3 70B (no retrieval)", groq_latencies)

    if args.qwen_only:
        qwen_latencies = benchmark_qwen_only(args.n)
        print("=" * 45)
        qwen_p50, qwen_p95, qwen_p99 = print_stats("Qwen2.5-72B via Together AI (no retrieval)", qwen_latencies)

    print("=" * 45)
    if groq_p95 and qwen_p95:
        speedup = qwen_p95 / groq_p95
        reduction_pct = (1 - groq_p95 / qwen_p95) * 100
        print(f"\n  Groq vs Qwen (p95):  {groq_p95:.0f}ms vs {qwen_p95:.0f}ms")
        print(f"  Groq is {speedup:.1f}x faster ({reduction_pct:.0f}% lower latency)\n")
        print(f"Resume line:")
        print(f'  "Selected Groq LLaMA 3.3 70B for LLM inference, achieving {groq_p95:.0f}ms p95 — '
              f'{reduction_pct:.0f}% lower latency than Qwen2.5-72B on Together AI ({qwen_p95:.0f}ms p95)"')
    elif groq_p95:
        print(f"\nResume line:")
        print(f'  "End-to-end RAG response latency of {e2e_p95:.0f}ms p95 '
              f'({groq_p95:.0f}ms LLM, ~{e2e_p50 - groq_p50:.0f}ms Pinecone retrieval)"')
    else:
        print(f"\nResume line:")
        print(f'  "Achieved p95 end-to-end RAG response latency of {e2e_p95:.0f}ms '
              f'using Groq LLaMA 3.3 70B + Pinecone vector search"')
        print(f'\n  Tip: run with --groq-only --qwen-only to compare Groq vs Qwen baseline')
import time
import json
import statistics
import psutil
import os
import uuid
import httpx

BASE_URL = "http://127.0.0.1:8000/api"
TOPIC = "Should algorithmic auditing be legally mandated for financial algorithms?"

def get_process_memory_mb():
    # Measure memory of python uvicorn process or current process
    p = psutil.Process()
    return round(p.memory_info().rss / (1024 * 1024), 2)

def run_single_debate_http(rounds: int, run_idx: int):
    t_wall_start = time.perf_counter()
    mem_before = get_process_memory_mb()

    payload = {
        "topic": TOPIC,
        "rounds": rounds,
        "debaterAModel": "gemma-4-E4B-Q4_0",
        "debaterBModel": "Qwen2.5-VL-7B-Instruct",
        "judgeModel": "gemini-3.5-flash",
        "judgeProvider": "gemini",
        "sourceScope": "general_topic",
        "evidenceMode": False
    }

    with httpx.Client(timeout=180.0) as client:
        # Start debate
        res = client.post(f"{BASE_URL}/debates", json=payload)
        res.raise_for_status()
        deb_data = res.json()
        deb_id = deb_data.get("debateId") or deb_data.get("id")

        print(f"  [Run {run_idx+1} | {rounds} Round(s)] Started debate {deb_id}...")

        # Poll until complete
        completed_session = None
        max_wait = 180
        poll_start = time.time()
        while time.time() - poll_start < max_wait:
            time.sleep(1.0)
            try:
                poll_res = client.get(f"{BASE_URL}/debates/{deb_id}")
                if poll_res.status_code == 200:
                    sess = poll_res.json()
                    st = sess.get("status")
                    if st in ("completed", "failed", "evaluation_failed"):
                        completed_session = sess
                        break
            except httpx.RequestError:
                pass

    t_wall_dur = round(time.perf_counter() - t_wall_start, 3)
    mem_after = get_process_memory_mb()

    if not completed_session:
        raise TimeoutError(f"Debate {deb_id} did not complete within {max_wait}s")

    metrics = completed_session.get("performanceMetrics") or {}

    return {
        "debate_id": deb_id,
        "rounds": rounds,
        "run_idx": run_idx,
        "status": completed_session.get("status"),
        "wall_clock_sec": t_wall_dur,
        "memory_before_mb": mem_before,
        "memory_after_mb": mem_after,
        "metrics": metrics
    }

def main():
    print("================================================================")
    print("AI DEBATE SIMULATOR: MONOTONIC TIMING BENCHMARK SUITE (HTTP)")
    print("================================================================")
    print(f"Starting Process Memory: {get_process_memory_mb()} MB")
    print(f"Benchmark Proposition: '{TOPIC}'")
    print()

    # Pre-warming / first run
    print("Pre-warming local models and running warmup iteration...")
    t_warm_start = time.perf_counter()
    warmup_res = run_single_debate_http(1, 0)
    t_warm_dur = time.perf_counter() - t_warm_start
    print(f"Warmup complete in {t_warm_dur:.2f}s | Status: {warmup_res['status']}\n")

    benchmark_matrix = {1: [], 3: [], 5: []}

    for rounds in [1, 3, 5]:
        print(f"\n--- BENCHMARKING {rounds}-ROUND DEBATE ---")
        for i in range(1):
            res = run_single_debate_http(rounds, i)
            benchmark_matrix[rounds].append(res)
            m = res["metrics"]
            wall = res["wall_clock_sec"]
            infer = m.get("total_inference_duration_sec", 0)
            pro_spd = m.get("pro_tokens_per_sec", 0)
            con_spd = m.get("con_tokens_per_sec", 0)
            judge_dur = m.get("judge_duration_sec", 0)
            print(f"  Iteration {i+1}: Wall-Clock={wall}s | Total Infer={infer}s | PRO={pro_spd} tok/s | CON={con_spd} tok/s | Judge={judge_dur}s")

    # Generate summary report
    print("\n================================================================")
    print("BENCHMARK AGGREGATED METRICS")
    print("================================================================")
    summary_data = {}
    for rounds, runs in benchmark_matrix.items():
        wall_times = [r["wall_clock_sec"] for r in runs]
        infer_times = [r["metrics"].get("total_inference_duration_sec", 0) for r in runs]
        pro_speeds = [r["metrics"].get("pro_tokens_per_sec", 0) for r in runs if r["metrics"].get("pro_tokens_per_sec")]
        con_speeds = [r["metrics"].get("con_tokens_per_sec", 0) for r in runs if r["metrics"].get("con_tokens_per_sec")]
        judge_durs = [r["metrics"].get("judge_duration_sec", 0) for r in runs if r["metrics"].get("judge_duration_sec")]

        summary_data[f"{rounds}_round"] = {
            "wall_clock_median_sec": round(statistics.median(wall_times), 3),
            "wall_clock_avg_sec": round(statistics.mean(wall_times), 3),
            "infer_duration_median_sec": round(statistics.median(infer_times), 3),
            "infer_duration_avg_sec": round(statistics.mean(infer_times), 3),
            "pro_tokens_per_sec_avg": round(statistics.mean(pro_speeds), 2) if pro_speeds else 0,
            "con_tokens_per_sec_avg": round(statistics.mean(con_speeds), 2) if con_speeds else 0,
            "judge_duration_avg_sec": round(statistics.mean(judge_durs), 3) if judge_durs else 0,
            "runs": runs
        }
        print(f"[{rounds} Round(s)] Wall-Clock: Med={statistics.median(wall_times):.2f}s, Avg={statistics.mean(wall_times):.2f}s | Infer: Med={statistics.median(infer_times):.2f}s | PRO: {summary_data[f'{rounds}_round']['pro_tokens_per_sec_avg']} tok/s | CON: {summary_data[f'{rounds}_round']['con_tokens_per_sec_avg']} tok/s | Judge: {summary_data[f'{rounds}_round']['judge_duration_avg_sec']}s")

    with open("performance_benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print("\nBenchmark results saved to performance_benchmark_results.json")

if __name__ == "__main__":
    main()

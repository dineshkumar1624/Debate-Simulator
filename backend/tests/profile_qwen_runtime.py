"""
Controlled Profiling & Runtime Optimization Investigation for Qwen CON Agent.
Evaluates:
- Model Loading & Unloading overhead
- Tokenization & Prefill latency (TTFT)
- Autoregressive decode throughput under varying thread counts (8, 12, 16)
- Impact of CPU flush denormal settings
- Peak RAM and memory reclamation
"""

import os
import sys
import time
import json
import psutil
import torch
from transformers import AutoTokenizer, Qwen2_5_VLForConditionalGeneration

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.llm.model_manager import local_model_manager
from app.agents.con_agent import con_agent

def get_current_rss_mb():
    try:
        proc = psutil.Process(os.getpid())
        return proc.memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0

def profile_qwen():
    print("=" * 60)
    print("QWEN2.5-VL-7B-INSTRUCT CPU RUNTIME PROFILING")
    print("=" * 60)
    
    initial_rss = get_current_rss_mb()
    print(f"Initial RSS: {initial_rss:.2f} MB")
    
    # Standard proposition
    topic = "Should universities allow students to use generative AI for academic assignments?"
    pro_arg = (
        "The proposition that universities should allow students to use generative AI for academic assignments "
        "is fundamentally sound, provided the integration is managed through pedagogical evolution rather than outright prohibition."
    )
    
    # 1. Prompt Tokenization & Assembly
    t0_tok = time.perf_counter()
    clean_pro = con_agent._clean_substantive_text(pro_arg)
    user_prompt_lines = [
        f"Topic: {topic}",
        "Round: 1 of 1 (CON)",
        "",
        "Grounding Evidence:",
        "No external grounding documents retrieved. Rely on core empirical principles.",
        "",
        "Opposing PRO Argument to Rebut:",
        clean_pro
    ]
    user_prompt = "\n".join(user_prompt_lines)
    system_prompt = (
        "You are the CON debater in a formal debate.\n"
        "Challenge the affirmative position with analytical rigor.\n"
        "Structure (40-60 words):\n"
        "- Target: The opposing claim challenged\n"
        "- Rebuttal: 1-2 precise counterpoints\n"
        "- Conclusion: Definitive concluding takeaway\n"
        "Finish completely with terminal punctuation."
    )
    
    tokenizer = local_model_manager.load_tokenizer("CON")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    chat_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(chat_prompt, return_tensors="pt")
    input_ids = inputs.input_ids
    tok_duration = (time.perf_counter() - t0_tok) * 1000
    prompt_tokens = input_ids.shape[1]
    
    print(f"Prompt Tokens: {prompt_tokens}")
    print(f"Tokenization Duration: {tok_duration:.2f} ms")
    
    # 2. Model Loading
    print("\n--- MODEL LOADING ---")
    t0_load = time.perf_counter()
    model, _ = local_model_manager.load_model("CON")
    load_duration = time.perf_counter() - t0_load
    post_load_rss = get_current_rss_mb()
    print(f"Model Load Time: {load_duration:.2f} s")
    print(f"Post-Load RSS: {post_load_rss:.2f} MB (Delta: {post_load_rss - initial_rss:.2f} MB)")
    
    # Resolve authoritative EOS
    gen_cfg_eos = getattr(getattr(model, "generation_config", None), "eos_token_id", None)
    effective_eos = gen_cfg_eos if gen_cfg_eos is not None else tokenizer.eos_token_id
    pad_token_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
    
    experiments = [
        {"name": "12_threads_baseline_warmup", "threads": 12, "denormal": False, "tokens": 4},
        {"name": "12_threads_steady_state", "threads": 12, "denormal": False, "tokens": 4},
        {"name": "16_threads_all_logical", "threads": 16, "denormal": False, "tokens": 4},
        {"name": "8_threads_p_cores", "threads": 8, "denormal": False, "tokens": 4},
        {"name": "12_threads_flush_denormal", "threads": 12, "denormal": True, "tokens": 4},
    ]
    
    results = {
        "prompt_tokens": prompt_tokens,
        "tokenization_ms": round(tok_duration, 2),
        "load_time_sec": round(load_duration, 2),
        "post_load_rss_mb": round(post_load_rss, 2),
        "experiments": []
    }
    
    for exp in experiments:
        name = exp["name"]
        num_threads = exp["threads"]
        use_denormal = exp["denormal"]
        num_tokens = exp["tokens"]
        
        torch.set_num_threads(num_threads)
        if use_denormal:
            torch.set_flush_denormal(True)
        else:
            torch.set_flush_denormal(False)
            
        print(f"\nRunning experiment: {name} (threads={num_threads}, denormal={use_denormal}, tokens={num_tokens})...")
        
        t0_gen = time.perf_counter()
        with torch.inference_mode():
            out = model.generate(
                **inputs,
                max_new_tokens=num_tokens,
                temperature=0.0,
                do_sample=False,
                pad_token_id=pad_token_id,
                eos_token_id=effective_eos,
                use_cache=True
            )
        gen_duration = time.perf_counter() - t0_gen
        
        gen_ids = out[0][input_ids.shape[1]:]
        actual_tokens = len(gen_ids)
        tok_sec = actual_tokens / gen_duration if gen_duration > 0 else 0.0
        sec_tok = gen_duration / actual_tokens if actual_tokens > 0 else 0.0
        cur_rss = get_current_rss_mb()
        
        decoded_text = tokenizer.decode(gen_ids, skip_special_tokens=True)
        print(f"  Duration: {gen_duration:.2f} s | Tokens: {actual_tokens} | Rate: {tok_sec:.4f} tok/s ({sec_tok:.2f} s/tok) | Peak RSS: {cur_rss:.2f} MB")
        print(f"  Decoded: {repr(decoded_text)}")
        
        results["experiments"].append({
            "name": name,
            "threads": num_threads,
            "flush_denormal": use_denormal,
            "tokens_generated": actual_tokens,
            "duration_sec": round(gen_duration, 2),
            "tokens_per_sec": round(tok_sec, 4),
            "sec_per_token": round(sec_tok, 2),
            "peak_rss_mb": round(cur_rss, 2),
            "output_preview": decoded_text
        })
        
    # Unload and measure release
    print("\n--- MODEL UNLOADING ---")
    t0_unload = time.perf_counter()
    local_model_manager.unload_all()
    unload_duration = time.perf_counter() - t0_unload
    post_unload_rss = get_current_rss_mb()
    print(f"Unload Duration: {unload_duration:.2f} s")
    print(f"Post-Unload RSS: {post_unload_rss:.2f} MB")
    
    results["unload_time_sec"] = round(unload_duration, 2)
    results["post_unload_rss_mb"] = round(post_unload_rss, 2)
    
    out_file = os.path.join(backend_dir, "..", "test_reports", "optimization_d_profile_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[DONE] Profiling results written to {out_file}")

if __name__ == "__main__":
    profile_qwen()


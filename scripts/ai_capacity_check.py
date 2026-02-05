import os
import sys
import json
import subprocess
import platform

# --- Configuration: Adjust these if your setup changes ---
# How much RAM (in GB) to leave for the OS + Uptime Kuma + Crafty
SYSTEM_OVERHEAD_GB = 3.0 
# Maximum theoretical allocation for your 2 MC worlds (12GB x 2)
MC_MAX_ALLOC_GB = 24.0
# Realistic current active usage for 2 MC worlds (2GB x 2)
MC_REALISTIC_USAGE_GB = 4.0

def get_cpu_info():
    """Detects CPU cores and AVX support (Critical for AI on CPU)."""
    cpu_info = {"cores": 0, "threads": 0, "avx2": False, "model": "Unknown"}
    
    try:
        # Linux specific checks
        with open('/proc/cpuinfo', 'r') as f:
            lines = f.readlines()
            for line in lines:
                if "model name" in line and cpu_info["model"] == "Unknown":
                    cpu_info["model"] = line.split(":")[1].strip()
                if "flags" in line:
                    if "avx2" in line:
                        cpu_info["avx2"] = True
        
        cpu_info["cores"] = int(subprocess.check_output(['nproc', '--all']).decode().strip()) / 2 # Approx for hyperthreading
        cpu_info["threads"] = int(subprocess.check_output(['nproc', '--all']).decode().strip())
    except Exception as e:
        cpu_info["error"] = str(e)
        
    return cpu_info

def get_memory_info():
    """Reads actual memory availability."""
    mem = {"total": 0, "available": 0, "free": 0}
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in lines:
                parts = line.split()
                key = parts[0].strip(':')
                val = int(parts[1]) // 1024 # Convert kB to MB
                if key == "MemTotal": mem["total"] = val / 1024
                if key == "MemAvailable": mem["available"] = val / 1024
                if key == "MemFree": mem["free"] = val / 1024
    except:
        # Fallback using free command if proc fails
        try:
            out = subprocess.check_output(['free', '-g']).decode().splitlines()[1].split()
            mem["total"] = int(out[1])
            mem["available"] = int(out[6])
        except:
            pass
    return mem

def define_models():
    """
    Database of models with their estimated RAM usage (Quantized GGUF/ONNX).
    Size includes ~1GB buffer for context window (KV Cache).
    """
    return [
        # TEXT (LLMs)
        {"id": "qwen2.5-0.5b", "type": "LLM", "name": "Qwen 2.5 (0.5B)", "ram_gb": 1.0, "desc": "Tiny, fast text classification/simple logic."},
        {"id": "llama3.2-3b", "type": "LLM", "name": "Llama 3.2 (3B)", "ram_gb": 3.5, "desc": "Best balance of speed/smarts for 4-core CPUs."},
        {"id": "qwen2.5-7b", "type": "LLM", "name": "Qwen 2.5 (7B)", "ram_gb": 6.5, "desc": "Coding capable. Comparable to GPT-3.5."},
        {"id": "mistral-nemo-12b", "type": "LLM", "name": "Mistral NeMo (12B)", "ram_gb": 10.0, "desc": "Smart, but slow on 4 cores."},
        {"id": "qwen2.5-32b", "type": "LLM", "name": "Qwen 2.5 (32B)", "ram_gb": 22.0, "desc": "Expert coder. TOO HEAVY for concurrent MC usage."},

        # VISION (Multimodal)
        {"id": "moondream2", "type": "Vision", "name": "Moondream 2", "ram_gb": 2.5, "desc": "Very fast image description for CPUs."},
        {"id": "llava-v1.6-7b", "type": "Vision", "name": "LLaVA v1.6 (7B)", "ram_gb": 6.0, "desc": "Standard open-source vision model."},

        # GENERATIVE (Image/Audio)
        {"id": "musicgen-small", "type": "Audio", "name": "MusicGen Small", "ram_gb": 4.0, "desc": "Generates short music loops. CPU Heavy."},
        {"id": "fastsd-cpu", "type": "Image", "name": "FastSD (OpenVINO)", "ram_gb": 5.0, "desc": "Optimized Stable Diffusion for CPU. Expect 1-2 mins/image."},
        {"id": "flux-schnell", "type": "Image", "name": "Flux Schnell (Quant)", "ram_gb": 14.0, "desc": "High quality image gen. Will likely OOM kill Minecraft."},
    ]

def analyze_capacity(sys_mem, cpu_data):
    # Scenario A: WORST CASE (Minecraft uses full allocation)
    # Total - System - MC_Max
    safe_ram = sys_mem["total"] - SYSTEM_OVERHEAD_GB - MC_MAX_ALLOC_GB
    
    # Scenario B: BURST/CURRENT (Minecraft uses typical real usage)
    # Total - System - MC_Real
    burst_ram = sys_mem["total"] - SYSTEM_OVERHEAD_GB - MC_REALISTIC_USAGE_GB
    
    report = {
        "system_summary": {
            "cpu_model": cpu_data["model"],
            "avx2_support": cpu_data["avx2"],
            "total_ram_gb": round(sys_mem["total"], 2),
            "safe_headroom_gb": round(max(0, safe_ram), 2),
            "burst_headroom_gb": round(max(0, burst_ram), 2)
        },
        "recommendations": []
    }

    models = define_models()
    
    for m in models:
        status = "UNSAFE"
        perf_note = "OK"
        
        # CPU Bottleneck Check
        if cpu_data["threads"] < 8 and m["type"] in ["Image", "Audio"] and m["ram_gb"] > 8:
            perf_note = "EXTREME LAG (CPU Bound)"
        elif not cpu_data["avx2"] and m["type"] != "LLM":
             perf_note = "SLOW (No AVX2)"
            
        # RAM Fit Check
        if m["ram_gb"] <= safe_ram:
            status = "PERMANENT" # Can run 24/7 safely
        elif m["ram_gb"] <= burst_ram:
            status = "CONDITIONAL" # Can run if MC isn't full
        else:
            status = "INCOMPATIBLE" # Will crash server
            
        report["recommendations"].append({
            "model": m["name"],
            "type": m["type"],
            "status": status,
            "estimated_ram": f"{m['ram_gb']} GB",
            "performance_prediction": perf_note,
            "description": m["desc"]
        })
        
    return report

def print_table(data):
    print(f"\n{'='*60}")
    print(f" SERVER AI CAPACITY REPORT ({data['system_summary']['total_ram_gb']}GB Total)")
    print(f"{'='*60}")
    print(f"CPU: {data['system_summary']['cpu_model']}")
    print(f"Safe RAM Available (Worst Case): {data['system_summary']['safe_headroom_gb']} GB")
    print(f"Burst RAM Available (Best Case): {data['system_summary']['burst_headroom_gb']} GB")
    print("-" * 60)
    print(f"{'MODEL':<20} | {'TYPE':<7} | {'STATUS':<12} | {'RAM COST':<10}")
    print("-" * 60)
    
    for r in data["recommendations"]:
        color = ""
        if r["status"] == "PERMANENT": color = "\033[92m" # Green
        elif r["status"] == "CONDITIONAL": color = "\033[93m" # Yellow
        else: color = "\033[91m" # Red
        
        reset = "\033[0m"
        print(f"{color}{r['model']:<20} | {r['type']:<7} | {r['status']:<12} | {r['estimated_ram']:<10}{reset}")
    
    print("-" * 60)
    print("\n* PERMANENT: Safe to run alongside full Minecraft load.")
    print("* CONDITIONAL: Safe only if Minecraft usage is normal (~2GB/world).")
    print("* INCOMPATIBLE: High risk of OOM Killer crashing Minecraft.")
    print("\nJSON Output for Automation:")
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    if platform.system() != "Linux":
        print("This script is designed for Linux servers.")
    
    # 1. Gather Data
    cpu = get_cpu_info()
    mem = get_memory_info()
    if mem["total"] == 0: 
        # Fallback for non-proc systems
        mem["total"] = 32.0 
    
    # 2. Analyze
    analysis = analyze_capacity(mem, cpu)
    
    # 3. Report
    print_table(analysis)

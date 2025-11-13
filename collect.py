import time, json, psutil, os

DATA_DIR = os.getenv("DATA_DIR", "/app/data")
OUT_FILE = os.path.join(DATA_DIR, "metrics.json")
INTERVAL = int(os.getenv("COLLECT_INTERVAL_SECONDS", "5"))

os.makedirs(DATA_DIR, exist_ok=True)

while True:
    data = {
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "mem_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        "timestamp": int(time.time())
    }
    try:
        existing = []
        if os.path.exists(OUT_FILE):
            with open(OUT_FILE, "r") as f:
                existing = json.load(f)
        existing.append(data)
        existing = existing[-200:]
        with open(OUT_FILE, "w") as f:
            json.dump(existing, f)
    except Exception as e:
        print("Error writing metrics:", e)
    time.sleep(INTERVAL)

import os
import subprocess
import time
import psutil

# Set environment variables
os.environ["IS_DOCKER"] = "false"
os.environ["REDIS_HOST"] = "localhost"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5433/bittensor"
os.environ["API_TOKEN"] = "datura"
os.environ["DATURA_APIKEY"] = "dt$q4qWC2K5mwT5BnNh0ZNF9MfeMDJenJ-pddsi_rE1FZ8"
os.environ["CHUTES_API_KEY"] = "cpk_9402c24cc755440b94f4b0931ebaa272.7a748b60e4a557f6957af9ce25778f49.8huXjHVlrSttzKuuY0yU2Fy4qEskr5J0"
os.environ["WALLET_MNEMONIC"] = "diamond like interest affair safe clarify lawsuit innocent beef van grief color"
os.environ["WALLET_HOTKEY"] = "default_hotkey_name"

print("Cleaning up old processes...")

for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = proc.info.get('cmdline') or []
        if any("uvicorn" in cmd for cmd in cmdline) or any("celery" in cmd for cmd in cmdline):
            print(f"Terminating process {proc.pid} ({cmdline})")
            proc.terminate()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        continue

time.sleep(2)  # Let the OS settle

# Start FastAPI server
print("Starting FastAPI server...")
api_proc = subprocess.Popen(
    ["uvicorn", "bittensor_async_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
)

time.sleep(3)  # Let FastAPI warm up

# Start Celery worker
print("Starting Celery worker...")
celery_proc = subprocess.Popen(
    ["celery", "-A", "celery_worker", "worker", "--loglevel=info"]
)

print("API and worker are now running. Press Ctrl+C to stop.")

try:
    api_proc.wait()
    celery_proc.wait()
except KeyboardInterrupt:
    print("\nStopping processes...")
    api_proc.terminate()
    celery_proc.terminate()
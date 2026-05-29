import os
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

def main():
    backend_dir = os.path.join(PROJECT_ROOT, "backend")
    frontend_dir = os.path.join(PROJECT_ROOT, "frontend")

    print("Starting backend and frontend dev servers concurrently...")
    
    # 1. Spawn backend (Uvicorn)
    backend_cmd = ["uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"]
    print(f"Starting backend: {' '.join(backend_cmd)} in {backend_dir}")
    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=backend_dir,
        shell=sys.platform == "win32"
    )

    # 2. Spawn frontend (Vite)
    frontend_cmd = ["npm", "run", "dev"]
    print(f"Starting frontend: {' '.join(frontend_cmd)} in {frontend_dir}")
    frontend_proc = subprocess.Popen(
        frontend_cmd,
        cwd=frontend_dir,
        shell=sys.platform == "win32"
    )

    try:
        # Keep main thread alive, monitoring children
        while True:
            if backend_proc.poll() is not None:
                print("Backend server exited unexpectedly.")
                break
            if frontend_proc.poll() is not None:
                print("Frontend server exited unexpectedly.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down dev servers...")
    finally:
        # Terminate both processes
        backend_proc.terminate()
        frontend_proc.terminate()
        
        # Wait a moment, force kill if needed
        try:
            backend_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            backend_proc.kill()
            
        try:
            frontend_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            frontend_proc.kill()

        print("Dev servers stopped.")

if __name__ == "__main__":
    main()

import subprocess
import time
import sys
import signal
import os
import threading

# 실행할 프로세스들을 담을 리스트
processes = []

def signal_handler(sig, frame):
    print("\n[Run Script] Shutting down all services...")
    for p in processes:
        if p.poll() is None: # 아직 실행 중이면
            p.terminate()
    sys.exit(0)

# Ctrl+C 시그널 감지 등록
signal.signal(signal.SIGINT, signal_handler)

def stream_output(process, prefix):
    """프로세스의 출력을 실시간으로 출력 (디버깅용)"""
    for line in iter(process.stdout.readline, b''):
        print(f"[{prefix}] {line.decode().strip()}")

def run_services():
    try:
        # 1. OpenWebUI 실행 (uvx 사용 - 격리된 환경)
        # 8080 포트 사용 (기본값)
        print("[Run Script] Starting OpenWebUI on port 8080 using uvx...")
        # uvx는 uv가 설치되어 있어야 함. (현재 uv 사용 중이므로 가능)
        # stdout=subprocess.PIPE 로 하면 출력을 캡처할 수 있음
        env = os.environ.copy()
        env["PORT"] = "8080"
        # OLLAMA_BASE_URL 설정 (로컬 Ollama 사용 시)
        env["OLLAMA_BASE_URL"] = "http://localhost:11434"
        
        p_openwebui = subprocess.Popen(
            ["uvx", "open-webui", "serve"], 
            env=env
            # stdout=subprocess.PIPE, 
            # stderr=subprocess.PIPE
        )
        processes.append(p_openwebui)
        
        # 2. FastAPI 실행
        print("[Run Script] Starting FastAPI on port 8000...")
        p_fastapi = subprocess.Popen(
            ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
            env=os.environ.copy()
        )
        processes.append(p_fastapi)

        print("\n" + "="*40)
        print("🚀 All services are starting!")
        print("🏠 FastAPI Dashboard: http://localhost:8000")
        print("🤖 OpenWebUI:       http://localhost:8080")
        print("="*40 + "\n")
        
        # 프로세스 상태 모니터링
        while True:
            time.sleep(1)
            # 만약 둘 중 하나라도 죽으면 같이 종료
            if p_fastapi.poll() is not None:
                print("[Run Script] FastAPI process exited.")
                break
            if p_openwebui.poll() is not None:
                print("[Run Script] OpenWebUI process exited.")
                break

    except Exception as e:
        print(f"Error: {e}")
    finally:
        signal_handler(None, None)

if __name__ == "__main__":
    run_services()

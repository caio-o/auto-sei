from config import DEBUG

def log(msg: str):
    print(f"[INFO] {msg}", flush=True)

def aviso(msg: str):
    print(f"[AVISO] {msg}", flush=True)

def erro(msg: str):
    print(f"[ERRO] {msg}", flush=True)

def debug(msg: str):
    if DEBUG:
        print(f"[DEBUG] {msg}", flush=True)
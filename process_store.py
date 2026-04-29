import json
import re
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROCESS_DIR = SCRIPT_DIR / "processos_ocr"
CONFIG_PATH = SCRIPT_DIR / "app_config.json"


DEFAULT_APP_CONFIG = {
    "modelo_word_path": "",
    "nome_usuario_salvar": "",
    "ultimo_processo": "",
    "boot_script_path": "",
    "boot_macro": "",
}


def ensure_process_dir():
    PROCESS_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_filename(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r'[\\/*?:"<>|]', "_", text)
    text = re.sub(r"\s+", "_", text)
    return text


def get_process_json_path(process_number: str) -> Path:
    ensure_process_dir()
    safe_name = sanitize_filename(process_number)
    return PROCESS_DIR / f"{safe_name}.json"


def load_process_data(process_number: str):
    if not process_number:
        return None

    path = get_process_json_path(process_number)
    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_process_data(process_number: str, data: dict):
    if not process_number:
        return

    path = get_process_json_path(process_number)
    ensure_process_dir()

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def delete_process_data(process_number: str) -> bool:
    if not process_number:
        return False

    path = get_process_json_path(process_number)
    if not path.exists():
        return False

    path.unlink()
    return True


def list_saved_processes() -> list[str]:
    ensure_process_dir()

    files = sorted(PROCESS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    results = []

    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            numero = data.get("numero_processo", "").strip()
            results.append(numero if numero else path.stem)
        except Exception:
            results.append(path.stem)

    return results


def load_app_config() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULT_APP_CONFIG)

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        merged = dict(DEFAULT_APP_CONFIG)
        merged.update(data if isinstance(data, dict) else {})
        return merged
    except Exception:
        return dict(DEFAULT_APP_CONFIG)


def save_app_config(config: dict):
    merged = dict(DEFAULT_APP_CONFIG)
    merged.update(config if isinstance(config, dict) else {})

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

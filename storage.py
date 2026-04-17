import json
from pathlib import Path
from config import (
    ARQUIVO_CAMPOS_OCR,
    ARQUIVO_CHECKPOINTS_REF,
    ARQUIVO_RESULTADO,
)
from logger import log, erro

def carregar_json(caminho: Path, padrao):
    if not caminho.exists():
        return padrao
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        erro(f"Falha ao carregar {caminho}: {e}")
        return padrao

def salvar_json(caminho: Path, dados):
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        log(f"Arquivo salvo: {caminho.resolve()}")
    except Exception as e:
        erro(f"Falha ao salvar {caminho}: {e}")

def carregar_campos_ocr():
    return carregar_json(ARQUIVO_CAMPOS_OCR, {})

def salvar_campos_ocr(dados):
    salvar_json(ARQUIVO_CAMPOS_OCR, dados)

def carregar_checkpoints_ref():
    return carregar_json(ARQUIVO_CHECKPOINTS_REF, {})

def salvar_checkpoints_ref(dados):
    salvar_json(ARQUIVO_CHECKPOINTS_REF, dados)

def salvar_resultado_formatado(resultados_ocr):
    campos = carregar_campos_ocr()
    resultado_final = {}

    for indice, dados in resultados_ocr.items():
        info = campos.get(str(indice))
        if not info:
            continue

        nome = info.get("nome_campo", f"campo_{indice}")
        valor = dados.get("valor")
        label = dados.get("label")

        resultado_final[nome] = {
            "valor": valor,
            "label": label,
            "indice": int(indice)
        }

    salvar_json(ARQUIVO_RESULTADO, resultado_final)
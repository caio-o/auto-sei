import pyautogui
import pytesseract
from PIL import ImageOps, ImageEnhance, ImageFilter
from config import USAR_OCR
from logger import aviso, erro

def preparar_imagem_para_ocr(img):
    img = ImageOps.grayscale(img)
    img = ImageEnhance.Contrast(img).enhance(2.5)
    img = img.filter(ImageFilter.SHARPEN)
    return img

def ler_texto_da_imagem(img):
    if not USAR_OCR:
        aviso("OCR desativado.")
        return ""
    try:
        img = preparar_imagem_para_ocr(img)
        texto = pytesseract.image_to_string(img, lang="por")
        return texto.strip()
    except Exception as e:
        erro(f"Falha no OCR: {e}")
        return ""

def quebrar_linhas_validas(texto: str):
    linhas = []
    for linha in texto.splitlines():
        linha = " ".join(linha.strip().split())
        if linha:
            linhas.append(linha)
    return linhas

def extrair_label_e_valor(texto: str):
    linhas = quebrar_linhas_validas(texto)
    if not linhas:
        return {"label": None, "valor": None}
    if len(linhas) == 1:
        return {"label": linhas[0], "valor": None}
    return {"label": linhas[0], "valor": linhas[1]}

def extrair_texto_da_regiao(regiao):
    try:
        img = pyautogui.screenshot(region=regiao)
    except Exception as e:
        erro(f"Falha ao capturar região {regiao}: {e}")
        return None

    texto = ler_texto_da_imagem(img)
    partes = extrair_label_e_valor(texto)

    return {
        "regiao": regiao,
        "texto_bruto": texto,
        "label": partes["label"],
        "valor": partes["valor"],
    }
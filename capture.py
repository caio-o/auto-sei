import pyautogui
import state
from config import PASTA_IMAGENS
from logger import log, erro
from storage import (
    carregar_campos_ocr,
    salvar_campos_ocr,
    carregar_checkpoints_ref,
    salvar_checkpoints_ref,
)
from ocr_tools import ler_texto_da_imagem, extrair_label_e_valor
from utils import indice_valido, calcular_regiao, calcular_centro_regiao

def limpar_estado_captura():
    state.modo_captura = None
    state.indice_captura = None
    state.inicio_selecao = None
    state.fim_selecao = None

def iniciar_captura_campo_ocr(indice: int):
    if not indice_valido(indice):
        erro(f"Índice inválido: {indice}")
        return

    state.modo_captura = "campo_ocr"
    state.indice_captura = indice
    state.inicio_selecao = None
    state.fim_selecao = None

    log("=" * 80)
    log(f"MODO CAPTURAR CAMPO OCR -> índice {indice}")
    log("Captura o campo inteiro, de preferência label + valor.")
    log("=" * 80)

def iniciar_captura_checkpoint(indice: int):
    if not indice_valido(indice):
        erro(f"Índice inválido: {indice}")
        return

    state.modo_captura = "checkpoint_img"
    state.indice_captura = indice
    state.inicio_selecao = None
    state.fim_selecao = None

    log("=" * 80)
    log(f"MODO CAPTURAR IMAGEM -> índice {indice}")
    log("Clica e arrasta cobrindo só a imagem de referência.")
    log("Depois ela pode ser usada para esperar/clicar por referência ou na tela.")
    log("=" * 80)

def finalizar_captura_campo():
    if state.inicio_selecao is None or state.fim_selecao is None:
        erro("Captura do campo OCR incompleta.")
        limpar_estado_captura()
        return

    regiao = calcular_regiao(state.inicio_selecao, state.fim_selecao)
    x, y, largura, altura = regiao

    if largura <= 0 or altura <= 0:
        erro("Área capturada inválida.")
        limpar_estado_captura()
        return

    caminho_img = PASTA_IMAGENS / f"campo_{state.indice_captura}.png"

    try:
        img = pyautogui.screenshot(region=regiao)
        img.save(caminho_img)
    except Exception as e:
        erro(f"Falha ao capturar campo OCR: {e}")
        limpar_estado_captura()
        return

    campos = carregar_campos_ocr()
    antigo = campos.get(str(state.indice_captura), {})

    campos[str(state.indice_captura)] = {
        "indice": state.indice_captura,
        "imagem": str(caminho_img),
        "regiao": [x, y, largura, altura],
        "nome_campo": antigo.get("nome_campo", f"campo_{state.indice_captura}"),
        "papel": "ocr_origem",
    }
    salvar_campos_ocr(campos)

    texto = ler_texto_da_imagem(img)
    partes = extrair_label_e_valor(texto)

    log("=" * 80)
    log(f"CAMPO OCR CAPTURADO -> índice {state.indice_captura}")
    log(f"Região -> ({x}, {y}, {largura}, {altura})")
    log(f"Imagem -> {caminho_img.resolve()}")
    log(f"Nome do campo -> {campos[str(state.indice_captura)]['nome_campo']}")
    log(f"Label OCR -> {repr(partes['label'])}")
    log(f"Valor OCR -> {repr(partes['valor'])}")
    log("=" * 80)

    limpar_estado_captura()

def finalizar_captura_checkpoint():
    if state.inicio_selecao is None or state.fim_selecao is None:
        erro("Captura da imagem incompleta.")
        limpar_estado_captura()
        return

    regiao = calcular_regiao(state.inicio_selecao, state.fim_selecao)
    x, y, largura, altura = regiao

    if largura <= 0 or altura <= 0:
        erro("Área capturada inválida.")
        limpar_estado_captura()
        return

    caminho_img = PASTA_IMAGENS / f"{state.indice_captura}.png"

    try:
        img = pyautogui.screenshot(region=regiao)
        img.save(caminho_img)
    except Exception as e:
        erro(f"Falha ao capturar checkpoint: {e}")
        limpar_estado_captura()
        return

    centro = calcular_centro_regiao(regiao)

    checkpoints = carregar_checkpoints_ref()
    antigo = checkpoints.get(str(state.indice_captura), {})

    checkpoints[str(state.indice_captura)] = {
        "indice": state.indice_captura,
        "imagem": str(caminho_img),
        "regiao_capturada": [x, y, largura, altura],
        "centro_esperado": [centro[0], centro[1]],
        "papel": antigo.get("papel", "referencia_visual"),
    }
    salvar_checkpoints_ref(checkpoints)

    log("=" * 80)
    log(f"IMAGEM CAPTURADA -> índice {state.indice_captura}")
    log(f"Imagem -> {caminho_img.resolve()}")
    log(f"Região -> ({x}, {y}, {largura}, {altura})")
    log(f"Centro esperado -> {centro}")
    log("=" * 80)

    limpar_estado_captura()
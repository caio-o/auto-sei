import json
import state
from logger import log, aviso, debug
from utils import calcular_espera, indice_valido
from storage import carregar_checkpoints_ref

def registrar_acao(tipo: str, **dados):
    acao = {
        "tipo": tipo,
        "espera": calcular_espera(),
        **dados
    }
    state.acoes.append(acao)
    debug(f"Ação gravada: {acao}")

def salvar_macro(caminho_macro):
    with open(caminho_macro, "w", encoding="utf-8") as f:
        json.dump(state.acoes, f, ensure_ascii=False, indent=2)
    log(f"Macro salva em: {caminho_macro.resolve()}")

def carregar_macro(caminho_macro):
    if not caminho_macro.exists():
        aviso(f"Nenhuma macro encontrada: {caminho_macro.resolve()}")
        return []

    with open(caminho_macro, "r", encoding="utf-8") as f:
        dados = json.load(f)

    log(f"Macro carregada ({caminho_macro.name}) com {len(dados)} ação(ões).")
    return dados

def apagar_macro(caminho_macro):
    if caminho_macro == state.ARQUIVO_MACRO_ATUAL:
        state.acoes = []

    if caminho_macro.exists():
        caminho_macro.unlink()
        log(f"Macro apagada: {caminho_macro.resolve()}")
    else:
        aviso(f"Não havia macro para apagar: {caminho_macro.resolve()}")

def gravar_esperar_ref(indice: int, timeout):
    if not state.gravando or not indice_valido(indice):
        return
    registrar_acao("esperar_ref", indice=indice, timeout=timeout)
    log(f"Ação gravada -> esperar_ref ({indice})")

def gravar_clicar_ref(indice: int, timeout):
    if not state.gravando or not indice_valido(indice):
        return
    registrar_acao("clicar_ref", indice=indice, timeout=timeout)
    log(f"Ação gravada -> clicar_ref ({indice})")

def gravar_clicar_tela(indice: int, timeout):
    if not state.gravando or not indice_valido(indice):
        return
    registrar_acao("clicar_tela", indice=indice, timeout=timeout)
    log(f"Ação gravada -> clicar_tela ({indice})")

def gravar_esperar_tela(indice: int, timeout):
    if not state.gravando or not indice_valido(indice):
        return
    registrar_acao("esperar_tela", indice=indice, timeout=timeout)
    log(f"Ação gravada -> esperar_tela ({indice})")

def gravar_ocr(indice: int):
    if not state.gravando or not indice_valido(indice):
        return
    registrar_acao("ocr", indice=indice)
    log(f"Ação gravada -> ocr ({indice})")

def gravar_colar_data_em_destino(destino_indice: int, timeout):
    if not state.gravando or not indice_valido(destino_indice):
        return
    registrar_acao("colar_data_em_destino", destino_indice=destino_indice, timeout=timeout)
    log(f"Ação gravada -> colar_data_em_destino ({destino_indice})")

def gravar_colar_valor_de_origem_em_destino(origem_indice: int, destino_indice: int, timeout):
    if not state.gravando:
        return
    if not indice_valido(origem_indice) or not indice_valido(destino_indice):
        return

    registrar_acao(
        "colar_valor_de_origem_em_destino",
        origem_indice=origem_indice,
        destino_indice=destino_indice,
        timeout=timeout,
    )
    log(f"Ação gravada -> colar_valor_de_origem_em_destino (origem={origem_indice}, destino={destino_indice})")

def gravar_confirmacao_manual():
    if not state.gravando:
        aviso("Confirmação manual ignorada porque não está gravando.")
        return

    registrar_acao("confirmar")
    log("Ponto de confirmação manual gravado.")
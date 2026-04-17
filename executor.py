import pyautogui
import state
from pathlib import Path
from datetime import datetime
from config import (
    DURACAO_MOVIMENTO,
    VELOCIDADE_EXECUCAO,
    TIMEOUT_CHECKPOINT,
    EXECUTAR_MACRO_2_QUANDO,
    DELAY_ENTRE_MACROS,
    MODO_TESTE,
    CONFIANCA,
    GRAYSCALE,
    ARQUIVO_MACRO_1,
    ARQUIVO_MACRO_2,
)
from logger import log, aviso, erro, debug
from macro import carregar_macro
from storage import (
    carregar_checkpoints_ref,
    carregar_campos_ocr,
    salvar_resultado_formatado,
)
from ocr_tools import extrair_texto_da_regiao
from utils import (
    esperar_interrompivel,
    esperar_confirmacao_manual,
    tempo_ajustado,
    deve_parar,
    centro_box,
    distancia,
    deve_executar_macro_2,
    parar_execucao_event,
    pausa_execucao_event,
)

def procurar_checkpoint_inteligente(indice: int):
    checkpoints = carregar_checkpoints_ref()
    info = checkpoints.get(str(indice))

    if not info:
        erro(f"Checkpoint {indice} não encontrado no JSON.")
        return None

    caminho_img = info["imagem"]
    regiao_capturada = tuple(info["regiao_capturada"])
    centro_esperado = tuple(info["centro_esperado"])

    x, y, largura, altura = regiao_capturada
    margem = 150

    regiao_prioritaria = (
        max(0, x - margem),
        max(0, y - margem),
        largura + (margem * 2),
        altura + (margem * 2),
    )

    try:
        resultados = list(pyautogui.locateAllOnScreen(
            caminho_img,
            confidence=CONFIANCA,
            grayscale=GRAYSCALE,
            region=regiao_prioritaria
        ))
    except Exception as e:
        erro(f"Erro procurando checkpoint na região prioritária: {e}")
        return None

    if not resultados:
        try:
            resultados = list(pyautogui.locateAllOnScreen(
                caminho_img,
                confidence=CONFIANCA,
                grayscale=GRAYSCALE
            ))
        except Exception as e:
            erro(f"Erro procurando checkpoint na tela inteira: {e}")
            return None

    if not resultados:
        return None

    melhor = None
    melhor_dist = float("inf")

    for box in resultados:
        c = centro_box(box)
        d = distancia(c, centro_esperado)
        if d < melhor_dist:
            melhor_dist = d
            melhor = box

    return melhor

def procurar_imagem_tela(indice: int):
    checkpoints = carregar_checkpoints_ref()
    info = checkpoints.get(str(indice))

    if not info:
        erro(f"Imagem {indice} não encontrada no JSON.")
        return None

    caminho_img = info["imagem"]

    try:
        resultados = list(pyautogui.locateAllOnScreen(
            caminho_img,
            confidence=CONFIANCA,
            grayscale=GRAYSCALE
        ))
    except Exception as e:
        erro(f"Erro ao procurar imagem na tela: {e}")
        return None

    if not resultados:
        return None

    return resultados[0]

def esperar_checkpoint(indice: int, timeout=TIMEOUT_CHECKPOINT):
    import time
    inicio = time.time()

    while time.time() - inicio < timeout:
        if deve_parar():
            return None

        while not pausa_execucao_event.is_set():
            if deve_parar():
                return None
            time.sleep(0.05)

        box = procurar_checkpoint_inteligente(indice)
        if box is not None:
            return box

        if not esperar_interrompivel(0.3):
            return None

    return None

def esperar_imagem_tela(indice: int, timeout=TIMEOUT_CHECKPOINT):
    import time
    inicio = time.time()

    while time.time() - inicio < timeout:
        if deve_parar():
            return None

        while not pausa_execucao_event.is_set():
            if deve_parar():
                return None
            time.sleep(0.05)

        box = procurar_imagem_tela(indice)
        if box is not None:
            return box

        if not esperar_interrompivel(0.3):
            return None

    return None

def clicar_box(box):
    x, y = centro_box(box)
    pyautogui.moveTo(x, y, duration=max(0.0, DURACAO_MOVIMENTO / VELOCIDADE_EXECUCAO))

    if MODO_TESTE:
        log(f"[TESTE] clicaria em ({x}, {y})")
        return True

    pyautogui.click(x, y)
    log(f"Clique realizado em ({x}, {y})")
    return True

def colar_texto(texto: str):
    if texto is None:
        aviso("Nada para colar.")
        return False

    if MODO_TESTE:
        log(f"[TESTE] colaria o texto: {repr(texto)}")
        return True

    try:
        pyautogui.write(str(texto), interval=0.01)
        log(f"Texto colado: {repr(texto)}")
        return True
    except Exception as e:
        erro(f"Falha ao colar texto: {e}")
        return False

def formatar_data_brasil():
    return datetime.now().strftime("%d/%m/%Y")

def executar_ocr_do_checkpoint(indice: int):
    campos = carregar_campos_ocr()
    info = campos.get(str(indice))

    if not info:
        return None

    regiao = tuple(info["regiao"])
    resultado = extrair_texto_da_regiao(regiao)
    if resultado is None:
        return None

    state.resultados_ocr_execucao[str(indice)] = resultado
    state.ultimo_label_extraido = resultado.get("label")
    state.ultimo_valor_extraido = resultado.get("valor")

    log(f"[OCR {indice}] label -> {repr(resultado['label'])}")
    log(f"[OCR {indice}] valor -> {repr(resultado['valor'])}")
    return resultado

def colar_data_em_destino(destino_indice: int, timeout=TIMEOUT_CHECKPOINT):
    box = esperar_checkpoint(destino_indice, timeout=timeout)
    if box is None:
        erro(f"Falha ao localizar destino {destino_indice}")
        return False

    if not clicar_box(box):
        return False

    return colar_texto(formatar_data_brasil())

def colar_valor_de_origem_em_destino(origem_indice: int, destino_indice: int, timeout=TIMEOUT_CHECKPOINT):
    dados = state.resultados_ocr_execucao.get(str(origem_indice))
    if not dados:
        aviso(f"Não existe valor extraído na origem {origem_indice}")
        return False

    valor = dados.get("valor")
    if not valor:
        aviso(f"A origem {origem_indice} não tem valor para colar")
        return False

    box = esperar_checkpoint(destino_indice, timeout=timeout)
    if box is None:
        erro(f"Falha ao localizar destino {destino_indice}")
        return False

    if not clicar_box(box):
        return False

    return colar_texto(valor)

def executar_mouse_down(botao: str, x: int, y: int):
    if deve_parar():
        return False
    pyautogui.moveTo(x, y, duration=max(0.0, DURACAO_MOVIMENTO / VELOCIDADE_EXECUCAO))
    if MODO_TESTE:
        return True
    pyautogui.mouseDown(x=x, y=y, button=botao)
    return True

def executar_mouse_up(botao: str, x: int, y: int):
    if deve_parar():
        return False
    pyautogui.moveTo(x, y, duration=max(0.0, DURACAO_MOVIMENTO / VELOCIDADE_EXECUCAO))
    if MODO_TESTE:
        return True
    pyautogui.mouseUp(x=x, y=y, button=botao)
    return True

def executar_move(x: int, y: int):
    if deve_parar():
        return False
    pyautogui.moveTo(x, y, duration=max(0.0, DURACAO_MOVIMENTO / VELOCIDADE_EXECUCAO))
    return True

def executar_drag_move(x: int, y: int):
    if deve_parar():
        return False
    pyautogui.moveTo(x, y, duration=max(0.0, DURACAO_MOVIMENTO / VELOCIDADE_EXECUCAO))
    return True

def executar_scroll(dx: int, dy: int):
    if deve_parar():
        return False
    if MODO_TESTE:
        return True
    pyautogui.scroll(dy)
    return True

def executar_key_down(tecla: str):
    if deve_parar():
        return False
    if MODO_TESTE:
        return True
    pyautogui.keyDown(tecla)
    return True

def executar_key_up(tecla: str):
    if deve_parar():
        return False
    if MODO_TESTE:
        return True
    pyautogui.keyUp(tecla)
    return True

def executar_confirmacao_manual():
    log("PONTO DE CONFIRMAÇÃO MANUAL ENCONTRADO")
    log("Aperta F12 para continuar. F11 pausa/continua. ESC cancela.")
    return esperar_confirmacao_manual()

def executar_macro_de_arquivo(caminho_macro):
    dados = carregar_macro(caminho_macro)
    if not dados:
        aviso(f"Não há macro para executar: {caminho_macro.resolve()}")
        state.status_ultima_execucao = "erro"
        return False

    log(f"Iniciando execução de {caminho_macro.name}")

    for i, acao in enumerate(dados, start=1):
        if deve_parar():
            state.status_ultima_execucao = "cancelada"
            return False

        tipo = acao.get("tipo")
        espera = tempo_ajustado(acao.get("espera", 0))

        if espera > 0:
            if not esperar_interrompivel(espera):
                state.status_ultima_execucao = "cancelada"
                return False

        ok = True

        try:
            if tipo == "move":
                ok = executar_move(acao["x"], acao["y"])
            elif tipo == "drag_move":
                ok = executar_drag_move(acao["x"], acao["y"])
            elif tipo == "mouse_down":
                ok = executar_mouse_down(acao["botao"], acao["x"], acao["y"])
            elif tipo == "mouse_up":
                ok = executar_mouse_up(acao["botao"], acao["x"], acao["y"])
            elif tipo == "scroll":
                ok = executar_scroll(acao["dx"], acao["dy"])
            elif tipo == "key_down":
                ok = executar_key_down(acao["tecla"])
            elif tipo == "key_up":
                ok = executar_key_up(acao["tecla"])
            elif tipo == "esperar_ref":
                ok = esperar_checkpoint(acao["indice"], acao.get("timeout", TIMEOUT_CHECKPOINT)) is not None
            elif tipo == "clicar_ref":
                box = esperar_checkpoint(acao["indice"], acao.get("timeout", TIMEOUT_CHECKPOINT))
                ok = box is not None and clicar_box(box)
            elif tipo == "clicar_tela":
                box = esperar_imagem_tela(acao["indice"], acao.get("timeout", TIMEOUT_CHECKPOINT))
                ok = box is not None and clicar_box(box)
            elif tipo == "esperar_tela":
                ok = esperar_imagem_tela(acao["indice"], acao.get("timeout", TIMEOUT_CHECKPOINT)) is not None
            elif tipo == "ocr":
                executar_ocr_do_checkpoint(acao["indice"])
            elif tipo == "colar_data_em_destino":
                ok = colar_data_em_destino(acao["destino_indice"], acao.get("timeout", TIMEOUT_CHECKPOINT))
            elif tipo == "colar_valor_de_origem_em_destino":
                ok = colar_valor_de_origem_em_destino(
                    acao["origem_indice"],
                    acao["destino_indice"],
                    acao.get("timeout", TIMEOUT_CHECKPOINT),
                )
            elif tipo == "confirmar":
                ok = executar_confirmacao_manual()
            else:
                aviso(f"Tipo desconhecido: {tipo}")

        except pyautogui.FailSafeException:
            erro("Execução abortada pelo FAILSAFE.")
            state.status_ultima_execucao = "cancelada"
            return False
        except Exception as e:
            erro(f"Erro na ação {i}: {e}")
            state.status_ultima_execucao = "erro"
            return False

        if not ok:
            erro(f"Ação {i} falhou.")
            state.status_ultima_execucao = "erro"
            return False

    state.status_ultima_execucao = "finalizada"
    log(f"Macro finalizada: {caminho_macro.name}")
    return True

def executar_fluxo_encadeado():
    try:
        state.resultados_ocr_execucao = {}
        state.status_ultima_execucao = None

        if not esperar_interrompivel(1.0):
            state.status_ultima_execucao = "cancelada"
            return

        if ARQUIVO_MACRO_1.exists():
            executar_macro_de_arquivo(ARQUIVO_MACRO_1)
            status1 = state.status_ultima_execucao
        else:
            erro(f"Macro principal não encontrada: {ARQUIVO_MACRO_1.resolve()}")
            state.status_ultima_execucao = "erro"
            return

        if ARQUIVO_MACRO_2.exists():
            dados_macro_2 = carregar_macro(ARQUIVO_MACRO_2)
            if dados_macro_2 and deve_executar_macro_2(status1, EXECUTAR_MACRO_2_QUANDO):
                parar_execucao_event.clear()
                if not esperar_interrompivel(DELAY_ENTRE_MACROS):
                    state.status_ultima_execucao = "cancelada"
                    return
                executar_macro_de_arquivo(ARQUIVO_MACRO_2)

        salvar_resultado_formatado(state.resultados_ocr_execucao)

    finally:
        state.executando = False
        parar_execucao_event.clear()
        pausa_execucao_event.set()
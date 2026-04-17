from pynput import mouse, keyboard
import threading
import state
from config import TIMEOUT_CHECKPOINT
from logger import log
from utils import (
    nome_tecla,
    tecla_eh_ctrl,
    tecla_eh_alt,
    tecla_eh_shift,
    tecla_eh_win,
    nome_botao,
    iniciar_tempo,
    parar_execucao_event,
    pausa_execucao_event,
    confirmar_execucao_event,
)
from capture import (
    iniciar_captura_campo_ocr,
    iniciar_captura_checkpoint,
    finalizar_captura_campo,
    finalizar_captura_checkpoint,
)
from macro import (
    registrar_acao,
    salvar_macro,
    apagar_macro,
    gravar_esperar_ref,
    gravar_clicar_ref,
    gravar_clicar_tela,
    gravar_esperar_tela,
    gravar_ocr,
    gravar_confirmacao_manual,
)
from executor import executar_fluxo_encadeado

def selecionar_macro_1():
    from config import ARQUIVO_MACRO_1
    if state.gravando or state.executando:
        return
    state.ARQUIVO_MACRO_ATUAL = ARQUIVO_MACRO_1
    log(f"Macro ativa -> {state.ARQUIVO_MACRO_ATUAL.resolve()}")

def selecionar_macro_2():
    from config import ARQUIVO_MACRO_2
    if state.gravando or state.executando:
        return
    state.ARQUIVO_MACRO_ATUAL = ARQUIVO_MACRO_2
    log(f"Macro ativa -> {state.ARQUIVO_MACRO_ATUAL.resolve()}")

def iniciar_gravacao():
    if state.executando:
        return

    state.gravando = True
    state.acoes = []
    state.teclas_pressionadas = set()
    state.botao_esquerdo_pressionado = False
    state.botao_direito_pressionado = False
    state.botao_meio_pressionado = False
    state.ctrl_pressionado = False
    state.alt_pressionado = False
    state.shift_pressionado = False
    state.win_pressionado = False
    state.ultimo_movimento_gravado = 0.0
    iniciar_tempo()

    log(f"GRAVAÇÃO INICIADA -> {state.ARQUIVO_MACRO_ATUAL.resolve()}")

def parar_gravacao():
    state.gravando = False
    salvar_macro(state.ARQUIVO_MACRO_ATUAL)
    log("GRAVAÇÃO FINALIZADA")

def iniciar_execucao_em_thread():
    if state.executando:
        return

    parar_execucao_event.clear()
    pausa_execucao_event.set()
    confirmar_execucao_event.clear()

    state.executando = True
    state.thread_execucao = threading.Thread(target=executar_fluxo_encadeado, daemon=True)
    state.thread_execucao.start()

def parar_execucao():
    if state.executando:
        log("Parando execução...")
        parar_execucao_event.set()

def alternar_pausa_execucao():
    if not state.executando:
        return

    if pausa_execucao_event.is_set():
        pausa_execucao_event.clear()
        log("EXECUÇÃO PAUSADA")
    else:
        pausa_execucao_event.set()
        log("EXECUÇÃO RETOMADA")

def confirmar_execucao_manual():
    if not state.executando:
        return
    confirmar_execucao_event.set()
    log("Confirmação manual enviada.")

def on_move(x, y):
    from config import GRAVAR_MOVIMENTO_MOUSE, INTERVALO_MOVIMENTO
    import time

    if not state.gravando or not GRAVAR_MOVIMENTO_MOUSE:
        return

    if state.modo_captura is not None:
        return

    agora = time.time()
    if agora - state.ultimo_movimento_gravado < INTERVALO_MOVIMENTO:
        return

    state.ultimo_movimento_gravado = agora

    if state.botao_esquerdo_pressionado or state.botao_direito_pressionado or state.botao_meio_pressionado:
        registrar_acao("drag_move", x=int(x), y=int(y))
    else:
        registrar_acao("move", x=int(x), y=int(y))

def on_click(x, y, button, pressed):
    if state.modo_captura is not None and button == mouse.Button.left:
        if pressed:
            state.inicio_selecao = (x, y)
            log(f"Início da captura: {state.inicio_selecao}")
        else:
            state.fim_selecao = (x, y)
            log(f"Fim da captura: {state.fim_selecao}")

            if state.modo_captura == "campo_ocr":
                finalizar_captura_campo()
            elif state.modo_captura == "checkpoint_img":
                finalizar_captura_checkpoint()
        return

    if not state.gravando:
        return

    botao = nome_botao(button)

    if botao == "left":
        state.botao_esquerdo_pressionado = pressed
    elif botao == "right":
        state.botao_direito_pressionado = pressed
    elif botao == "middle":
        state.botao_meio_pressionado = pressed

    if pressed:
        registrar_acao("mouse_down", x=int(x), y=int(y), botao=botao)
    else:
        registrar_acao("mouse_up", x=int(x), y=int(y), botao=botao)

def on_scroll(x, y, dx, dy):
    if not state.gravando or state.modo_captura is not None:
        return
    registrar_acao("scroll", x=int(x), y=int(y), dx=int(dx), dy=int(dy))

def on_key_press(key):
    if tecla_eh_ctrl(key):
        state.ctrl_pressionado = True
    if tecla_eh_alt(key):
        state.alt_pressionado = True
    if tecla_eh_shift(key):
        state.shift_pressionado = True
    if tecla_eh_win(key):
        state.win_pressionado = True

    if key == keyboard.Key.esc:
        if state.executando:
            parar_execucao()
            return
        return False

    if key == keyboard.Key.f11:
        alternar_pausa_execucao()
        return

    if key == keyboard.Key.f12:
        confirmar_execucao_manual()
        return

    if key == keyboard.Key.f6:
        selecionar_macro_1()
        return

    if key == keyboard.Key.f7:
        selecionar_macro_2()
        return

    if key == keyboard.Key.f8:
        if state.gravando:
            parar_gravacao()
        else:
            iniciar_gravacao()
        return

    if key == keyboard.Key.f9:
        iniciar_execucao_em_thread()
        return

    if key == keyboard.Key.f10:
        apagar_macro(state.ARQUIVO_MACRO_ATUAL)
        return

    tecla = nome_tecla(key)

    if state.ctrl_pressionado and state.alt_pressionado and tecla.lower() == "m":
        gravar_confirmacao_manual()
        return

    if tecla and str(tecla).isdigit():
        indice = int(tecla)

        if state.ctrl_pressionado and state.win_pressionado:
            iniciar_captura_checkpoint(indice)
            return

        if state.ctrl_pressionado and state.shift_pressionado:
            iniciar_captura_campo_ocr(indice)
            return

        if state.ctrl_pressionado and state.alt_pressionado and state.gravando:
            gravar_esperar_ref(indice, TIMEOUT_CHECKPOINT)
            return

        if state.alt_pressionado and state.shift_pressionado and state.gravando:
            gravar_clicar_tela(indice, TIMEOUT_CHECKPOINT)
            return

        if state.win_pressionado and state.shift_pressionado and state.gravando:
            gravar_esperar_tela(indice, TIMEOUT_CHECKPOINT)
            return

    if not state.gravando or state.modo_captura is not None:
        return

    if tecla in state.teclas_pressionadas:
        return

    state.teclas_pressionadas.add(tecla)
    registrar_acao("key_down", tecla=tecla)

def on_key_release(key):
    if tecla_eh_ctrl(key):
        state.ctrl_pressionado = False
    if tecla_eh_alt(key):
        state.alt_pressionado = False
    if tecla_eh_shift(key):
        state.shift_pressionado = False
    if tecla_eh_win(key):
        state.win_pressionado = False

    if not state.gravando or state.modo_captura is not None:
        return

    if key in {
        keyboard.Key.f6, keyboard.Key.f7, keyboard.Key.f8, keyboard.Key.f9,
        keyboard.Key.f10, keyboard.Key.f11, keyboard.Key.f12,
        keyboard.Key.esc, keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
        keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r,
        keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r,
        keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r,
    }:
        return

    tecla = nome_tecla(key)
    if tecla and str(tecla).isdigit():
        return

    if tecla in state.teclas_pressionadas:
        state.teclas_pressionadas.remove(tecla)
    registrar_acao("key_up", tecla=tecla)
import math
import time
import threading
import state
from config import VELOCIDADE_EXECUCAO

parar_execucao_event = threading.Event()
pausa_execucao_event = threading.Event()
confirmar_execucao_event = threading.Event()

pausa_execucao_event.set()

def iniciar_tempo():
    state.ultimo_tempo = time.time()

def calcular_espera():
    agora = time.time()

    if state.ultimo_tempo is None:
        state.ultimo_tempo = agora
        return 0.0

    espera = agora - state.ultimo_tempo
    state.ultimo_tempo = agora
    return round(espera, 4)

def esperar_interrompivel(segundos: float, passo=0.02) -> bool:
    if segundos <= 0:
        return not parar_execucao_event.is_set()

    inicio = time.time()
    while time.time() - inicio < segundos:
        if parar_execucao_event.is_set():
            return False

        while not pausa_execucao_event.is_set():
            if parar_execucao_event.is_set():
                return False
            time.sleep(0.05)

        time.sleep(min(passo, segundos))
    return True

def esperar_confirmacao_manual() -> bool:
    confirmar_execucao_event.clear()

    while True:
        if parar_execucao_event.is_set():
            return False

        while not pausa_execucao_event.is_set():
            if parar_execucao_event.is_set():
                return False
            time.sleep(0.05)

        if confirmar_execucao_event.is_set():
            confirmar_execucao_event.clear()
            return True

        time.sleep(0.05)

def tempo_ajustado(segundos: float) -> float:
    if VELOCIDADE_EXECUCAO <= 0:
        return segundos
    return segundos / VELOCIDADE_EXECUCAO

def deve_parar() -> bool:
    return parar_execucao_event.is_set()

def indice_valido(indice: int) -> bool:
    return 0 <= indice <= 9

def calcular_regiao(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    x = min(x1, x2)
    y = min(y1, y2)
    largura = abs(x2 - x1)
    altura = abs(y2 - y1)
    return (x, y, largura, altura)

def calcular_centro_regiao(regiao):
    x, y, largura, altura = regiao
    return (x + largura // 2, y + altura // 2)

def distancia(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def deve_executar_macro_2(status: str, regra: str) -> bool:
    if regra == "nunca":
        return False
    if regra == "quando_finalizar":
        return status == "finalizada"
    if regra == "quando_parar":
        return status == "cancelada"
    if regra == "sempre":
        return status in {"finalizada", "cancelada", "erro"}
    return False

def nome_tecla_bruta(key) -> str:
    try:
        if hasattr(key, "char") and key.char is not None:
            return key.char
        return str(key).replace("Key.", "")
    except Exception:
        return str(key)

def normalizar_tecla(tecla: str) -> str:
    if tecla is None:
        return ""
    tecla = str(tecla).strip()
    mapa_numpad = {
        "<96>": "0", "<97>": "1", "<98>": "2", "<99>": "3", "<100>": "4",
        "<101>": "5", "<102>": "6", "<103>": "7", "<104>": "8", "<105>": "9",
    }
    return mapa_numpad.get(tecla, tecla)

def nome_tecla(key) -> str:
    return normalizar_tecla(nome_tecla_bruta(key))

def tecla_eh_ctrl(key) -> bool:
    try:
        from pynput import keyboard
        return key in {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r}
    except Exception:
        return False

def tecla_eh_alt(key) -> bool:
    try:
        from pynput import keyboard
        return key in {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r}
    except Exception:
        return False

def tecla_eh_shift(key) -> bool:
    try:
        from pynput import keyboard
        return key in {keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r}
    except Exception:
        return False

def tecla_eh_win(key) -> bool:
    try:
        from pynput import keyboard
        return key in {keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r}
    except Exception:
        return False

def nome_botao(button) -> str:
    return str(button).replace("Button.", "")

def centro_box(box):
    import pyautogui
    p = pyautogui.center(box)
    return (int(p.x), int(p.y))
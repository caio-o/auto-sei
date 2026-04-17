from config import ARQUIVO_MACRO_1

gravando = False
executando = False
acoes = []
ultimo_tempo = None
ultimo_movimento_gravado = 0.0
teclas_pressionadas = set()

botao_esquerdo_pressionado = False
botao_direito_pressionado = False
botao_meio_pressionado = False

ctrl_pressionado = False
alt_pressionado = False
shift_pressionado = False
win_pressionado = False

thread_execucao = None
status_ultima_execucao = None

modo_captura = None
indice_captura = None
inicio_selecao = None
fim_selecao = None

resultados_ocr_execucao = {}

ultimo_label_extraido = None
ultimo_valor_extraido = None

ARQUIVO_MACRO_ATUAL = ARQUIVO_MACRO_1
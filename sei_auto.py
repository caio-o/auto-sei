# Para gerar EXTRATO, MEMORIA/DETALHE e GRU.
import os         # Manuseio de arquivos
import pyautogui  # Interação com a interface de usuário
import subprocess # Interação com o PowerShell
import time       # Função sleep

__dir__ = 'docs/'
__dir_ps__ = 'docs'

# Dicionário de documentos gerados pelo TDCalc, no formato:
#     <nome gerado pelo TDCalc>: <nome descritivo>
__docs__ = {\
    'rptgrusimples.pdf':         'Guia de recolhimento.pdf',    \
    'rptmemoriacalculo.pdf':     'Extrato de prestações.pdf',   \
    'rptmemoriacalculop.pdf':    'Memória de cálculo.pdf',      \
    'rptmemoriacalculop99.pdf':  'Memória de cálculo.pdf'       \
}

# Dicionário de elementos da interface de usuário, no formato:
#     <nome descritivo>: <nome do arquivo>
__imgs__ = {\
    'janela firefox':         'imgs/firefox-pqn.png',           \
    'janela firefox aberta':  'imgs/firefox-2.png',             \
    'janela tdcalc':          'imgs/tdcalc-1.png',              \
    'janela tdcalc aberta':   'imgs/tdcalc-2.png',              \
    'janela arquivos':        'imgs/explorador-arquivos-1.png', \
    'janela arquivos aberta': 'imgs/explorador-arquivos-2.png', \
    'sei':                    'imgs/sei.png',                   \
    'sei aberto':             'imgs/aba-sei-2.png',             \
    'selecionado':            'imgs/selecionado.png',           \
    'arquivos':               'imgs/explorador-arquivos.png',   \
    'docs':                   'imgs/docs.png'                   \
}

# Renomeia os documentos gerados pelo TDCalc com nomes legíveis,
# para posterior inclusão no processo SEI.
def renomear():
    arquivos = os.listdir (__dir__)
    for arq in arquivos:
        if arq in __docs__:
            os.rename (__dir__ + arq, __dir__ + __docs__[arq])

def abrirDocs():
    subprocess.run ('explorer ' + __dir_ps__)

def buscarImgA(path: str):
    x, y, w, h = -1, -1, 0, 0
    if os.path.exists(path):
        try:
            x, y, w, h = pyautogui.locateOnScreen(path, 0.5)
        except pyautogui.ImageNotFoundException:
            print ('Imagem correspondente a \"' + path + '\" não encontrada!')
    else:
        print ('Arquivo \"' + path + '\" não encontrado!')
    return x,y,w,h

def buscarImg(s: str):
    x,y,w,h = -1,-1,-1,-1
    if s in __imgs__:
        x, y, w, h = buscarImgA(__imgs__[s])
    else:
        print ('Imagem \"' + s + '\" não existe no dicionário.')
    return x,y,w,h

def moverParaImg(s: str) -> bool:
    x,y,w,h = buscarImg (s)
    if x != -1:
        x = x + w/2
        y = y + h/2
        pyautogui.moveTo (x, y)
    else:
        return False
    return True

def clicarImg(s: str) -> bool:
    x,y,w,h = buscarImg (s)
    if x != -1:
        x = x + w/2
        y = y + h/2
        pyautogui.click (x, y)
    else:
        return False
    return True

"""
renomear()
clicarImg('janela firefox')
time.sleep(1)
clicarImg('sei')
time.sleep(1)
abrirDocs()
time.sleep(0.5)
clicarImg('arquivos')
time.sleep(0.1)
clicarImg('docs')

pyautogui.keyDown('ctrl')
time.sleep(0.3)
pyautogui.press('a')
pyautogui.keyUp('ctrl')

time.sleep(0.1)
if moverParaImg('selecionado'):
    pyautogui.dragTo(15, 300, 1, pyautogui.easeOutQuad, 'left')
"""



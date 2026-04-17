from pathlib import Path
import pytesseract

BASE_DIR = Path(__file__).resolve().parent

PASTA_IMAGENS = BASE_DIR / "imgs"
PASTA_IMAGENS.mkdir(parents=True, exist_ok=True)

ARQUIVO_MACRO_1 = BASE_DIR / "macro_principal.json"
ARQUIVO_MACRO_2 = BASE_DIR / "macro_secundaria.json"

ARQUIVO_CAMPOS_OCR = BASE_DIR / "campos_ocr.json"
ARQUIVO_CHECKPOINTS_REF = BASE_DIR / "checkpoints_ref.json"
ARQUIVO_RESULTADO = BASE_DIR / "resultado.json"

CAMINHO_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = CAMINHO_TESSERACT

MODO_TESTE = False
DEBUG = True
GRAVAR_MOVIMENTO_MOUSE = True

INTERVALO_MOVIMENTO = 0.05
DURACAO_MOVIMENTO = 0.08
VELOCIDADE_EXECUCAO = 3.0
TIMEOUT_CHECKPOINT = 20
CONFIANCA = 0.8
GRAYSCALE = True
USAR_OCR = True

# nunca | quando_finalizar | quando_parar | sempre
EXECUTAR_MACRO_2_QUANDO = "sempre"
DELAY_ENTRE_MACROS = 0.8

=======
# Auto Bot

Bot de automação visual com gravação de macro, captura de imagem, OCR e ações inteligentes.

## Recursos

- gravação e execução de macro
- captura de imagem de referência
- captura de campo OCR
- OCR por região
- esperar/clicar por referência
- esperar/clicar na tela
- ponto de confirmação manual
- colagem automática de:
  - data em formato BR
  - valor extraído por OCR
- execução encadeada de macro principal e secundária

## Arquivos

- `main.py` -> ponto de entrada
- `keyboard_mouse.py` -> hotkeys e listeners
- `executor.py` -> execução da macro
- `capture.py` -> captura de imagem e OCR
- `macro.py` -> gravação das ações
- `storage.py` -> leitura/escrita dos JSONs
- `ocr_tools.py` -> OCR
- `utils.py` -> utilidades
- `state.py` -> estado global
- `config.py` -> configurações

## Teclas
## Controle

 - F6 -> selecionar macro principal
 - F7 -> selecionar macro secundária
 - F8 -> iniciar/parar gravação
 - F9 -> executar
 - F10 -> apagar macro ativa
 - F11 -> pausar/retomar execução
 - F12 -> confirmar continuação manual
 - ESC -> cancelar execução/sair

## Capturas

 - Ctrl+Win+0..9 -> capturar imagem de referência
 - Ctrl+Shift+0..9 -> capturar campo OCR

## Macro

 - Ctrl+Alt+0..9 -> gravar esperar_ref
 - Alt+Shift+0..9 -> gravar clicar_tela
 - Win+Shift+0..9 -> gravar esperar_tela
 - Ctrl+Alt+M -> gravar confirmar

## Ações suportadas

 - esperar_ref
 - clicar_ref
 - esperar_tela
 - clicar_tela

## ocr

 - confirmar
 - colar_data_em_destino
 - colar_valor_de_origem_em_destino

## Observações

 - colar_valor_de_origem_em_destino usa uma origem OCR e um destino visual
 - colar_data_em_destino usa a data atual em formato dd/mm/aaaa
 - resultado.json guarda os dados extraídos no formato amigável

## JSONs usados

- `macro_principal.json`
- `macro_secundaria.json`
- `campos_ocr.json`
- `checkpoints_ref.json`
- `resultado.json`

## Instalação

```bash
pip install pyautogui pynput pillow pytesseract opencv-python pyperclip
>>>>>>> 975d078 (last_version)

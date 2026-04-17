from pynput import mouse, keyboard
from keyboard_mouse import on_move, on_click, on_scroll, on_key_press, on_key_release

def main():
    print("=" * 100)
    print("BOT AUTOMAÇÃO")
    print("=" * 100)
    print("F6  -> selecionar macro principal")
    print("F7  -> selecionar macro secundária")
    print("F8  -> iniciar/parar gravação")
    print("F9  -> executar")
    print("F10 -> apagar macro ativa")
    print("F11 -> pausar / continuar execução")
    print("F12 -> confirmar continuação manual")
    print("ESC -> parar execução / sair")
    print("")
    print("CAPTURAS")
    print("Ctrl+Win+0..9   -> capturar imagem de referência")
    print("Ctrl+Shift+0..9 -> capturar campo OCR")
    print("")
    print("AÇÕES DE MACRO")
    print("Ctrl+Alt+0..9   -> esperar_ref")
    print("Alt+Shift+0..9  -> clicar_tela")
    print("Win+Shift+0..9  -> esperar_tela")
    print("Ctrl+Alt+M      -> ponto de confirmação manual")
    print("")
    print("OBS:")
    print("- colar_data_em_destino e colar_valor_de_origem_em_destino")
    print("  podem ser inseridos manualmente no JSON da macro para teste")
    print("=" * 100)

    with mouse.Listener(
        on_move=on_move,
        on_click=on_click,
        on_scroll=on_scroll
    ) as listener_mouse, keyboard.Listener(
        on_press=on_key_press,
        on_release=on_key_release
    ) as listener_teclado:
        listener_teclado.join()

if __name__ == "__main__":
    main()
### Dependências:
* Python 3
  - Bibliotecas: OpenCV, Pillow, PyAutoGUI
* Acesso ao PowerShell
* Mouse e Tela xD
* Windwos 10 ou 11 (decerto só está funcionando em Windows 10)

### Estado atual:
O programa atualmente opera completamente pela **interface de usuário**. 
Portanto, para acessar uma janela, ele procura o ícone do programa correspondente, 
e depois clica sobre esse ícone. O problema é que os ícones podem variar levemente
conforme preferências e versões do Sistema Operacional.

Por isso precisamos substituir o acesso à interface gráfica por um acesso à API do windows.

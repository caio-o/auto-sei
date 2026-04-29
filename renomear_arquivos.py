from pathlib import Path
import os
import re

# ==================================
# CONFIGURAÇÃO
# ==================================

PASTA = r"C:\Users\Genaba\Documents\000 Sei\script python\executavel\doc"

MAPA_RENOMEAR = {
    "rptmemoriacalculo.pdf": "Extrato de prestações.pdf",
    "rptgrusimples.pdf": "Guia de Recolhimento da União - GRU.pdf",
    "rptmemoriacalculop.pdf": "Memória de cálculo.pdf",
    "rptmemoriacalculop99.pdf": "Memória de cálculo.pdf",
}

NOME_WORD = "Analise técnica"


# ==================================
# FUNÇÕES
# ==================================

def normalizar_nome(nome: str) -> str:
    nome = (nome or "").strip().lower()
    nome = re.sub(r"\s+", " ", nome)
    return nome


def apagar_se_existir(destino: Path):
    if destino.exists():
        try:
            os.remove(destino)
        except PermissionError:
            print(f"Não foi possível apagar porque está aberto: {destino.name}")
            raise


def substituir_arquivo(origem: Path, destino: Path):
    apagar_se_existir(destino)
    origem.rename(destino)


def listar_arquivos(pasta: Path):
    arquivos = [arq for arq in pasta.iterdir() if arq.is_file()]
    print("\nArquivos encontrados na pasta:")
    if not arquivos:
        print(" - nenhum arquivo")
    for arq in arquivos:
        print(f" - {arq.name}")
    return arquivos


def renomear_por_nomes(pasta: Path, mapa: dict):
    arquivos = [arq for arq in pasta.iterdir() if arq.is_file()]
    encontrou_algum = False

    mapa_normalizado = {
        normalizar_nome(nome_antigo): nome_novo
        for nome_antigo, nome_novo in mapa.items()
    }

    for arquivo in arquivos:
        nome_atual = normalizar_nome(arquivo.name)

        if nome_atual in mapa_normalizado:
            nome_novo = mapa_normalizado[nome_atual]
            destino = pasta / nome_novo

            print(f"Renomeando conhecido: {arquivo.name} -> {nome_novo}")
            substituir_arquivo(arquivo, destino)
            encontrou_algum = True

    if not encontrou_algum:
        print("\nNenhum arquivo da lista foi encontrado para renomear.")


def renomear_word_para_analise_tecnica(pasta: Path):
    arquivos = [arq for arq in pasta.iterdir() if arq.is_file()]
    encontrou_word = False

    for arquivo in arquivos:
        sufixo = arquivo.suffix.lower()

        if sufixo not in [".doc", ".docx"]:
            continue

        novo_nome = f"{NOME_WORD}{arquivo.suffix}"
        destino = pasta / novo_nome

        print(f"Renomeando Word: {arquivo.name} -> {novo_nome}")
        substituir_arquivo(arquivo, destino)
        encontrou_word = True
        break

    if not encontrou_word:
        print("Nenhum arquivo Word (.doc/.docx) encontrado.")


def main():
    pasta = Path(PASTA)

    if not pasta.exists():
        print("Pasta não encontrada:")
        print(PASTA)
        input("Pressione Enter para sair...")
        return

    listar_arquivos(pasta)
    renomear_por_nomes(pasta, MAPA_RENOMEAR)
    renomear_word_para_analise_tecnica(pasta)

    print("\nPronto.")
    input("Pressione Enter para sair...")


if __name__ == "__main__":
    main()
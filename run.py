#!/usr/bin/env python3
"""
Modo "tudo em um": builda o frontend (sempre, pra nunca servir uma versão
desatualizada), sobe o backend servindo tanto a API quanto o frontend
buildado, e abre o navegador — tudo em http://localhost:8000, uma porta só.

Uso:
    python run.py

Esse é o script pensado para rodar direto pelo botão Run/Play do VS Code
(veja .vscode/launch.json) ou por um duplo-clique / atalho no terminal.

Para desenvolvimento com hot-reload do frontend (mudanças refletindo na hora,
sem esperar o build a cada alteração), prefira o modo separado:
`python start.py` (backend) + `npm run dev` dentro de frontend/ (frontend),
em dois terminais.
"""
import subprocess
import sys
import os
import time
import webbrowser
import socket

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
FRONTEND_DIST = os.path.join(FRONTEND_DIR, "dist")
PORT = 8000


def run(cmd, cwd=None):
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True)


def ensure_frontend_build():
    node_modules = os.path.join(FRONTEND_DIR, "node_modules")
    npm = "npm.cmd" if os.name == "nt" else "npm"

    if not os.path.isdir(node_modules):
        print("Dependências do frontend não encontradas — rodando 'npm install'...")
        run([npm, "install"], cwd=FRONTEND_DIR)

    # Builda sempre (não só na primeira vez): um build antigo em frontend/dist
    # ficaria servindo código desatualizado silenciosamente sempre que o
    # projeto for atualizado, o que é pior do que pagar alguns segundos a
    # mais de build em toda inicialização.
    print("Buildando o frontend (garante que está servindo a versão mais recente)...")
    run([npm, "run", "build"], cwd=FRONTEND_DIR)


def is_ollama_running(host="localhost", port=11434) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def try_start_ollama():
    if is_ollama_running():
        print("Ollama já está rodando — a análise por IA vai funcionar.")
        return
    try:
        print("Ollama não parece estar rodando. Tentando iniciar em segundo plano...")
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2)
        if is_ollama_running():
            print("Ollama iniciado com sucesso.")
        else:
            print("Não deu pra confirmar se o Ollama subiu. A análise por IA pode não funcionar até você iniciá-lo manualmente.")
    except FileNotFoundError:
        print(
            "Ollama não está instalado (ou não está no PATH). O app funciona normalmente, "
            "mas a análise por IA vai ficar indisponível até você instalar: https://ollama.com/download"
        )


def open_browser_when_ready():
    def _wait_and_open():
        for _ in range(30):
            try:
                with socket.create_connection(("localhost", PORT), timeout=1):
                    webbrowser.open(f"http://localhost:{PORT}")
                    return
            except OSError:
                time.sleep(0.5)

    import threading
    threading.Thread(target=_wait_and_open, daemon=True).start()


def main():
    ensure_frontend_build()
    try_start_ollama()

    print(f"\nSubindo tudo em http://localhost:{PORT} ...")
    print(f"Docs interativas da API em http://localhost:{PORT}/docs\n")

    open_browser_when_ready()

    subprocess.run(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORT)],
        cwd=BACKEND_DIR,
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Script de inicialização do backend. Funciona igual em Linux e Windows.

Uso:
    python start.py

O frontend é iniciado separadamente com `npm run dev` dentro da pasta frontend/
(em desenvolvimento), enquanto esse script sobe apenas a API.
"""
import subprocess
import sys
import os

BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")

def main():
    print("Subindo a API em http://localhost:8000 ...")
    print("Docs interativas em http://localhost:8000/docs")
    subprocess.run(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
        cwd=BACKEND_DIR,
    )

if __name__ == "__main__":
    main()

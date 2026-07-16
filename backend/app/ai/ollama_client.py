import os
import requests
from typing import Optional

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

SYSTEM_PROMPT = """Você é um assistente financeiro especializado em quitação de dívidas.
Você SEMPRE recebe números já calculados por um motor determinístico (nunca invente
ou recalcule valores, apenas use exatamente os números fornecidos).

Sua tarefa é:
1. Explicar de forma clara e acolhedora (sem jargão excessivo) o que o plano de
   quitação significa na prática para a pessoa.
2. Destacar pontos de atenção, especialmente dívidas em "armadilha de juros"
   (quando o pagamento mínimo não cobre nem os juros do mês).
3. Dar 2-3 recomendações práticas e realistas, considerando a renda informada.
4. Ser direto e objetivo.

Responda sempre em português do Brasil."""


class OllamaUnavailableError(Exception):
    pass


def is_ollama_available() -> bool:
    try:
        resp = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def generate_analysis(context: str, model: Optional[str] = None) -> str:
    model_name = model or DEFAULT_MODEL

    if not is_ollama_available():
        raise OllamaUnavailableError(
            "Não foi possível conectar ao Ollama em "
            f"{OLLAMA_HOST}. Verifique se ele está instalado e rodando "
            "(`ollama serve` ou o app do Ollama em segundo plano)."
        )

    payload = {
        "model": model_name,
        "system": SYSTEM_PROMPT,
        "prompt": context,
        "stream": False,
        "options": {"temperature": 0.4},
    }

    try:
        resp = requests.post(f"{OLLAMA_HOST}/api/generate", json=payload, timeout=120)
        if resp.status_code != 200:
            try:
                detail = resp.json().get("error", resp.text)
            except ValueError:
                detail = resp.text
            raise OllamaUnavailableError(
                f"O Ollama respondeu com erro ao usar o modelo '{model_name}': {detail}\n"
                f"Rode `ollama list` no terminal pra ver os modelos disponíveis e ajuste "
                f"OLLAMA_MODEL no arquivo backend/.env."
            )
        data = resp.json()
        return data.get("response", "").strip()
    except requests.RequestException as e:
        raise OllamaUnavailableError(f"Erro ao chamar o Ollama: {e}") from e


def build_context(income_summary: str, plan_summary: str) -> str:
    return f"""Renda mensal disponível informada pelo usuário:
{income_summary}

Resultado do plano de quitação calculado (dados exatos, não recalcule):
{plan_summary}

Com base nesses dados, gere a análise seguindo as instruções do sistema."""
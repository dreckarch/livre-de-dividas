# 💰 Livre de Dívidas

Software local (Linux/Windows) de gestão financeira focado em **quitação de dívidas**, com:

- Cadastro de renda (salário, VT, VA, comissões etc.)
- Cadastro de dívidas (saldo, juros, pagamento mínimo)
- Motor de cálculo determinístico com as estratégias **Avalanche** (menor juros total) e **Snowball** (motivacional)
- Análise em linguagem natural gerada por **IA local e gratuita** (via [Ollama](https://ollama.com)) — os números nunca são calculados pela IA, apenas explicados por ela

Todos os dados ficam no seu computador (SQLite local). Nada é enviado para a nuvem.

## Arquitetura

```
backend/    API em FastAPI (Python) + SQLite + motor de cálculo
frontend/   Interface web (React + Vite), roda localmente no navegador
start.py    Sobe o backend com um único comando
```

A camada de IA **nunca faz contas** — ela recebe o resultado já calculado pelo motor
determinístico (`backend/app/engine/debt_engine.py`) e apenas o traduz em explicação e
recomendações. Isso evita erros de matemática comuns em modelos de linguagem.

## Pré-requisitos

- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)
- [Ollama](https://ollama.com/download) (para a análise por IA — opcional para usar o resto do app)

## Instalação

```bash
git clone dreckarch/livre-de-dividas
cd livre-de-dividas

# Backend
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..

# Frontend (instala as dependências; o build acontece sozinho no primeiro run)
cd frontend
npm install
cd ..

# IA local (opcional, mas recomendado)
ollama pull llama3.2
```

## Rodando — modo simples (recomendado)

Um único comando builda o frontend (se preciso), sobe o backend, tenta iniciar
o Ollama, e abre o navegador automaticamente — tudo em **http://localhost:8000**:

```bash
python run.py
```

**No VS Code**: abra a pasta do projeto, vá em *Run and Debug* (▶) e escolha
"▶ Livre de Dívidas (tudo em um)" — ou simplesmente aperte **F5**. Isso já
executa o `run.py` pra você (configuração em `.vscode/launch.json`). Só é
necessário ter a extensão *Python* instalada no VS Code.

> `run.py` sempre reconstrói o frontend a cada execução (leva só alguns
> segundos), justamente pra nunca correr o risco de servir uma versão
> desatualizada da interface — inclusive depois de atualizar o projeto.

## Rodando — modo desenvolvimento (hot-reload do frontend)

Útil se você for mexer bastante na interface e quiser ver as mudanças na hora,
sem precisar buildar a cada alteração. Requer dois terminais:

```bash
# Terminal 1 — backend (API em http://localhost:8000)
python start.py

# Terminal 2 — frontend com hot-reload (http://localhost:5173)
cd frontend
npm run dev
```

Nesse modo, abra **http://localhost:5173** (não a porta 8000).

## Configurando o modelo do Ollama

Por padrão o backend tenta usar o modelo `llama3.2`. Se você baixou outro modelo,
copie o arquivo de exemplo e ajuste:

```bash
cd backend
cp .env.example .env
# edite .env e coloque o nome exato do modelo (confira com `ollama list`)
```

## Resolvendo problemas com a análise por IA

Se o botão "Pedir análise da IA" não parecer fazer nada:

1. **Espere um pouco** — a primeira consulta depois que o Ollama inicia pode levar
   até 1 minuto, porque o modelo precisa carregar na memória. As próximas são bem
   mais rápidas.
2. **Confira o nome do modelo** — rode `ollama list` no terminal e compare com o
   que está em `backend/.env` (`OLLAMA_MODEL`). Se você rodou `ollama run llama3.2`
   mas o `.env` diz `llama3.1` (ou não existe), a chamada falha.
3. **Abra o DevTools do navegador** (F12 → aba Network), clique no botão de novo, e
   veja a requisição para `/api/ai/analyze`. Se ela retornar erro 503, a mensagem
   de detalhe já traz o motivo exato reportado pelo Ollama.
4. **Teste o Ollama isoladamente**: `curl http://localhost:11434/api/tags` deve
   listar os modelos instalados. Se der erro de conexão, o Ollama não está
   acessível nessa porta.

## Estratégias de quitação

- **Avalanche**: prioriza a dívida com maior taxa de juros. Matematicamente é sempre a
  que menos juros totais gera.
- **Snowball**: prioriza a dívida com menor saldo. Gera vitórias mais rápidas, o que
  ajuda psicologicamente a manter a disciplina.

O app também detecta automaticamente dívidas em **"armadilha de juros"** — quando o
pagamento mínimo nem cobre os juros do mês, ou seja, o saldo cresce mesmo pagando em dia.

## Categorias de dívida

O motor de cálculo trata três categorias de forma diferente — cada uma com sua própria
mecânica financeira, não é tudo "cartão de crédito" disfarçado:

- **Rotativo** (cartão de crédito, cheque especial): saldo com juros compostos mensais.
  Entra na fila do Avalanche/Snowball e recebe o dinheiro extra disponível.
- **Parcelado Fixo** (financiamento, empréstimo pessoal, consignado): parcela já
  definida em contrato. É deduzida automaticamente da renda todo mês — não compete
  no Avalanche/Snowball, é uma despesa obrigatória. Parcelas em atraso viram
  **prioridade máxima** de quitação, à frente até das dívidas rotativas.
- **Acordo Ativo**: nasce quando você usa o simulador de acordo (ver abaixo) pra
  converter uma dívida rotativa numa parcela fixa negociada com o credor.

## Fluxo de caixa por retenção

Em vez de informar "quanto a mais você consegue pagar", você informa **quanto quer
reter** por mês (despesas fixas, reserva de emergência etc.). O motor calcula:

```
disponível para dívidas = renda mensal − valor retido − parcelas fixas obrigatórias
```

Esse disponível paga primeiro qualquer atraso de parcelas vencidas, depois vai pro
Avalanche/Snowball das dívidas rotativas.

## Simulador de Acordo / Parcelamento

Na página **Plano de Quitação**, é possível comparar duas rotas para uma dívida
rotativa específica:

- **À vista**: a dívida continua rotativa, amortizada normalmente pela estratégia
  escolhida.
- **Acordo**: a dívida sai da fila e vira uma parcela fixa (ex: 12x de R$ 450) que
  passa a ser deduzida automaticamente da renda, como um financiamento.

O motor simula o **plano inteiro** nos dois cenários (não só a dívida isolada, já que
mudar uma dívida de categoria afeta o fluxo de caixa disponível para todas as outras)
e aponta qual opção é mais barata e qual é mais rápida — de forma determinística, sem
a IA "achar" nada. A IA entra depois só pra explicar o resultado em português claro.

## Testando o motor de cálculo

```bash
cd backend
pytest -v
```

## Atualizando de uma versão anterior

Se você já tinha rodado uma versão anterior deste projeto, o schema do banco mudou
(novas colunas para categoria e parcelamento). Apague `backend/data/livre_de_dividas.db`
antes de rodar de novo — ele é recriado automaticamente, e por padrão nunca é
versionado no Git (veja `.gitignore`).

Ao baixar uma versão nova do projeto, prefira **substituir a pasta inteira**
em vez de extrair os arquivos novos por cima da pasta antiga — assim você evita
misturar código novo com uma pasta `frontend/node_modules` ou configurações
antigas por engano. Isso não afeta mais o build do frontend em si (`run.py`
sempre reconstrói do zero a cada execução), mas ainda é a forma mais segura
de garantir que nada da versão anterior ficou pra trás.

## Roadmap / próximos passos sugeridos

- [ ] Autenticação local simples (multiusuário na mesma máquina)
- [ ] Gráficos de evolução do saldo devedor ao longo do tempo
- [ ] Exportação do plano em PDF
- [ ] Editar parcelas pagas/em atraso diretamente pela interface (hoje é só na criação)
- [ ] Empacotamento com Tauri/Electron para gerar um instalador único

## Licença

Este projeto está sob a licença MIT — veja o arquivo [LICENSE](LICENSE).

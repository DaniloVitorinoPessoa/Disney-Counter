# ✨ Disney Counter

Rastreador de gastos para a viagem à Disney — feito para dois casais
(**Danilo & Rafaella** e **Pedro & Giovanna**), cada um com seus próprios
dados, metas e desejos.

Web app em **Python + Flask**, com **SQLite** localmente e **PostgreSQL**
(Neon) em produção. Front-end em HTML/CSS/JS puro, sem frameworks.

---

## 🎯 Funcionalidades

### Gastos
- Cadastro de gastos com: **descrição, valor, moeda (R$/US$), quem pagou,
  de quem é, data, categoria e tipo** (Pré-viagem / Na viagem).
- **Cotação travada por gasto:** cada compra em dólar guarda o câmbio do dia
  em que foi feita (US$100 a 5,50 ≠ US$100 a 5,20). O total reflete o custo real.
- Botão **"Ver totais em R$ / US$"** — converte a exibição usando a cotação
  travada de cada gasto (não recalcula nada).
- **Resumo:** total geral, total Pré-viagem, total Na viagem e total por pessoa.
- Categorias com emoji (✈️ Passagem, 🛂 Visto, 🎢 Parque, 🍔 Alimentação,
  🛍️ Comprinhas, etc.).
- Excluir gasto com confirmação.

### 🤝 Acerto do casal
- Cada gasto tem **"de quem é"**: de uma pessoa ou **meio a meio**.
- O sistema calcula automaticamente **quem deve quanto pro outro**, mostrando
  uma frase só (ex.: *"Danilo deve R$ 210 para Rafaella"*). Respeita a moeda
  escolhida e a cotação travada.

### 🎯 Cofrinho (metas de grana)
- **Meta por pessoa** + um **total combinado** dos dois.
- Registro de **aportes** (quanto cada um guardou), com barra de progresso,
  percentual e *"faltam R$ X — guardar ~R$ Y por dia até a viagem"*.

### 🛍️ Lista de desejos
- Wishlist de produtos (nome, preço estimado, moeda, de quem é).
- Botão **"Comprei"** pré-preenche o formulário de gasto e, ao confirmar,
  remove o item da lista (vira gasto de verdade).

### ⏳ Contagem regressiva
- Conta dias/horas/min/seg até **25/12/2026** (chegada), com frases mágicas.
  Trata os períodos durante e depois da viagem.

### 🎬 Temas e visual
- 7 temas de filme (Mágico, Frozen, Enrolados, Carros, Rei Leão, Pequena
  Sereia, Toy Story) — cada um troca cores, cenário de fundo (desenhos SVG
  autorais), efeito de ambiente e **cursor temático animado**.
- Easter eggs (fogos, poeira mágica, estrela cadente, neve/lanternas, etc.).

### 🔐 Acesso e isolamento
- **Login por nome** + senha (4 usuários). Senhas só via variáveis de ambiente.
- **Separação por casal (grupo):** cada casal só enxerga e mexe nos próprios
  gastos, metas e desejos — nunca se misturam, mesmo no mesmo banco.

---

## 🗂️ Estrutura

```
disney-gastos/
  app.py              # backend Flask (rotas + acesso ao banco)
  requirements.txt    # dependências
  Procfile            # comando de start em produção (gunicorn)
  render.yaml         # configuração de deploy no Render
  .env.example        # modelo das variáveis de ambiente
  .gitignore          # ignora .env, *.db, venv, __pycache__
  start.bat           # atalho para rodar no Windows
  templates/
    login.html        # tela de login
    index.html        # app (gastos, metas, desejos)
  static/
    temas.js          # biblioteca de desenhos SVG dos temas
```

## 🛠️ Variáveis de ambiente

| Variável | Para que serve |
|---|---|
| `DANILO_SENHA`, `RAFAELLA_SENHA` | senhas do casal 1 |
| `PEDRO_SENHA`, `GIOVANNA_SENHA` | senhas do casal 2 |
| `DATABASE_URL` | string do Postgres (Neon). Sem ela, usa SQLite local |
| `SECRET_KEY` | chave de assinatura das sessões de login |

> As senhas e o `DATABASE_URL` **nunca** ficam no código — só nas variáveis
> de ambiente (no `.env` local, ignorado pelo Git, ou no painel do Render).

## 💻 Rodando localmente (Windows)

1. Copie `.env.example` para `.env` e preencha as senhas.
2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
3. Rode:
   ```
   python app.py
   ```
   (ou dê dois cliques em `start.bat`)
4. Acesse `http://localhost:5000`.

Sem `DATABASE_URL`, os dados ficam num arquivo SQLite local (`disney_gastos.db`).

## ☁️ Deploy (Render + Neon)

1. **Neon:** crie um banco PostgreSQL grátis e copie a connection string
   (use o host com `-pooler`).
2. **Render:** crie um *Web Service* a partir deste repositório (ele lê o
   `render.yaml`). Em **Environment**, preencha `DATABASE_URL` e as 4 senhas
   (o `SECRET_KEY` o Render gera).
3. O app cria as tabelas automaticamente no primeiro acesso.

> Plano grátis do Render hiberna após ~15 min sem uso — o primeiro acesso
> depois disso demora ~30-50s (cold start) e depois fica rápido.

## 🧱 Stack

- **Backend:** Python, Flask, gunicorn
- **Banco:** SQLite (local) / PostgreSQL via `psycopg` (produção)
- **Front-end:** HTML, CSS e JavaScript puro
- **Hospedagem:** Render · **Banco:** Neon

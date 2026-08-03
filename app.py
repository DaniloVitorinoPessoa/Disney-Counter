import os
import json
import time
import sqlite3
import urllib.request
import urllib.error
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    session,
    redirect,
    url_for,
)
from werkzeug.security import generate_password_hash, check_password_hash

# Carrega variaveis de um arquivo .env local (se existir). Em producao
# as variaveis vem do painel do Render. O .env NAO vai pro Git.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")

# Em producao (nuvem) usa Postgres via DATABASE_URL; localmente usa SQLite.
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_PG = bool(DATABASE_URL)
DB_PATH = os.environ.get("DISNEY_DB_PATH", "disney_gastos.db")
PH = "%s" if USE_PG else "?"  # placeholder de parametro do driver

# Busca da aba "Onde comprar" (100% gratis, sem cartao):
#  1) TAVILY faz a busca real na web e devolve resultados com link (free tier
#     sem cartao - crie a chave em tavily.com). E o que garante confiabilidade.
#  2) GEMINI (so texto, gratis) cura e explica os resultados em portugues.
#     Opcional: sem ele, a aba mostra os resultados crus do Tavily.
# As chaves vem SO de variaveis de ambiente (nada no codigo).
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# Modelo de TEXTO do Gemini (nao usa mais o grounding pago; quem busca e o
# Tavily). O "lite" e gratis, leve e menos sujeito a picos de demanda (503).
# O alias "-latest" evita 404 quando uma versao e aposentada.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")

if USE_PG:
    import psycopg
    from psycopg.rows import dict_row

# Grupos (casais). Cada casal so enxerga os proprios gastos.
GRUPOS = {
    "casal1": {"nome": "Danilo & Rafaella", "membros": ["Danilo", "Rafaella"]},
    "casal2": {"nome": "Pedro & Giovanna", "membros": ["Pedro", "Giovanna"]},
}

# Usuarios: nome (minusculo) -> {nome canonico, grupo, hash da senha}.
# Senhas vem SO de variaveis de ambiente (nada de senha no codigo).
# Localmente, defina-as no arquivo .env (que NAO vai pro Git).
USUARIOS = {}
for _nome, _grupo, _var in (
    ("Danilo", "casal1", "DANILO_SENHA"),
    ("Rafaella", "casal1", "RAFAELLA_SENHA"),
    ("Pedro", "casal2", "PEDRO_SENHA"),
    ("Giovanna", "casal2", "GIOVANNA_SENHA"),
):
    _senha = os.environ.get(_var)
    if _senha:
        USUARIOS[_nome.lower()] = {
            "nome": _nome,
            "grupo": _grupo,
            "hash": generate_password_hash(_senha),
        }


def get_db():
    if USE_PG:
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    id_col = "SERIAL PRIMARY KEY" if USE_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"
    valor_col = "DOUBLE PRECISION" if USE_PG else "REAL"
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS gastos (
            id {id_col},
            descricao TEXT NOT NULL,
            valor {valor_col} NOT NULL,
            categoria TEXT NOT NULL,
            quem TEXT NOT NULL,
            data TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Viagem',
            moeda TEXT NOT NULL DEFAULT 'USD',
            cotacao {valor_col} NOT NULL DEFAULT 1,
            grupo TEXT NOT NULL DEFAULT 'casal1',
            responsavel TEXT NOT NULL DEFAULT '',
            criado_em TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS config (chave TEXT PRIMARY KEY, valor TEXT)"
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS aportes (
            id {id_col},
            valor {valor_col} NOT NULL,
            quem TEXT NOT NULL,
            data TEXT NOT NULL,
            grupo TEXT NOT NULL DEFAULT 'casal1',
            criado_em TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS desejos (
            id {id_col},
            nome TEXT NOT NULL,
            valor {valor_col} NOT NULL DEFAULT 0,
            moeda TEXT NOT NULL DEFAULT 'USD',
            quem TEXT NOT NULL DEFAULT '',
            grupo TEXT NOT NULL DEFAULT 'casal1',
            criado_em TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS lugares (
            id {id_col},
            nome TEXT NOT NULL,
            descricao TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL DEFAULT '',
            busca TEXT NOT NULL DEFAULT '',
            quem TEXT NOT NULL DEFAULT '',
            grupo TEXT NOT NULL DEFAULT 'casal1',
            criado_em TEXT NOT NULL
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS essenciais (
            id {id_col},
            nome TEXT NOT NULL,
            valor {valor_col} NOT NULL DEFAULT 0,
            moeda TEXT NOT NULL DEFAULT 'USD',
            obs TEXT NOT NULL DEFAULT '',
            comprado INTEGER NOT NULL DEFAULT 0,
            grupo TEXT NOT NULL DEFAULT 'casal1',
            criado_em TEXT NOT NULL
        )
        """
    )
    # Migracoes para bancos criados antes destes campos.
    if USE_PG:
        conn.execute("ALTER TABLE gastos ADD COLUMN IF NOT EXISTS tipo TEXT NOT NULL DEFAULT 'Viagem'")
        conn.execute("ALTER TABLE gastos ADD COLUMN IF NOT EXISTS moeda TEXT NOT NULL DEFAULT 'USD'")
        conn.execute(f"ALTER TABLE gastos ADD COLUMN IF NOT EXISTS cotacao {valor_col} NOT NULL DEFAULT 1")
        conn.execute("ALTER TABLE gastos ADD COLUMN IF NOT EXISTS grupo TEXT NOT NULL DEFAULT 'casal1'")
        conn.execute("ALTER TABLE gastos ADD COLUMN IF NOT EXISTS responsavel TEXT NOT NULL DEFAULT ''")
    else:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(gastos)").fetchall()]
        if "tipo" not in cols:
            conn.execute("ALTER TABLE gastos ADD COLUMN tipo TEXT NOT NULL DEFAULT 'Viagem'")
        if "moeda" not in cols:
            conn.execute("ALTER TABLE gastos ADD COLUMN moeda TEXT NOT NULL DEFAULT 'USD'")
        if "cotacao" not in cols:
            conn.execute(f"ALTER TABLE gastos ADD COLUMN cotacao {valor_col} NOT NULL DEFAULT 1")
        if "grupo" not in cols:
            conn.execute("ALTER TABLE gastos ADD COLUMN grupo TEXT NOT NULL DEFAULT 'casal1'")
        if "responsavel" not in cols:
            conn.execute("ALTER TABLE gastos ADD COLUMN responsavel TEXT NOT NULL DEFAULT ''")
    conn.commit()
    conn.close()


def get_cotacao(conn, grupo):
    row = conn.execute(
        f"SELECT valor FROM config WHERE chave = {PH}", (f"cotacao:{grupo}",)
    ).fetchone()
    try:
        return float(row["valor"]) if row else 5.50
    except (TypeError, ValueError):
        return 5.50


def converter(valor, moeda, exibir, cotacao):
    """Converte usando a cotacao TRAVADA do proprio gasto (BRL por 1 USD)."""
    moeda = moeda or "USD"
    cot = cotacao or 1
    if moeda == exibir:
        return valor
    if exibir == "BRL":
        return valor * cot           # gasto em USD -> BRL (custo real do dia)
    return valor / cot               # gasto em BRL -> USD


def _tavily_buscar(pergunta):
    """Busca real na web via Tavily (free tier, sem cartao). Devolve uma lista
    de resultados [{titulo, url, conteudo}] - a base confiavel da resposta."""
    if not TAVILY_API_KEY:
        raise RuntimeError("Busca nao configurada.")
    body = json.dumps(
        {
            "query": pergunta,
            "search_depth": "basic",
            "max_results": 8,
            "topic": "general",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + TAVILY_API_KEY,
        },
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    resultados = []
    for r in data.get("results", []) or []:
        url = (r.get("url") or "").strip()
        if not url.lower().startswith("http"):
            continue
        resultados.append(
            {
                "titulo": (r.get("title") or "").strip(),
                "url": url,
                "conteudo": (r.get("content") or "").strip(),
            }
        )
    return resultados


def _gemini_texto(prompt, timeout=45, tentativas=3):
    """Chamada simples de texto ao Gemini (gratis, sem grounding). Devolve o
    texto gerado, ou '' se a IA nao estiver configurada / falhar. Faz retry com
    backoff em erros transitorios (503 sobrecarga, 429 rate, 500)."""
    if not GEMINI_API_KEY:
        return ""
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
    )
    for i in range(tentativas):
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            cand = (data.get("candidates") or [{}])[0]
            partes = cand.get("content", {}).get("parts", []) or []
            return "".join(p.get("text", "") for p in partes)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and i < tentativas - 1:
                time.sleep(1.5 * (i + 1))  # 1.5s, 3s...
                continue
            return ""
        except Exception:
            return ""
    return ""


def _parse_json_obj(texto):
    """Extrai um objeto JSON do texto da IA (tolera cercas ``` e lixo em volta)."""
    if not texto:
        return {}
    t = texto.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t[:4].lower() == "json":
            t = t[4:]
    ini, fim = t.find("{"), t.rfind("}")
    if ini != -1 and fim != -1 and fim > ini:
        t = t[ini : fim + 1]
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else {}
    except (ValueError, TypeError):
        return {}


def _limpar_lugares(lista, resultados):
    """Normaliza a lista de lugares da IA. Se houver resultados do Tavily, so
    aceita URLs que vieram deles (anti-alucinacao); senao aceita http."""
    canon = {(r["url"] or "").rstrip("/").lower(): r["url"] for r in resultados}
    limpos = []
    for l in lista or []:
        if not isinstance(l, dict):
            continue
        nome = (l.get("nome") or "").strip()
        if not nome:
            continue
        url = (l.get("url") or "").strip()
        if resultados:
            real = canon.get(url.rstrip("/").lower())
            if not real:
                continue  # url inventada -> descarta
            url = real
        elif not url.lower().startswith("http"):
            url = ""
        limpos.append(
            {
                "nome": nome[:200],
                "descricao": (l.get("descricao") or "").strip()[:500],
                "url": url[:500],
            }
        )
    return limpos[:8]


def _historico_texto(mensagens):
    """Formata a conversa (lista de {papel, texto}) como texto para o prompt."""
    linhas = []
    for m in mensagens:
        quem = "Usuario" if m.get("papel") == "user" else "Assistente"
        linhas.append(f"{quem}: {(m.get('texto') or '').strip()}")
    return "\n".join(linhas)


def _query_de_busca(mensagens):
    """Deriva uma consulta de busca autossuficiente a partir da conversa (para
    lidar com follow-ups tipo 'e mais barato?'). Na 1a mensagem, busca direto."""
    ultima = next(
        (m.get("texto", "").strip() for m in reversed(mensagens) if m.get("papel") == "user"),
        "",
    )
    if not GEMINI_API_KEY or len(mensagens) <= 1:
        return ultima
    prompt = (
        "Dada a conversa abaixo, escreva UMA consulta de busca na web, curta e "
        "autossuficiente, no idioma do usuario, que capture o que ele procura "
        "AGORA. Responda somente com a consulta, sem aspas.\n\n"
        + _historico_texto(mensagens)
    )
    q = _gemini_texto(prompt).strip()
    q = q.splitlines()[0].strip().strip('"') if q else ""
    return (q or ultima)[:300]


def _gemini_conversa(mensagens, resultados):
    """Resposta conversacional do Gemini com base na conversa + resultados reais
    do Tavily. Devolve (resposta_texto, lugares) ou ('', None) se a IA falhar."""
    if not GEMINI_API_KEY or not resultados:
        return "", None
    contexto = "\n\n".join(
        f"[{i}] {r['titulo']}\nURL: {r['url']}\n{r['conteudo'][:500]}"
        for i, r in enumerate(resultados)
    )
    instrucao = (
        "Voce e um assistente de compras simpatico e direto, conversando em "
        "portugues. Com base na conversa e nos resultados de busca REAIS abaixo, "
        "responda ao usuario e sugira lugares/lojas confiaveis e com bom preco. "
        "Responda SOMENTE com um JSON valido, sem markdown, no formato: "
        '{"resposta":"uma ou duas frases conversando","lugares":[{"nome":"...",'
        '"descricao":"por que e confiavel e a faixa de preco","url":"uma das URLs '
        'dos resultados"}]}. Use SOMENTE URLs que aparecem nos resultados. Sugira '
        "de 2 a 6 lugares. Se o usuario apenas agradecer ou conversar sem pedir "
        'compra, deixe "lugares" vazio e apenas responda gentilmente.\n\n'
        f"Conversa:\n{_historico_texto(mensagens)}\n\nResultados:\n{contexto}"
    )
    obj = _parse_json_obj(_gemini_texto(instrucao))
    if not obj:
        return "", None
    resposta = (obj.get("resposta") or "").strip()[:600]
    lugares = _limpar_lugares(obj.get("lugares"), resultados)
    return resposta, lugares


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "usuario" not in session or "grupo" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"erro": "Nao autenticado"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return wrapper


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "usuario" in session:
            return redirect(url_for("index"))
        return render_template("login.html")

    data = request.get_json(silent=True) or request.form
    usuario = (data.get("usuario") or "").strip()
    senha = data.get("senha") or ""

    u = USUARIOS.get(usuario.lower())
    if u and check_password_hash(u["hash"], senha):
        session["usuario"] = u["nome"]
        session["grupo"] = u["grupo"]
        return jsonify({"ok": True, "usuario": u["nome"]})
    return jsonify({"erro": "Usuario ou senha invalidos"}), 401


@app.route("/logout", methods=["POST", "GET"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    g = GRUPOS[session["grupo"]]
    return render_template(
        "index.html",
        usuario=session["usuario"],
        grupo_nome=g["nome"],
        membro1=g["membros"][0],
        membro2=g["membros"][1],
    )


@app.route("/api/gastos", methods=["GET"])
@login_required
def listar_gastos():
    grupo = session["grupo"]
    conn = get_db()
    rows = conn.execute(
        f"SELECT * FROM gastos WHERE grupo = {PH} ORDER BY criado_em DESC, id DESC",
        (grupo,),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/gastos", methods=["POST"])
@login_required
def inserir_gasto():
    data = request.get_json(silent=True) or {}
    descricao = (data.get("descricao") or "").strip()
    categoria = (data.get("categoria") or "").strip()
    quem = (data.get("quem") or "").strip()
    data_gasto = (data.get("data") or "").strip()
    tipo = (data.get("tipo") or "Viagem").strip()
    if tipo not in ("Fixo", "Viagem"):
        tipo = "Viagem"
    moeda = (data.get("moeda") or "USD").strip().upper()
    if moeda not in ("USD", "BRL"):
        moeda = "USD"

    try:
        valor = float(data.get("valor"))
    except (TypeError, ValueError):
        return jsonify({"erro": "Valor invalido"}), 400

    if not descricao or not categoria or not quem or not data_gasto:
        return jsonify({"erro": "Campos obrigatorios ausentes"}), 400

    grupo = session["grupo"]
    membros = GRUPOS[grupo]["membros"]
    if quem not in membros:
        quem = session["usuario"]

    # "De quem e" o gasto: um dos membros ou 'Dividido' (meio a meio).
    # Se nao vier valido, assume que e de quem pagou (ninguem deve nada).
    responsavel = (data.get("responsavel") or "").strip()
    if responsavel not in membros and responsavel != "Dividido":
        responsavel = quem

    criado_em = datetime.now().isoformat()
    conn = get_db()

    # Cotacao TRAVADA no momento do gasto (BRL por 1 USD). Se nao vier,
    # usa a ultima cotacao salva do grupo como padrao.
    try:
        cot = float(data.get("cotacao"))
    except (TypeError, ValueError):
        cot = 0.0
    if cot <= 0:
        cot = get_cotacao(conn, grupo)

    sql = (
        "INSERT INTO gastos (descricao, valor, categoria, quem, data, tipo, moeda, cotacao, grupo, responsavel, criado_em) "
        f"VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})"
    )
    params = (descricao, valor, categoria, quem, data_gasto, tipo, moeda, cot, grupo, responsavel, criado_em)
    if USE_PG:
        novo_id = conn.execute(sql + " RETURNING id", params).fetchone()["id"]
    else:
        novo_id = conn.execute(sql, params).lastrowid
    # lembra a ultima cotacao usada DO GRUPO (para pre-preencher o formulario)
    conn.execute(
        f"INSERT INTO config (chave, valor) VALUES ({PH}, {PH}) "
        "ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor",
        (f"cotacao:{grupo}", str(cot)),
    )
    conn.commit()
    row = conn.execute(f"SELECT * FROM gastos WHERE id = {PH}", (novo_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@app.route("/api/gastos/<int:gasto_id>", methods=["DELETE"])
@login_required
def deletar_gasto(gasto_id):
    grupo = session["grupo"]
    conn = get_db()
    cur = conn.execute(
        f"DELETE FROM gastos WHERE id = {PH} AND grupo = {PH}", (gasto_id, grupo)
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        return jsonify({"erro": "Gasto nao encontrado"}), 404
    return jsonify({"ok": True})


@app.route("/api/resumo", methods=["GET"])
@login_required
def resumo():
    exibir = request.args.get("exibir", "USD").upper()
    if exibir not in ("USD", "BRL"):
        exibir = "USD"

    grupo = session["grupo"]
    membros = GRUPOS[grupo]["membros"]
    conn = get_db()
    ultima = get_cotacao(conn, grupo)  # ultima cotacao do grupo (pre-preenche o form)
    rows = conn.execute(
        f"SELECT valor, moeda, cotacao, categoria, quem, tipo FROM gastos WHERE grupo = {PH}",
        (grupo,),
    ).fetchall()
    conn.close()

    total = 0.0
    por_categoria = {}
    por_quem = {m: 0.0 for m in membros}
    por_tipo = {"Fixo": 0.0, "Viagem": 0.0}
    for r in rows:
        v = converter(r["valor"], r["moeda"], exibir, r["cotacao"])
        total += v
        por_categoria[r["categoria"]] = por_categoria.get(r["categoria"], 0.0) + v
        if r["quem"] in por_quem:
            por_quem[r["quem"]] += v
        t = r["tipo"] if r["tipo"] in por_tipo else "Viagem"
        por_tipo[t] += v

    return jsonify(
        {
            "total_geral": total,
            "por_categoria": por_categoria,
            "por_quem": por_quem,
            "por_tipo": por_tipo,
            "cotacao": ultima,
            "exibir": exibir,
        }
    )


@app.route("/api/config", methods=["GET"])
@login_required
def get_config():
    conn = get_db()
    rate = get_cotacao(conn, session["grupo"])
    conn.close()
    return jsonify({"cotacao": rate})


@app.route("/api/config", methods=["POST"])
@login_required
def set_config():
    data = request.get_json(silent=True) or {}
    try:
        cot = float(data.get("cotacao"))
    except (TypeError, ValueError):
        return jsonify({"erro": "Cotacao invalida"}), 400
    if cot <= 0:
        return jsonify({"erro": "Cotacao invalida"}), 400
    conn = get_db()
    conn.execute(
        f"INSERT INTO config (chave, valor) VALUES ({PH}, {PH}) "
        "ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor",
        (f"cotacao:{session['grupo']}", str(cot)),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "cotacao": cot})


@app.route("/api/acerto", methods=["GET"])
@login_required
def acerto():
    exibir = request.args.get("exibir", "USD").upper()
    if exibir not in ("USD", "BRL"):
        exibir = "USD"
    grupo = session["grupo"]
    m1, m2 = GRUPOS[grupo]["membros"]

    conn = get_db()
    rows = conn.execute(
        f"SELECT valor, moeda, cotacao, quem, responsavel FROM gastos WHERE grupo = {PH}",
        (grupo,),
    ).fetchall()
    conn.close()

    # net positivo = a pessoa tem a receber; negativo = deve.
    net = {m1: 0.0, m2: 0.0}
    for r in rows:
        v = converter(r["valor"], r["moeda"], exibir, r["cotacao"])
        pagou = r["quem"]
        resp = r["responsavel"] or pagou  # vazio = de quem pagou (sem divida)
        if resp == "Dividido":
            parte = {m1: v / 2, m2: v / 2}
        elif resp in net:
            parte = {resp: v}
        else:
            parte = {pagou: v}
        for m in (m1, m2):
            pago = v if pagou == m else 0.0
            net[m] += pago - parte.get(m, 0.0)

    saldo = net[m1]  # quanto m1 tem a receber (se negativo, m1 deve)
    if abs(saldo) < 0.01:
        return jsonify({"quitado": True, "valor": 0, "exibir": exibir})
    if saldo > 0:
        devedor, credor, valor = m2, m1, saldo
    else:
        devedor, credor, valor = m1, m2, -saldo
    return jsonify(
        {
            "quitado": False,
            "devedor": devedor,
            "credor": credor,
            "valor": round(valor, 2),
            "exibir": exibir,
        }
    )


@app.route("/api/cofrinho", methods=["GET"])
@login_required
def get_cofrinho():
    grupo = session["grupo"]
    membros = GRUPOS[grupo]["membros"]
    conn = get_db()
    metas = {}
    for m in membros:
        row = conn.execute(
            f"SELECT valor FROM config WHERE chave = {PH}", (f"meta:{grupo}:{m}",)
        ).fetchone()
        try:
            metas[m] = float(row["valor"]) if row else 0.0
        except (TypeError, ValueError):
            metas[m] = 0.0
    aportes = conn.execute(
        f"SELECT * FROM aportes WHERE grupo = {PH} ORDER BY data DESC, id DESC",
        (grupo,),
    ).fetchall()
    conn.close()
    totais = {m: 0.0 for m in membros}
    for a in aportes:
        if a["quem"] in totais:
            totais[a["quem"]] += a["valor"]
    return jsonify(
        {
            "metas": metas,
            "totais": totais,
            "meta_geral": sum(metas.values()),
            "total_geral": sum(totais.values()),
            "aportes": [dict(a) for a in aportes],
        }
    )


@app.route("/api/cofrinho", methods=["POST"])
@login_required
def set_meta():
    data = request.get_json(silent=True) or {}
    grupo = session["grupo"]
    membros = GRUPOS[grupo]["membros"]
    quem = (data.get("quem") or "").strip()
    if quem not in membros:
        return jsonify({"erro": "Pessoa invalida"}), 400
    try:
        meta = float(data.get("meta"))
    except (TypeError, ValueError):
        return jsonify({"erro": "Meta invalida"}), 400
    if meta < 0:
        return jsonify({"erro": "Meta invalida"}), 400
    conn = get_db()
    conn.execute(
        f"INSERT INTO config (chave, valor) VALUES ({PH}, {PH}) "
        "ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor",
        (f"meta:{grupo}:{quem}", str(meta)),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "quem": quem, "meta": meta})


@app.route("/api/aportes", methods=["POST"])
@login_required
def add_aporte():
    data = request.get_json(silent=True) or {}
    grupo = session["grupo"]
    membros = GRUPOS[grupo]["membros"]
    quem = (data.get("quem") or "").strip()
    if quem not in membros:
        quem = session["usuario"]
    data_aporte = (data.get("data") or "").strip()
    try:
        valor = float(data.get("valor"))
    except (TypeError, ValueError):
        return jsonify({"erro": "Valor invalido"}), 400
    if valor <= 0 or not data_aporte:
        return jsonify({"erro": "Dados invalidos"}), 400

    criado_em = datetime.now().isoformat()
    conn = get_db()
    sql = (
        "INSERT INTO aportes (valor, quem, data, grupo, criado_em) "
        f"VALUES ({PH}, {PH}, {PH}, {PH}, {PH})"
    )
    params = (valor, quem, data_aporte, grupo, criado_em)
    if USE_PG:
        novo_id = conn.execute(sql + " RETURNING id", params).fetchone()["id"]
    else:
        novo_id = conn.execute(sql, params).lastrowid
    conn.commit()
    row = conn.execute(f"SELECT * FROM aportes WHERE id = {PH}", (novo_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@app.route("/api/aportes/<int:aporte_id>", methods=["DELETE"])
@login_required
def del_aporte(aporte_id):
    grupo = session["grupo"]
    conn = get_db()
    cur = conn.execute(
        f"DELETE FROM aportes WHERE id = {PH} AND grupo = {PH}", (aporte_id, grupo)
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        return jsonify({"erro": "Aporte nao encontrado"}), 404
    return jsonify({"ok": True})


@app.route("/api/desejos", methods=["GET"])
@login_required
def listar_desejos():
    grupo = session["grupo"]
    conn = get_db()
    rows = conn.execute(
        f"SELECT * FROM desejos WHERE grupo = {PH} ORDER BY id DESC", (grupo,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/desejos", methods=["POST"])
@login_required
def add_desejo():
    data = request.get_json(silent=True) or {}
    grupo = session["grupo"]
    membros = GRUPOS[grupo]["membros"]
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"erro": "Nome obrigatorio"}), 400
    moeda = (data.get("moeda") or "USD").strip().upper()
    if moeda not in ("USD", "BRL"):
        moeda = "USD"
    quem = (data.get("quem") or "").strip()
    if quem not in membros:
        quem = ""
    try:
        valor = float(data.get("valor"))
    except (TypeError, ValueError):
        valor = 0.0
    if valor < 0:
        valor = 0.0

    criado_em = datetime.now().isoformat()
    conn = get_db()
    sql = (
        "INSERT INTO desejos (nome, valor, moeda, quem, grupo, criado_em) "
        f"VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH})"
    )
    params = (nome, valor, moeda, quem, grupo, criado_em)
    if USE_PG:
        novo_id = conn.execute(sql + " RETURNING id", params).fetchone()["id"]
    else:
        novo_id = conn.execute(sql, params).lastrowid
    conn.commit()
    row = conn.execute(f"SELECT * FROM desejos WHERE id = {PH}", (novo_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@app.route("/api/desejos/<int:desejo_id>", methods=["DELETE"])
@login_required
def del_desejo(desejo_id):
    grupo = session["grupo"]
    conn = get_db()
    cur = conn.execute(
        f"DELETE FROM desejos WHERE id = {PH} AND grupo = {PH}", (desejo_id, grupo)
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        return jsonify({"erro": "Desejo nao encontrado"}), 404
    return jsonify({"ok": True})


@app.route("/api/buscar-lugares", methods=["POST"])
@login_required
def buscar_lugares():
    if not TAVILY_API_KEY:
        return (
            jsonify(
                {"erro": "Busca nao configurada. Defina TAVILY_API_KEY no ambiente."}
            ),
            503,
        )
    data = request.get_json(silent=True) or {}

    # Aceita a conversa inteira em "mensagens" (chat) ou, por compatibilidade,
    # uma unica "pergunta".
    mensagens = data.get("mensagens")
    if not isinstance(mensagens, list):
        pergunta = (data.get("pergunta") or "").strip()
        mensagens = [{"papel": "user", "texto": pergunta}] if pergunta else []
    mensagens = [
        {
            "papel": "user" if m.get("papel") == "user" else "assistant",
            "texto": (m.get("texto") or "").strip()[:1000],
        }
        for m in mensagens
        if isinstance(m, dict) and (m.get("texto") or "").strip()
    ][-12:]
    if not mensagens:
        return jsonify({"erro": "Escreva o que voce procura."}), 400

    # 1) Consulta autossuficiente (lida com follow-ups) e busca real (Tavily).
    query = _query_de_busca(mensagens)
    try:
        resultados = _tavily_buscar(query)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            msg = "A TAVILY_API_KEY parece inválida. Confira a chave."
        elif e.code == 429:
            msg = "Cota de buscas do mês esgotada (Tavily). Tente no próximo ciclo."
        else:
            msg = f"A busca falhou (HTTP {e.code}). Tente de novo."
        return jsonify({"erro": msg}), 502
    except urllib.error.URLError:
        return jsonify({"erro": "Nao consegui fazer a busca agora. Tente de novo."}), 502
    except Exception:
        return jsonify({"erro": "Erro inesperado na busca."}), 500

    fontes = [{"url": r["url"], "titulo": r["titulo"]} for r in resultados]

    # 2) Gemini responde conversando + sugere lugares. Se falhar, cai nos
    #    resultados crus do Tavily - o chat nunca fica sem resposta.
    resposta, lugares = _gemini_conversa(mensagens, resultados)
    if lugares is None:
        lugares = [
            {
                "nome": r["titulo"] or r["url"],
                "descricao": r["conteudo"][:300],
                "url": r["url"],
            }
            for r in resultados[:6]
        ]
    if not resposta:
        resposta = (
            "Achei estas opções pra você 👇"
            if lugares
            else "Não encontrei lugares confiáveis pra isso. Quer tentar descrever de outro jeito?"
        )

    return jsonify({"resposta": resposta, "lugares": lugares, "fontes": fontes})


@app.route("/api/lugares", methods=["GET"])
@login_required
def listar_lugares():
    grupo = session["grupo"]
    conn = get_db()
    rows = conn.execute(
        f"SELECT * FROM lugares WHERE grupo = {PH} ORDER BY id DESC", (grupo,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/lugares", methods=["POST"])
@login_required
def add_lugar():
    data = request.get_json(silent=True) or {}
    grupo = session["grupo"]
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"erro": "Nome obrigatorio"}), 400
    descricao = (data.get("descricao") or "").strip()
    url = (data.get("url") or "").strip()
    if not url.lower().startswith("http"):
        url = ""
    busca = (data.get("busca") or "").strip()

    criado_em = datetime.now().isoformat()
    conn = get_db()
    sql = (
        "INSERT INTO lugares (nome, descricao, url, busca, quem, grupo, criado_em) "
        f"VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})"
    )
    params = (
        nome[:200],
        descricao[:500],
        url[:500],
        busca[:500],
        session["usuario"],
        grupo,
        criado_em,
    )
    if USE_PG:
        novo_id = conn.execute(sql + " RETURNING id", params).fetchone()["id"]
    else:
        novo_id = conn.execute(sql, params).lastrowid
    conn.commit()
    row = conn.execute(f"SELECT * FROM lugares WHERE id = {PH}", (novo_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@app.route("/api/lugares/<int:lugar_id>", methods=["DELETE"])
@login_required
def del_lugar(lugar_id):
    grupo = session["grupo"]
    conn = get_db()
    cur = conn.execute(
        f"DELETE FROM lugares WHERE id = {PH} AND grupo = {PH}", (lugar_id, grupo)
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        return jsonify({"erro": "Lugar nao encontrado"}), 404
    return jsonify({"ok": True})


# ----- Essenciais (checklist do que falta comprar) -----
# Itens que ja aparecem preenchidos na 1a vez de cada casal.
ESSENCIAIS_PADRAO = [
    "✈️ Passagem",
    "🏨 Hospedagem",
    "🚗 Carro",
    "🎢 Ingressos Disney",
    "🎟️ Ingressos Universal",
]


@app.route("/api/essenciais", methods=["GET"])
@login_required
def listar_essenciais():
    grupo = session["grupo"]
    conn = get_db()
    # Semeia os itens padrao uma unica vez por casal (marca no config).
    ja = conn.execute(
        f"SELECT valor FROM config WHERE chave = {PH}", (f"essenciais_seed:{grupo}",)
    ).fetchone()
    if not ja:
        criado_em = datetime.now().isoformat()
        for nome in ESSENCIAIS_PADRAO:
            conn.execute(
                "INSERT INTO essenciais (nome, valor, moeda, obs, comprado, grupo, criado_em) "
                f"VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})",
                (nome, 0, "USD", "", 0, grupo, criado_em),
            )
        conn.execute(
            f"INSERT INTO config (chave, valor) VALUES ({PH}, {PH}) "
            "ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor",
            (f"essenciais_seed:{grupo}", "1"),
        )
        conn.commit()
    rows = conn.execute(
        f"SELECT * FROM essenciais WHERE grupo = {PH} ORDER BY comprado ASC, id ASC",
        (grupo,),
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/essenciais", methods=["POST"])
@login_required
def add_essencial():
    data = request.get_json(silent=True) or {}
    grupo = session["grupo"]
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"erro": "Nome obrigatorio"}), 400
    moeda = (data.get("moeda") or "USD").strip().upper()
    if moeda not in ("USD", "BRL"):
        moeda = "USD"
    obs = (data.get("obs") or "").strip()[:300]
    try:
        valor = float(data.get("valor"))
    except (TypeError, ValueError):
        valor = 0.0
    if valor < 0:
        valor = 0.0

    criado_em = datetime.now().isoformat()
    conn = get_db()
    sql = (
        "INSERT INTO essenciais (nome, valor, moeda, obs, comprado, grupo, criado_em) "
        f"VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})"
    )
    params = (nome[:120], valor, moeda, obs, 0, grupo, criado_em)
    if USE_PG:
        novo_id = conn.execute(sql + " RETURNING id", params).fetchone()["id"]
    else:
        novo_id = conn.execute(sql, params).lastrowid
    conn.commit()
    row = conn.execute(f"SELECT * FROM essenciais WHERE id = {PH}", (novo_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@app.route("/api/essenciais/<int:item_id>", methods=["PUT"])
@login_required
def atualizar_essencial(item_id):
    data = request.get_json(silent=True) or {}
    grupo = session["grupo"]
    conn = get_db()
    atual = conn.execute(
        f"SELECT * FROM essenciais WHERE id = {PH} AND grupo = {PH}", (item_id, grupo)
    ).fetchone()
    if not atual:
        conn.close()
        return jsonify({"erro": "Item nao encontrado"}), 404
    atual = dict(atual)

    nome = str(data.get("nome", atual["nome"]) or atual["nome"]).strip()[:120] or atual["nome"]
    obs = str(data.get("obs", atual["obs"]) or "").strip()[:300]
    moeda = str(data.get("moeda") or atual["moeda"] or "USD").strip().upper()
    if moeda not in ("USD", "BRL"):
        moeda = "USD"
    try:
        valor = float(data["valor"]) if data.get("valor") not in (None, "") else float(atual["valor"] or 0)
    except (TypeError, ValueError, KeyError):
        valor = float(atual["valor"] or 0)
    if valor < 0:
        valor = 0.0
    comprado = data.get("comprado")
    comprado = int(bool(comprado)) if comprado is not None else int(atual["comprado"] or 0)

    conn.execute(
        f"UPDATE essenciais SET nome = {PH}, valor = {PH}, moeda = {PH}, obs = {PH}, "
        f"comprado = {PH} WHERE id = {PH} AND grupo = {PH}",
        (nome, valor, moeda, obs, comprado, item_id, grupo),
    )
    conn.commit()
    row = conn.execute(f"SELECT * FROM essenciais WHERE id = {PH}", (item_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))


@app.route("/api/essenciais/<int:item_id>", methods=["DELETE"])
@login_required
def del_essencial(item_id):
    grupo = session["grupo"]
    conn = get_db()
    cur = conn.execute(
        f"DELETE FROM essenciais WHERE id = {PH} AND grupo = {PH}", (item_id, grupo)
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        return jsonify({"erro": "Item nao encontrado"}), 404
    return jsonify({"ok": True})


# Garante que o banco existe mesmo sob gunicorn (sem rodar __main__).
init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)

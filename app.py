import os
import sqlite3
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
    conn = get_db()
    row = conn.execute(
        f"SELECT valor FROM config WHERE chave = {PH}", (f"meta_grana:{grupo}",)
    ).fetchone()
    try:
        meta = float(row["valor"]) if row else 0.0
    except (TypeError, ValueError):
        meta = 0.0
    aportes = conn.execute(
        f"SELECT * FROM aportes WHERE grupo = {PH} ORDER BY data DESC, id DESC",
        (grupo,),
    ).fetchall()
    conn.close()
    total = sum(a["valor"] for a in aportes)
    return jsonify(
        {"meta": meta, "total": total, "aportes": [dict(a) for a in aportes]}
    )


@app.route("/api/cofrinho", methods=["POST"])
@login_required
def set_meta():
    data = request.get_json(silent=True) or {}
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
        (f"meta_grana:{session['grupo']}", str(meta)),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "meta": meta})


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


# Garante que o banco existe mesmo sob gunicorn (sem rodar __main__).
init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)

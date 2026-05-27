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

# Senhas vem SO de variaveis de ambiente (nenhuma senha fica no codigo).
# Localmente, defina-as no arquivo .env (que NAO vai pro Git).
# Se a variavel nao existir, aquele usuario simplesmente nao consegue logar.
USUARIOS = {}
for _nome, _var in (("Danilo", "DANILO_SENHA"), ("Rafaella", "RAFAELLA_SENHA")):
    _senha = os.environ.get(_var)
    if _senha:
        USUARIOS[_nome] = generate_password_hash(_senha)


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
            criado_em TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS config (chave TEXT PRIMARY KEY, valor TEXT)"
    )
    # Migracoes para bancos criados antes destes campos.
    if USE_PG:
        conn.execute("ALTER TABLE gastos ADD COLUMN IF NOT EXISTS tipo TEXT NOT NULL DEFAULT 'Viagem'")
        conn.execute("ALTER TABLE gastos ADD COLUMN IF NOT EXISTS moeda TEXT NOT NULL DEFAULT 'USD'")
    else:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(gastos)").fetchall()]
        if "tipo" not in cols:
            conn.execute("ALTER TABLE gastos ADD COLUMN tipo TEXT NOT NULL DEFAULT 'Viagem'")
        if "moeda" not in cols:
            conn.execute("ALTER TABLE gastos ADD COLUMN moeda TEXT NOT NULL DEFAULT 'USD'")
    # Cotacao padrao (1 USD = X BRL); so insere se ainda nao existir.
    conn.execute(
        "INSERT INTO config (chave, valor) VALUES ('cotacao', '5.50') "
        "ON CONFLICT (chave) DO NOTHING"
    )
    conn.commit()
    conn.close()


def get_cotacao(conn):
    row = conn.execute(
        f"SELECT valor FROM config WHERE chave = {PH}", ("cotacao",)
    ).fetchone()
    try:
        return float(row["valor"]) if row else 5.50
    except (TypeError, ValueError):
        return 5.50


def converter(valor, moeda, exibir, rate):
    """Converte um valor da sua moeda para a moeda de exibicao (rate = BRL por 1 USD)."""
    moeda = moeda or "USD"
    if moeda == exibir:
        return valor
    if exibir == "BRL":
        return valor * rate          # gasto em USD -> BRL
    return valor / rate              # gasto em BRL -> USD


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "usuario" not in session:
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

    hash_senha = USUARIOS.get(usuario)
    if hash_senha and check_password_hash(hash_senha, senha):
        session["usuario"] = usuario
        return jsonify({"ok": True, "usuario": usuario})
    return jsonify({"erro": "Usuario ou senha invalidos"}), 401


@app.route("/logout", methods=["POST", "GET"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template("index.html", usuario=session["usuario"])


@app.route("/api/gastos", methods=["GET"])
@login_required
def listar_gastos():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM gastos ORDER BY criado_em DESC, id DESC"
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

    criado_em = datetime.now().isoformat()
    conn = get_db()
    sql = (
        "INSERT INTO gastos (descricao, valor, categoria, quem, data, tipo, moeda, criado_em) "
        f"VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH})"
    )
    params = (descricao, valor, categoria, quem, data_gasto, tipo, moeda, criado_em)
    if USE_PG:
        novo_id = conn.execute(sql + " RETURNING id", params).fetchone()["id"]
    else:
        novo_id = conn.execute(sql, params).lastrowid
    conn.commit()
    row = conn.execute(f"SELECT * FROM gastos WHERE id = {PH}", (novo_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@app.route("/api/gastos/<int:gasto_id>", methods=["DELETE"])
@login_required
def deletar_gasto(gasto_id):
    conn = get_db()
    cur = conn.execute(f"DELETE FROM gastos WHERE id = {PH}", (gasto_id,))
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

    conn = get_db()
    rate = get_cotacao(conn)
    rows = conn.execute(
        "SELECT valor, moeda, categoria, quem, tipo FROM gastos"
    ).fetchall()
    conn.close()

    total = 0.0
    por_categoria = {}
    por_quem = {"Danilo": 0.0, "Rafaella": 0.0}
    por_tipo = {"Fixo": 0.0, "Viagem": 0.0}
    for r in rows:
        v = converter(r["valor"], r["moeda"], exibir, rate)
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
            "cotacao": rate,
            "exibir": exibir,
        }
    )


@app.route("/api/config", methods=["GET"])
@login_required
def get_config():
    conn = get_db()
    rate = get_cotacao(conn)
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
        f"INSERT INTO config (chave, valor) VALUES ('cotacao', {PH}) "
        "ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor",
        (str(cot),),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "cotacao": cot})


# Garante que o banco existe mesmo sob gunicorn (sem rodar __main__).
init_db()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)

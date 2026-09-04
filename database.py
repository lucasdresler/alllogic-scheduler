import sqlite3
from contextlib import contextmanager

DB_PATH = "barbearia.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_session():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db_session() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS servico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preco REAL NOT NULL,
                duracao_minutos INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS profissional (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agendamento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_nome TEXT NOT NULL,
                cliente_telefone TEXT NOT NULL,
                servico_id INTEGER NOT NULL,
                profissional_id INTEGER NOT NULL,
                data TEXT NOT NULL,
                hora TEXT NOT NULL,
                criado_em TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (servico_id) REFERENCES servico(id),
                FOREIGN KEY (profissional_id) REFERENCES profissional(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL
            )
        """)

        seed_data(conn)


def seed_data(conn):
    count_servicos = conn.execute("SELECT COUNT(*) AS c FROM servico").fetchone()["c"]
    if count_servicos == 0:
        conn.executemany(
            "INSERT INTO servico (nome, preco, duracao_minutos) VALUES (?, ?, ?)",
            [
                ("Corte", 40.0, 30),
                ("Barba", 35.0, 30),
                ("Corte + Barba", 70.0, 60),
            ],
        )

    count_profissionais = conn.execute("SELECT COUNT(*) AS c FROM profissional").fetchone()["c"]
    if count_profissionais == 0:
        conn.executemany(
            "INSERT INTO profissional (nome, ativo) VALUES (?, 1)",
            [("Carlos",), ("Rafael",)],
        )

    count_admin = conn.execute("SELECT COUNT(*) AS c FROM admin").fetchone()["c"]
    if count_admin == 0:
        from werkzeug.security import generate_password_hash

        conn.execute(
            "INSERT INTO admin (usuario, senha_hash) VALUES (?, ?)",
            ("admin", generate_password_hash("barbeariatop123")),
        )

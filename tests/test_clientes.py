import ipaddress
import os
import re
import uuid
from datetime import date, timedelta

import pytest

if os.environ.get("SCHEDULER_TEST_DATABASE") != "1":
    pytest.skip(
        "Defina SCHEDULER_TEST_DATABASE=1 para habilitar testes com PostgreSQL isolado.",
        allow_module_level=True,
    )

_database_name = os.environ.get("POSTGRES_DB", "")
_database_host = os.environ.get("POSTGRES_HOST", "")
try:
    _host_is_local = ipaddress.ip_address(_database_host).is_loopback
except ValueError:
    _host_is_local = False

if not re.fullmatch(r"scheduler_test_[a-zA-Z0-9_]+", _database_name) or not _host_is_local:
    raise RuntimeError(
        "Os testes exigem POSTGRES_DB scheduler_test_* e POSTGRES_HOST de loopback."
    )

os.environ.setdefault("SECRET_KEY", "scheduler-test-only-secret")
os.environ.setdefault("ADMIN_SENHA_INICIAL", "scheduler-test-password")

import database
from app import app
import models

app.config["TESTING"] = True


@pytest.fixture
def client():
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def logged_admin(client):
    suffix = uuid.uuid4().hex[:8]
    username = f"admin_{suffix}"
    with database.db_session() as conn:
        conn.execute(
            """
            INSERT INTO admin (usuario, senha_hash, senha_inicial_alterada, email, nome_responsavel)
            VALUES (%s, 'dummyhash', TRUE, 'admin@teste.com', 'Responsavel Teste')
            ON CONFLICT (usuario) DO NOTHING
            """,
            (username,),
        )
    with client.session_transaction() as session:
        session["admin_logado"] = True
        session["admin_usuario"] = username
    return username


def _csrf_token(client, path):
    response = client.get(path)
    assert response.status_code == 200
    match = re.search(
        r'name="csrf_token"\s+value="([^"]+)"',
        response.get_data(as_text=True),
    )
    assert match, f"csrf_token not found in {path}"
    return match.group(1)


def test_admin_clientes_requer_login(client):
    res = client.get("/admin/clientes")
    assert res.status_code == 302
    assert "/admin/login" in res.headers["Location"]


def test_admin_clientes_listagem(client, logged_admin):
    # Cria cliente de teste
    suffix = uuid.uuid4().hex[:6]
    nome = f"Cliente Listagem {suffix}"
    tel = f"(11) 9{suffix[:4]}-0000"
    cid, err = models.criar_cliente(nome, tel, f"teste_{suffix}@exemplo.com", "Obs teste")
    assert err is None

    res = client.get("/admin/clientes")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Gerenciar clientes" in html
    assert nome in html
    assert tel in html


def test_admin_clientes_busca(client, logged_admin):
    suffix = uuid.uuid4().hex[:6]
    nome_alvo = f"BuscaAlvo {suffix}"
    tel_alvo = f"(11) 8{suffix[:4]}-1111"
    models.criar_cliente(nome_alvo, tel_alvo)

    # Busca por nome
    res = client.get(f"/admin/clientes?busca=BuscaAlvo+{suffix}")
    assert res.status_code == 200
    assert nome_alvo in res.get_data(as_text=True)

    # Busca por telefone
    res_tel = client.get(f"/admin/clientes?busca=8{suffix[:4]}")
    assert res_tel.status_code == 200
    assert nome_alvo in res_tel.get_data(as_text=True)


def test_admin_criar_e_editar_cliente(client, logged_admin):
    token_novo = _csrf_token(client, "/admin/clientes/novo")
    suffix = uuid.uuid4().hex[:6]
    nome = f"Cliente Form {suffix}"
    tel = f"(11) 9{suffix[:4]}-2222"

    # POST novo
    res = client.post(
        "/admin/clientes/novo",
        data={
            "csrf_token": token_novo,
            "nome": nome,
            "telefone": tel,
            "email": "form@exemplo.com",
            "observacoes": "Anotação especial de teste",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Cliente cadastrado com sucesso" in html
    assert nome in html

    # Localiza o ID
    cliente = [c for c in models.listar_clientes(nome) if c["nome"] == nome][0]
    cid = cliente["id"]

    # POST editar
    token_edit = _csrf_token(client, f"/admin/clientes/{cid}/editar")
    novo_nome = f"Cliente Editado {suffix}"
    res_edit = client.post(
        f"/admin/clientes/{cid}/editar",
        data={
            "csrf_token": token_edit,
            "nome": novo_nome,
            "telefone": tel,
            "email": "editado@exemplo.com",
            "observacoes": "Observação atualizada",
        },
        follow_redirects=True,
    )
    assert res_edit.status_code == 200
    html_edit = res_edit.get_data(as_text=True)
    assert "Dados do cliente atualizados com sucesso" in html_edit
    assert novo_nome in html_edit
    assert "Observação atualizada" in html_edit


def test_admin_detalhes_e_historico_cliente(client, logged_admin):
    # Cria serviço e profissional
    suffix = uuid.uuid4().hex[:6]
    sid, _ = models.criar_servico(f"Servico {suffix}", 50.0, 30, True)
    pid, _ = models.criar_profissional(f"Prof {suffix}", True, [sid])

    # Cria cliente e agendamento
    nome_cli = f"Cliente Hist {suffix}"
    tel_cli = f"(11) 9{suffix[:4]}-3333"
    cid, _ = models.criar_cliente(nome_cli, tel_cli)

    dias = models.dias_funcionamento()
    d = date.today() + timedelta(days=2)
    while d.weekday() not in dias:
        d += timedelta(days=1)
    data_str = d.strftime("%Y-%m-%d")

    horarios = models.horarios_disponiveis(pid, data_str, [sid])
    if horarios:
        ag_id, err = models.criar_agendamento(nome_cli, tel_cli, [sid], pid, data_str, horarios[0])
        assert err is None
        assert ag_id is not None

        res = client.get(f"/admin/clientes/{cid}")
        assert res.status_code == 200
        html = res.get_data(as_text=True)
        assert nome_cli in html
        assert f"Servico {suffix}" in html
        assert f"Prof {suffix}" in html

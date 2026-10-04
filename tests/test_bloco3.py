import ipaddress
import os
import re
import uuid
from datetime import date, timedelta
from functools import lru_cache

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

import psycopg
from psycopg import sql

import app as app_module
import database
from app import app
import models


app.config["TESTING"] = True


@pytest.fixture
def client():
    with app.test_client() as test_client:
        yield test_client


def _csrf_token(client, path):
    response = client.get(path)
    assert response.status_code == 200
    match = re.search(
        r'name="csrf_token"\s+value="([^"]+)"',
        response.get_data(as_text=True),
    )
    assert match
    return match.group(1)


def _config_payload(dias="1,3,5", antecedencia="14"):
    return {
        "nome_estabelecimento": "Scheduler Teste",
        "telefone_estabelecimento": "11999990000",
        "endereco_estabelecimento": "Rua de Teste",
        "nome_publico": "Scheduler Teste",
        "dias_antecedencia_agendamento": antecedencia,
        "horario_abertura": "08:30",
        "horario_fechamento": "11:00",
        "intervalo_slot_minutos": "30",
        "dias_funcionamento": dias,
    }


def test_professional_status_is_editable_only_from_edit_screen(client):
    suffix = uuid.uuid4().hex
    service_id, error = models.criar_servico(
        f"Serviço UX {suffix}", "40.00", 30, True, "Teste de status"
    )
    assert error is None
    professional_id, error = models.criar_profissional(
        f"Profissional UX {suffix}", True, [service_id]
    )
    assert error is None

    with client.session_transaction() as session:
        session["admin_logado"] = True

    listing = client.get("/admin/profissionais").get_data(as_text=True)
    assert "Status" in listing
    assert "Ativo" in listing
    assert "Editar" in listing
    assert f'/admin/profissionais/{professional_id}/toggle' not in listing
    assert f'href="/admin/profissionais/{professional_id}/editar"' in listing

    edit_path = f"/admin/profissionais/{professional_id}/editar"
    edit_page = client.get(edit_path).get_data(as_text=True)
    assert 'name="ativo" checked' in edit_page
    assert "desmarque para desativar" in edit_page

    token = _csrf_token(client, edit_path)
    deactivated = client.post(
        edit_path,
        data={
            "csrf_token": token,
            "nome": f"Profissional UX {suffix}",
            "servicos": str(service_id),
        },
    )
    assert deactivated.status_code == 302
    assert models.obter_profissional(professional_id)["ativo"] is False

    token = _csrf_token(client, edit_path)
    activated = client.post(
        edit_path,
        data={
            "csrf_token": token,
            "nome": f"Profissional UX {suffix}",
            "ativo": "on",
            "servicos": str(service_id),
        },
    )
    assert activated.status_code == 302
    assert models.obter_profissional(professional_id)["ativo"] is True


def test_success_page_uses_establishment_name(monkeypatch, client):
    monkeypatch.setattr(
        models,
        "obter_agendamento_completo",
        lambda appointment_id: {
            "servico_nome": "Serviço de teste",
            "servico_preco": 50,
            "profissional_nome": "Profissional de teste",
            "data": "2030-01-01",
            "hora": "10:00",
            "cliente_nome": "Cliente de teste",
        },
    )
    monkeypatch.setattr(
        app_module,
        "_carregar_config_template",
        lambda: {"nome_estabelecimento": "Estabelecimento de teste"},
    )

    response = client.get("/agendamento/sucesso/1")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "<h1>Estabelecimento de teste</h1>" in page
    assert "<title>Agendamento Confirmado — Estabelecimento de teste</title>" in page
    assert "Barbearia Top" not in page


def test_admin_auth_settings_and_service_description(client):
    assert client.get("/admin/servicos").status_code == 302

    login_token = _csrf_token(client, "/admin/login")
    rejected = client.post(
        "/admin/login",
        data={
            "csrf_token": login_token,
            "usuario": "admin",
            "senha": "senha-incorreta",
        },
    )
    assert rejected.status_code == 200
    assert "Usuário ou senha inválidos" in rejected.get_data(as_text=True)

    login_token = _csrf_token(client, "/admin/login")
    accepted = client.post(
        "/admin/login",
        data={
            "csrf_token": login_token,
            "usuario": "admin",
            "senha": os.environ["ADMIN_SENHA_INICIAL"],
        },
    )
    assert accepted.status_code == 302
    assert client.get("/admin/servicos").status_code == 200

    service_token = _csrf_token(client, "/admin/servicos/novo")
    created = client.post(
        "/admin/servicos/novo",
        data={
            "csrf_token": service_token,
            "nome": f"Serviço descrição {uuid.uuid4().hex}",
            "descricao": "Descrição persistida no CRUD.",
            "preco": "52.50",
            "duracao_minutos": "30",
            "ativo": "on",
        },
    )
    assert created.status_code == 302
    with database.db_session() as conn:
        service = conn.execute(
            "SELECT id, descricao FROM servico ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert service["descricao"] == "Descrição persistida no CRUD."

    edit_path = f"/admin/servicos/{service['id']}/editar"
    edit_token = _csrf_token(client, edit_path)
    updated = client.post(
        edit_path,
        data={
            "csrf_token": edit_token,
            "nome": f"Serviço atualizado {uuid.uuid4().hex}",
            "descricao": "Descrição atualizada.",
            "preco": "57.00",
            "duracao_minutos": "45",
            "ativo": "on",
        },
    )
    assert updated.status_code == 302
    assert models.obter_servico(service["id"])["descricao"] == "Descrição atualizada."

    models._limpar_cache_config()
    models.dias_funcionamento()
    with database.db_session() as conn:
        generation = conn.execute(
            "SELECT valor FROM configuracao WHERE chave = %s",
            (database.CONFIG_CACHE_VERSION_KEY,),
        ).fetchone()["valor"]
        previous_days = conn.execute(
            "SELECT valor FROM configuracao WHERE chave = 'dias_funcionamento'"
        ).fetchone()["valor"]

    @lru_cache(maxsize=1)
    def other_worker_config(config_generation):
        return models._carregar_configuracoes()

    assert other_worker_config(generation)["dias_funcionamento"] == previous_days
    settings_token = _csrf_token(client, "/admin/configuracoes")
    saved = client.post(
        "/admin/configuracoes",
        data={"csrf_token": settings_token, **_config_payload()},
    )
    assert saved.status_code == 200
    assert models.dias_funcionamento() == [1, 3, 5]
    assert models.horario_abertura() == "08:30"
    with database.db_session() as conn:
        updated_generation = conn.execute(
            "SELECT valor FROM configuracao WHERE chave = %s",
            (database.CONFIG_CACHE_VERSION_KEY,),
        ).fetchone()["valor"]
    assert updated_generation != generation
    assert other_worker_config(updated_generation)["dias_funcionamento"] == "1,3,5"

    invalid_token = _csrf_token(client, "/admin/configuracoes")
    invalid = client.post(
        "/admin/configuracoes",
        data={
            "csrf_token": invalid_token,
            **_config_payload(dias="7"),
        },
    )
    assert invalid.status_code == 200
    assert "entre 0 e 6" in invalid.get_data(as_text=True)
    assert models.dias_funcionamento() == [1, 3, 5]

    invalid_interval_token = _csrf_token(client, "/admin/configuracoes")
    invalid_interval = client.post(
        "/admin/configuracoes",
        data={
            "csrf_token": invalid_interval_token,
            **_config_payload(),
            "intervalo_slot_minutos": "0",
        },
    )
    assert invalid_interval.status_code == 200
    assert "múltiplo de 15" in invalid_interval.get_data(as_text=True)
    assert models.intervalo_slot_minutos() == 30

    invalid_cases = [
        ({"dias_funcionamento": "1,1"}, "únicos"),
        ({"dias_antecedencia_agendamento": "-1"}, "não pode ser negativa"),
        ({"horario_fechamento": "08:00"}, "posterior à abertura"),
    ]
    for overrides, message in invalid_cases:
        token = _csrf_token(client, "/admin/configuracoes")
        response = client.post(
            "/admin/configuracoes",
            data={"csrf_token": token, **_config_payload(), **overrides},
        )
        assert response.status_code == 200
        assert message in response.get_data(as_text=True)
    assert models.dias_funcionamento() == [1, 3, 5]

    home = client.get("/").get_data(as_text=True)
    assert "window.DIAS_FUNCIONAMENTO = [1, 3, 5]" in home


def test_inactive_compatibility_calendar_and_snapshots(client):
    suffix = uuid.uuid4().hex
    first_id, error = models.criar_servico(
        f"Serviço A {suffix}", "40.00", 30, True, "A"
    )
    assert error is None
    second_id, error = models.criar_servico(
        f"Serviço B {suffix}", "35.00", 30, True, "B"
    )
    assert error is None
    inactive_service_id, error = models.criar_servico(
        f"Serviço inativo {suffix}", "25.00", 30, False, "Inativo"
    )
    assert error is None

    compatible_id, error = models.criar_profissional(
        f"Compatível {suffix}", True, [first_id, second_id]
    )
    assert error is None
    partial_id, error = models.criar_profissional(
        f"Parcial {suffix}", True, [first_id]
    )
    assert error is None
    inactive_professional_id, error = models.criar_profissional(
        f"Profissional inativo {suffix}", False, [first_id, second_id]
    )
    assert error is None

    booking_date = date.today() + timedelta(days=1)
    day_number = (booking_date.weekday() + 1) % 7
    with database.db_session() as conn:
        database.atualizar_configuracoes(
            conn,
            {
                "dias_funcionamento": str(day_number),
                "dias_antecedencia_agendamento": "30",
                "horario_abertura": "09:00",
                "horario_fechamento": "10:00",
                "intervalo_slot_minutos": "45",
            },
        )
    models._limpar_cache_config()

    services = client.get("/api/services").get_json()
    assert inactive_service_id not in {item["id"] for item in services}

    professionals = client.get(
        "/api/professionals",
        query_string=[("servico_id", first_id), ("servico_id", second_id)],
    ).get_json()
    assert {item["id"] for item in professionals} == {compatible_id}
    assert partial_id not in {item["id"] for item in professionals}
    assert inactive_professional_id not in {item["id"] for item in professionals}

    availability_path = "/api/availability"
    base_query = {
        "profissional_id": compatible_id,
        "data": booking_date.isoformat(),
    }
    inactive_service = client.get(
        availability_path,
        query_string={**base_query, "servico_id": inactive_service_id},
    )
    assert inactive_service.status_code == 400
    inactive_professional = client.get(
        availability_path,
        query_string={
            **base_query,
            "profissional_id": inactive_professional_id,
            "servico_id": first_id,
        },
    )
    assert inactive_professional.status_code == 400

    available = client.get(
        availability_path,
        query_string={**base_query, "servico_id": first_id},
    ).get_json()["horarios"]
    assert available == ["09:00"]
    closed_date = booking_date + timedelta(days=1)
    closed = client.get(
        availability_path,
        query_string={
            **base_query,
            "data": closed_date.isoformat(),
            "servico_id": first_id,
        },
    ).get_json()["horarios"]
    assert closed == []

    invalid_service_booking = client.post(
        "/api/appointments",
        json={
            "cliente_nome": "Cliente teste",
            "cliente_telefone": "11999990000",
            "servico_ids": [inactive_service_id],
            "profissional_id": compatible_id,
            "data": booking_date.isoformat(),
            "hora": "09:00",
        },
    )
    assert invalid_service_booking.status_code == 400
    invalid_professional_booking = client.post(
        "/api/appointments",
        json={
            "cliente_nome": "Cliente teste",
            "cliente_telefone": "11999990000",
            "servico_ids": [first_id],
            "profissional_id": inactive_professional_id,
            "data": booking_date.isoformat(),
            "hora": "09:00",
        },
    )
    assert invalid_professional_booking.status_code == 400

    incompatible_booking = client.post(
        "/api/appointments",
        json={
            "cliente_nome": "Cliente teste",
            "cliente_telefone": "11999990000",
            "servico_ids": [second_id],
            "profissional_id": partial_id,
            "data": booking_date.isoformat(),
            "hora": "09:00",
        },
    )
    assert incompatible_booking.status_code == 409

    booking = client.post(
        "/api/appointments",
        json={
            "cliente_nome": "Cliente histórico",
            "cliente_telefone": "11999990001",
            "servico_ids": [first_id],
            "profissional_id": compatible_id,
            "data": booking_date.isoformat(),
            "hora": "09:00",
        },
    )
    assert booking.status_code == 201
    appointment_id = booking.get_json()["agendamento_id"]

    changed, error = models.atualizar_servico(
        first_id,
        f"Serviço A editado {suffix}",
        "99.00",
        90,
        True,
        "Descrição alterada",
    )
    assert changed and error is None
    changed, error = models.atualizar_profissional(
        compatible_id,
        f"Profissional editado {suffix}",
        True,
        [first_id, second_id],
    )
    assert changed and error is None

    history = models.obter_agendamento_completo(appointment_id)
    assert history["profissional_nome"] == f"Compatível {suffix}"
    assert history["servicos"][0]["nome"] == f"Serviço A {suffix}"
    assert float(history["servicos"][0]["preco"]) == 40.0
    assert history["servicos"][0]["duracao_minutos"] == 30


def test_migration_adds_snapshots_without_overwriting(monkeypatch):
    legacy_database = f"scheduler_test_legacy_{uuid.uuid4().hex}"
    connection_options = {
        "host": os.environ["POSTGRES_HOST"],
        "port": os.environ["POSTGRES_PORT"],
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
    }
    with psycopg.connect(dbname=_database_name, **connection_options, autocommit=True) as conn:
        conn.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(legacy_database))
        )

    with psycopg.connect(dbname=legacy_database, **connection_options) as conn:
        conn.execute("CREATE TABLE configuracao (chave TEXT PRIMARY KEY, valor TEXT NOT NULL)")
        conn.execute(
            """
            CREATE TABLE servico (
                id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                nome TEXT NOT NULL,
                preco NUMERIC(10, 2) NOT NULL,
                duracao_minutos INTEGER NOT NULL,
                ativo BOOLEAN NOT NULL DEFAULT TRUE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE profissional (
                id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                nome TEXT NOT NULL,
                ativo BOOLEAN NOT NULL DEFAULT TRUE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE profissional_servico (
                profissional_id INTEGER NOT NULL,
                servico_id INTEGER NOT NULL,
                PRIMARY KEY (profissional_id, servico_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE agendamento (
                id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                cliente_nome TEXT NOT NULL,
                cliente_telefone TEXT NOT NULL,
                servico_id INTEGER NOT NULL,
                profissional_id INTEGER NOT NULL,
                data TEXT NOT NULL,
                hora TEXT NOT NULL,
                criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE agendamento_servico (
                agendamento_id INTEGER NOT NULL,
                servico_id INTEGER NOT NULL,
                PRIMARY KEY (agendamento_id, servico_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE admin (
                id INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                usuario TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO servico (nome, preco, duracao_minutos) VALUES ('Legado', 25.00, 45)"
        )
        conn.execute("INSERT INTO profissional (nome) VALUES ('Profissional legado')")
        conn.execute(
            """
            INSERT INTO agendamento (
                cliente_nome, cliente_telefone, servico_id, profissional_id, data, hora
            ) VALUES ('Cliente legado', '11999990000', 1, 1, '2030-01-02', '09:00')
            """
        )

    monkeypatch.setenv("POSTGRES_DB", legacy_database)
    database.init_db()
    with database.db_session() as conn:
        migrated = conn.execute(
            """
            SELECT a.profissional_nome_snapshot,
                   ags.nome_servico,
                   ags.preco_unitario,
                   ags.duracao_minutos,
                   s.descricao
            FROM agendamento AS a
            JOIN agendamento_servico AS ags ON ags.agendamento_id = a.id
            JOIN servico AS s ON s.id = ags.servico_id
            WHERE a.id = 1
            """
        ).fetchone()
        conn.execute("UPDATE servico SET nome = 'Nome atual', preco = 90, duracao_minutos = 90")
        conn.execute("UPDATE profissional SET nome = 'Nome atual' WHERE id = 1")

    assert migrated["profissional_nome_snapshot"] == "Profissional legado"
    assert migrated["nome_servico"] == "Legado"
    assert float(migrated["preco_unitario"]) == 25.0
    assert migrated["duracao_minutos"] == 45
    assert migrated["descricao"] == ""

    database.init_db()
    with database.db_session() as conn:
        preserved = conn.execute(
            """
            SELECT a.profissional_nome_snapshot, ags.nome_servico, ags.preco_unitario,
                   ags.duracao_minutos
            FROM agendamento AS a
            JOIN agendamento_servico AS ags ON ags.agendamento_id = a.id
            WHERE a.id = 1
            """
        ).fetchone()
    assert preserved["profissional_nome_snapshot"] == "Profissional legado"
    assert preserved["nome_servico"] == "Legado"
    assert float(preserved["preco_unitario"]) == 25.0
    assert preserved["duracao_minutos"] == 45
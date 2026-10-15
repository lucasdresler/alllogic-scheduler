import ipaddress
import os
import random
import re
import uuid
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

import app as app_module
from app import app
import database
import models

app.config["TESTING"] = True
app.config["WTF_CSRF_ENABLED"] = False
app.config["RATELIMIT_ENABLED"] = False
from app import limiter
limiter.enabled = False


@pytest.fixture
def client():
    with app.test_client() as test_client:
        yield test_client


def test_multi_tenant_isolamento_completo(client):
    """
    Testa o isolamento de dados de multi-tenancy:
    - Cadastro de 2 estabelecimentos distintos via /agillex
    - Isolamento de serviços por estabelecimento
    - Isolamento de profissionais por estabelecimento
    - Agendamento pela rota pública /agendar/<slug>
    - Isolamento dos agendamentos no painel /admin
    - Isolamento dos clientes no painel /admin/clientes
    """
    suffix_a = uuid.uuid4().hex[:6]
    suffix_b = uuid.uuid4().hex[:6]

    email_a = f"dono_a_{suffix_a}@salao.com"
    email_b = f"dono_b_{suffix_b}@barbearia.com"
    cnpj_a = f"11223344{random.randint(100000, 999999)}"
    cnpj_b = f"55667788{random.randint(100000, 999999)}"

    # 1. Cadastro do Estabelecimento A
    resp_a = client.post(
        "/agillex",
        data={
            "nome_responsavel": f"Responsavel A {suffix_a}",
            "nome_estabelecimento": f"Salao Alpha {suffix_a}",
            "cnpj_cpf": cnpj_a,
            "telefone": "(11) 91111-2222",
            "email": email_a,
            "senha": "senhaValida123",
            "confirmar_senha": "senhaValida123",
            "termos": "1",
            "plano": "intermediario",
        },
    )
    assert resp_a.status_code == 302

    with database.db_session() as conn:
        estab_a = database.obter_estabelecimento_por_email(conn, email_a)
        assert estab_a is not None
        id_a = estab_a["id"]
        slug_a = estab_a["slug"]
        # Verifica seed de 2 serviços iniciais
        servicos_a_iniciais = models.listar_servicos_admin(estabelecimento_id=id_a)
        assert len(servicos_a_iniciais) >= 2

    # 2. Cadastro do Estabelecimento B
    resp_b = client.post(
        "/agillex",
        data={
            "nome_responsavel": f"Responsavel B {suffix_b}",
            "nome_estabelecimento": f"Barbearia Beta {suffix_b}",
            "cnpj_cpf": cnpj_b,
            "telefone": "(11) 93333-4444",
            "email": email_b,
            "senha": "senhaValida123",
            "confirmar_senha": "senhaValida123",
            "termos": "1",
            "plano": "intermediario",
        },
    )
    assert resp_b.status_code == 302

    with database.db_session() as conn:
        estab_b = database.obter_estabelecimento_por_email(conn, email_b)
        assert estab_b is not None
        id_b = estab_b["id"]
        slug_b = estab_b["slug"]

    # 3. Cria serviço exclusivo no Estabelecimento A e outro no B
    sid_a, _ = models.criar_servico(f"Corte Especial A {suffix_a}", 60.0, 30, True, estabelecimento_id=id_a)
    sid_b, _ = models.criar_servico(f"Barba Terapia B {suffix_b}", 45.0, 30, True, estabelecimento_id=id_b)

    # Cria profissional exclusivo no Estabelecimento A e outro no B
    pid_a, _ = models.criar_profissional(f"Barbeiro A {suffix_a}", True, [sid_a], estabelecimento_id=id_a)
    pid_b, _ = models.criar_profissional(f"Barbeiro B {suffix_b}", True, [sid_b], estabelecimento_id=id_b)

    # 4. Verifica que Estabelecimento A lista apenas os seus serviços e profissionais
    servs_a = models.listar_servicos(apenas_ativos=True, estabelecimento_id=id_a)
    serv_ids_a = {s["id"] for s in servs_a}
    assert sid_a in serv_ids_a
    assert sid_b not in serv_ids_a

    profs_a = models.listar_profissionais(apenas_ativos=True, estabelecimento_id=id_a)
    prof_ids_a = {p["id"] for p in profs_a}
    assert pid_a in prof_ids_a
    assert pid_b not in prof_ids_a

    # E o Estabelecimento B lista apenas os seus
    servs_b = models.listar_servicos(apenas_ativos=True, estabelecimento_id=id_b)
    serv_ids_b = {s["id"] for s in servs_b}
    assert sid_b in serv_ids_b
    assert sid_a not in serv_ids_b

    profs_b = models.listar_profissionais(apenas_ativos=True, estabelecimento_id=id_b)
    prof_ids_b = {p["id"] for p in profs_b}
    assert pid_b in prof_ids_b
    assert pid_a not in prof_ids_b

    # 5. Acesso às páginas públicas por slug
    resp_page_a = client.get(f"/agendar/{slug_a}")
    assert resp_page_a.status_code == 200
    html_a = resp_page_a.data.decode("utf-8")
    assert f"Salao Alpha {suffix_a}" in html_a
    assert f"Corte Especial A {suffix_a}" in html_a
    assert f"Barba Terapia B {suffix_b}" not in html_a

    resp_page_b = client.get(f"/agendar/{slug_b}")
    assert resp_page_b.status_code == 200
    html_b = resp_page_b.data.decode("utf-8")
    assert f"Barbearia Beta {suffix_b}" in html_b
    assert f"Barba Terapia B {suffix_b}" in html_b
    assert f"Corte Especial A {suffix_a}" not in html_b

    # Rota curta /<slug>
    resp_curta = client.get(f"/{slug_a}")
    assert resp_curta.status_code == 200
    assert f"Salao Alpha {suffix_a}" in resp_curta.data.decode("utf-8")

    # 6. Agendamento para o Estabelecimento A
    dias_a = models.dias_funcionamento()
    from datetime import date, timedelta
    d = date.today() + timedelta(days=2)
    while d.weekday() not in dias_a:
        d += timedelta(days=1)
    data_str = d.strftime("%Y-%m-%d")

    # Cria grade de horários para o profissional A
    with database.db_session() as conn:
        for dia_sem in range(7):
            conn.execute(
                """
                INSERT INTO profissional_disponibilidade (profissional_id, dia_semana, horario_entrada, horario_saida, ativo)
                VALUES (%s, %s, '09:00', '18:00', TRUE)
                ON CONFLICT (profissional_id, dia_semana) DO UPDATE
                SET horario_entrada = EXCLUDED.horario_entrada, horario_saida = EXCLUDED.horario_saida, ativo = EXCLUDED.ativo
                """,
                (pid_a, dia_sem),
            )
            conn.execute(
                """
                INSERT INTO profissional_disponibilidade (profissional_id, dia_semana, horario_entrada, horario_saida, ativo)
                VALUES (%s, %s, '09:00', '18:00', TRUE)
                ON CONFLICT (profissional_id, dia_semana) DO UPDATE
                SET horario_entrada = EXCLUDED.horario_entrada, horario_saida = EXCLUDED.horario_saida, ativo = EXCLUDED.ativo
                """,
                (pid_b, dia_sem),
            )

    horarios_a = models.horarios_disponiveis(pid_a, data_str, [sid_a])
    assert len(horarios_a) > 0

    ag_id_a, erro_a = models.criar_agendamento(
        f"Cliente Alpha {suffix_a}", "(11) 91111-9999", [sid_a], pid_a, data_str, horarios_a[0], estabelecimento_id=id_a
    )
    assert erro_a is None
    assert ag_id_a is not None

    # Agendamento para o Estabelecimento B
    horarios_b = models.horarios_disponiveis(pid_b, data_str, [sid_b])
    assert len(horarios_b) > 0
    ag_id_b, erro_b = models.criar_agendamento(
        f"Cliente Beta {suffix_b}", "(11) 92222-9999", [sid_b], pid_b, data_str, horarios_b[0], estabelecimento_id=id_b
    )
    assert erro_b is None
    assert ag_id_b is not None

    # 7. Verifica isolamento no Painel Admin do Estabelecimento A
    with client.session_transaction() as sess:
        sess["admin_logado"] = True
        sess["admin_usuario"] = f"admin_{suffix_a}"
        sess["estabelecimento_id"] = id_a

    resp_dash_a = client.get(f"/admin?aba=hoje&data={data_str}")
    assert resp_dash_a.status_code == 200
    html_dash_a = resp_dash_a.data.decode("utf-8")
    assert f"Cliente Alpha {suffix_a}" in html_dash_a
    assert f"Cliente Beta {suffix_b}" not in html_dash_a
    # Link público no dashboard
    assert f"/agendar/{slug_a}" in html_dash_a

    # 8. Verifica isolamento de Clientes no Estabelecimento A
    resp_cli_a = client.get("/admin/clientes")
    assert resp_cli_a.status_code == 200
    html_cli_a = resp_cli_a.data.decode("utf-8")
    assert f"Cliente Alpha {suffix_a}" in html_cli_a
    assert f"Cliente Beta {suffix_b}" not in html_cli_a

    # 9. Troca sessão para Estabelecimento B e verifica isolamento
    with client.session_transaction() as sess:
        sess["admin_logado"] = True
        sess["admin_usuario"] = f"admin_{suffix_b}"
        sess["estabelecimento_id"] = id_b

    resp_dash_b = client.get(f"/admin?aba=hoje&data={data_str}")
    assert resp_dash_b.status_code == 200
    html_dash_b = resp_dash_b.data.decode("utf-8")
    assert f"Cliente Beta {suffix_b}" in html_dash_b
    assert f"Cliente Alpha {suffix_a}" not in html_dash_b
    assert f"/agendar/{slug_b}" in html_dash_b

    resp_cli_b = client.get("/admin/clientes")
    assert resp_cli_b.status_code == 200
    html_cli_b = resp_cli_b.data.decode("utf-8")
    assert f"Cliente Beta {suffix_b}" in html_cli_b
    assert f"Cliente Alpha {suffix_a}" not in html_cli_b

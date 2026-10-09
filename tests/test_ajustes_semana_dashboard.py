import ipaddress
import os
import re
import uuid
import pytest
from datetime import date, timedelta

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


def _obter_ou_criar_profissional_e_servico():
    with database.db_session() as conn:
        p = conn.execute("SELECT id FROM profissional WHERE ativo = TRUE LIMIT 1").fetchone()
        if not p:
            p_id = conn.execute(
                "INSERT INTO profissional (nome, ativo) VALUES ('Prof Teste Semana', TRUE) RETURNING id"
            ).fetchone()["id"]
        else:
            p_id = p["id"]

        s = conn.execute("SELECT id, preco FROM servico WHERE ativo = TRUE LIMIT 1").fetchone()
        if not s:
            s_row = conn.execute(
                "INSERT INTO servico (nome, preco, duracao_minutos, ativo) VALUES ('Serv Teste', 50.0, 30, TRUE) RETURNING id, preco"
            ).fetchone()
            s_id = s_row["id"]
            s_preco = s_row["preco"]
        else:
            s_id = s["id"]
            s_preco = s["preco"]

        return p_id, s_id, float(s_preco)


def test_ordem_semanal_domingo_a_sabado(client, logged_admin):
    """
    Verifica que na visualização semanal (aba=semana):
    1. O início da semana é Domingo.
    2. O fim da semana é Sábado.
    3. As datas de navegação anterior/próxima avançam/recuam exatamente 7 dias.
    """
    # Testar com uma quarta-feira: 2026-10-07
    # Domingo deve ser 2026-10-04, Sábado deve ser 2026-10-10
    res = client.get("/admin?aba=semana&data=2026-10-07")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    assert "04/10/2026 a 10/10/2026" in html
    assert "data=2026-09-27" in html  # semana anterior (domingo anterior)
    assert "data=2026-10-11" in html  # próxima semana (próximo domingo)


def test_ordem_semanal_partindo_de_domingo_e_sabado(client, logged_admin):
    """
    Garante que se a data de referência for o próprio Domingo ou o próprio Sábado,
    a semana calculada é sempre a mesma: Domingo a Sábado.
    """
    # 2026-10-04 é domingo
    res_dom = client.get("/admin?aba=semana&data=2026-10-04")
    assert res_dom.status_code == 200
    html_dom = res_dom.get_data(as_text=True)
    assert "04/10/2026 a 10/10/2026" in html_dom

    # 2026-10-10 é sábado
    res_sab = client.get("/admin?aba=semana&data=2026-10-10")
    assert res_sab.status_code == 200
    html_sab = res_sab.get_data(as_text=True)
    assert "04/10/2026 a 10/10/2026" in html_sab

    # 2026-10-05 é segunda-feira
    res_seg = client.get("/admin?aba=semana&data=2026-10-05")
    assert res_seg.status_code == 200
    html_seg = res_seg.get_data(as_text=True)
    assert "04/10/2026 a 10/10/2026" in html_seg


def test_navegacao_entre_semanas(client, logged_admin):
    """
    Testa a navegação para semana anterior e próxima semana mantendo domingo a sábado.
    """
    # Navega para semana anterior (27/09 a 03/10)
    res_ant = client.get("/admin?aba=semana&data=2026-09-27")
    assert res_ant.status_code == 200
    html_ant = res_ant.get_data(as_text=True)
    assert "27/09/2026 a 03/10/2026" in html_ant
    assert "data=2026-09-20" in html_ant
    assert "data=2026-10-04" in html_ant

    # Navega para próxima semana (11/10 a 17/10)
    res_prox = client.get("/admin?aba=semana&data=2026-10-11")
    assert res_prox.status_code == 200
    html_prox = res_prox.get_data(as_text=True)
    assert "11/10/2026 a 17/10/2026" in html_prox
    assert "data=2026-10-04" in html_prox
    assert "data=2026-10-18" in html_prox


def test_agendamentos_no_domingo_e_sabado_na_semana(client, logged_admin):
    """
    Cria agendamentos no domingo (primeiro dia) e no sábado (último dia da semana)
    e confirma exibição correta e cabeçalhos com dias da semana.
    """
    p_id, s_id, preco = _obter_ou_criar_profissional_e_servico()

    data_dom = "2026-10-04"  # Domingo
    data_sab = "2026-10-10"  # Sábado
    data_fora = "2026-10-11"  # Domingo da próxima semana

    c_dom = f"Cliente Dom {uuid.uuid4().hex[:6]}"
    c_sab = f"Cliente Sab {uuid.uuid4().hex[:6]}"
    c_fora = f"Cliente Fora {uuid.uuid4().hex[:6]}"

    # Inserir agendamentos
    with database.db_session() as conn:
        ag_dom = conn.execute(
            """
            INSERT INTO agendamento (cliente_nome, cliente_telefone, profissional_id, servico_id, data, hora, status, profissional_nome_snapshot)
            VALUES (%s, '11999990001', %s, %s, %s, '10:00', 'agendado', 'Prof Snapshot') RETURNING id
            """,
            (c_dom, p_id, s_id, data_dom),
        ).fetchone()
        conn.execute(
            "INSERT INTO agendamento_servico (agendamento_id, servico_id, nome_servico, preco_unitario, duracao_minutos) VALUES (%s, %s, 'Corte', %s, 30)",
            (ag_dom["id"], s_id, preco),
        )

        ag_sab = conn.execute(
            """
            INSERT INTO agendamento (cliente_nome, cliente_telefone, profissional_id, servico_id, data, hora, status, profissional_nome_snapshot)
            VALUES (%s, '11999990002', %s, %s, %s, '11:00', 'agendado', 'Prof Snapshot') RETURNING id
            """,
            (c_sab, p_id, s_id, data_sab),
        ).fetchone()
        conn.execute(
            "INSERT INTO agendamento_servico (agendamento_id, servico_id, nome_servico, preco_unitario, duracao_minutos) VALUES (%s, %s, 'Corte', %s, 30)",
            (ag_sab["id"], s_id, preco),
        )

        ag_fora = conn.execute(
            """
            INSERT INTO agendamento (cliente_nome, cliente_telefone, profissional_id, servico_id, data, hora, status, profissional_nome_snapshot)
            VALUES (%s, '11999990003', %s, %s, %s, '12:00', 'agendado', 'Prof Snapshot') RETURNING id
            """,
            (c_fora, p_id, s_id, data_fora),
        ).fetchone()
        conn.execute(
            "INSERT INTO agendamento_servico (agendamento_id, servico_id, nome_servico, preco_unitario, duracao_minutos) VALUES (%s, %s, 'Corte', %s, 30)",
            (ag_fora["id"], s_id, preco),
        )

    # Buscar semana de 2026-10-07
    res = client.get("/admin?aba=semana&data=2026-10-07")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Domingo e Sábado devem estar presentes
    assert c_dom in html
    assert c_sab in html
    # Domingo da próxima semana não deve estar presente nesta semana
    assert c_fora not in html

    # Verificar cabeçalhos de agrupamento com nome do dia
    assert "Domingo — 04/10/2026" in html
    assert "Sábado — 10/10/2026" in html


def test_nomenclatura_valor_dos_agendamentos_no_dashboard(client, logged_admin):
    """
    Verifica que:
    1. O termo 'Receita' foi substituído por 'Valor dos agendamentos'.
    2. 'Receita do período' foi substituído por 'Valor dos agendamentos do período' (nas abas semana e mes).
    3. 'Receita prevista' foi substituído por 'Valor dos agendamentos previstos' (na aba hoje).
    4. O valor numérico e formatação R$ permanecem íntegros.
    """
    # Aba hoje
    res_hoje = client.get("/admin?aba=hoje")
    assert res_hoje.status_code == 200
    html_hoje = res_hoje.get_data(as_text=True)
    assert "Receita prevista" not in html_hoje
    assert "Receita do período" not in html_hoje
    assert "Receita" not in html_hoje
    assert "Valor dos agendamentos previstos" in html_hoje

    # Aba semana
    res_semana = client.get("/admin?aba=semana&data=2026-10-07")
    assert res_semana.status_code == 200
    html_semana = res_semana.get_data(as_text=True)
    assert "Receita prevista" not in html_semana
    assert "Receita do período" not in html_semana
    assert "Receita" not in html_semana
    assert "Valor dos agendamentos do período" in html_semana

    # Aba mes
    res_mes = client.get("/admin?aba=mes&data=2026-10-07")
    assert res_mes.status_code == 200
    html_mes = res_mes.get_data(as_text=True)
    assert "Receita prevista" not in html_mes
    assert "Receita do período" not in html_mes
    assert "Receita" not in html_mes
    assert "Valor dos agendamentos do período" in html_mes


def test_ordem_visual_estrita_dos_dias_na_semana(client, logged_admin):
    """
    Valida a ordem visual REAL renderizada no HTML da Agenda semanal:
    Domingo -> Segunda-feira -> Terça-feira -> Quarta-feira -> Quinta-feira -> Sexta-feira -> Sábado.
    Garante que os 7 dias aparecem mesmo sem agendamentos.
    """
    # Semana de 15/11/2026 a 21/11/2026 (18/11/2026 é quarta-feira)
    res = client.get("/admin?aba=semana&data=2026-11-18")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    dias_renderizados = re.findall(r'<div class="dia-agrupador">\s*(.*?)\s*</div>', html)
    esperados = [
        "Domingo — 15/11/2026",
        "Segunda-feira — 16/11/2026",
        "Terça-feira — 17/11/2026",
        "Quarta-feira — 18/11/2026",
        "Quinta-feira — 19/11/2026",
        "Sexta-feira — 20/11/2026",
        "Sábado — 21/11/2026",
    ]
    assert dias_renderizados == esperados, f"Ordem renderizada incorreta: {dias_renderizados}"
    assert html.count("Nenhum agendamento para este dia.") >= 7


def test_ordem_visual_com_agendamentos_esparsos(client, logged_admin):
    """
    Garante que quando há agendamentos apenas em dias intermediários (ex: terça e sexta),
    a semana ainda inicia visualmente no Domingo e termina no Sábado.
    """
    p_id, s_id, preco = _obter_ou_criar_profissional_e_servico()
    data_terca = "2026-12-08"   # Terça
    data_sexta = "2026-12-11"   # Sexta
    # Semana: 06/12/2026 (Dom) a 12/12/2026 (Sáb)

    c_terca = f"Cliente Ter {uuid.uuid4().hex[:6]}"
    c_sexta = f"Cliente Sex {uuid.uuid4().hex[:6]}"

    with database.db_session() as conn:
        ag_t = conn.execute(
            """
            INSERT INTO agendamento (cliente_nome, cliente_telefone, profissional_id, servico_id, data, hora, status, profissional_nome_snapshot)
            VALUES (%s, '11999990010', %s, %s, %s, '14:00', 'agendado', 'Prof Snapshot') RETURNING id
            """,
            (c_terca, p_id, s_id, data_terca),
        ).fetchone()
        conn.execute(
            "INSERT INTO agendamento_servico (agendamento_id, servico_id, nome_servico, preco_unitario, duracao_minutos) VALUES (%s, %s, 'Corte', %s, 30)",
            (ag_t["id"], s_id, preco),
        )

        ag_s = conn.execute(
            """
            INSERT INTO agendamento (cliente_nome, cliente_telefone, profissional_id, servico_id, data, hora, status, profissional_nome_snapshot)
            VALUES (%s, '11999990011', %s, %s, %s, '16:00', 'agendado', 'Prof Snapshot') RETURNING id
            """,
            (c_sexta, p_id, s_id, data_sexta),
        ).fetchone()
        conn.execute(
            "INSERT INTO agendamento_servico (agendamento_id, servico_id, nome_servico, preco_unitario, duracao_minutos) VALUES (%s, %s, 'Corte', %s, 30)",
            (ag_s["id"], s_id, preco),
        )

    res = client.get("/admin?aba=semana&data=2026-12-09")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    dias_renderizados = re.findall(r'<div class="dia-agrupador">\s*(.*?)\s*</div>', html)
    esperados = [
        "Domingo — 06/12/2026",
        "Segunda-feira — 07/12/2026",
        "Terça-feira — 08/12/2026",
        "Quarta-feira — 09/12/2026",
        "Quinta-feira — 10/12/2026",
        "Sexta-feira — 11/12/2026",
        "Sábado — 12/12/2026",
    ]
    assert dias_renderizados == esperados
    assert c_terca in html
    assert c_sexta in html


def test_ordem_dias_em_configuracoes_e_profissional(client, logged_admin):
    """
    Garante que as telas de Configurações da agenda e Edição de Profissional
    apresentem os dias da semana na ordem Domingo -> Sábado.
    """
    # 1. Configurações da agenda
    res_conf = client.get("/admin/configuracoes")
    assert res_conf.status_code == 200
    html_conf = res_conf.get_data(as_text=True)
    dias_conf = re.findall(
        r'<label class="checkbox-row">\s*<input [^>]*name="dias_funcionamento"[^>]*>\s*(.*?)\s*</label>',
        html_conf,
    )
    esperados_dias = [
        "Domingo",
        "Segunda-feira",
        "Terça-feira",
        "Quarta-feira",
        "Quinta-feira",
        "Sexta-feira",
        "Sábado",
    ]
    assert dias_conf == esperados_dias, f"Ordem inesperada em configuracoes: {dias_conf}"

    # 2. Edição de profissional
    p_id, _, _ = _obter_ou_criar_profissional_e_servico()
    res_prof = client.get(f"/admin/profissionais/{p_id}/editar")
    assert res_prof.status_code == 200
    html_prof = res_prof.get_data(as_text=True)
    dias_prof = re.findall(
        r'<label class="checkbox-row dia-label">.*?<span>(.*?)</span>',
        html_prof,
        re.DOTALL,
    )
    assert dias_prof == esperados_dias, f"Ordem inesperada em profissional: {dias_prof}"


def test_cabecalhos_cache_control_admin(client, logged_admin):
    """
    Verifica que rotas administrativas recebem Cache-Control: no-store, no-cache, must-revalidate,
    enquanto rotas públicas e arquivos estáticos preservam seus cabeçalhos originais.
    """
    res_admin = client.get("/admin?aba=semana")
    assert "no-store" in res_admin.headers.get("Cache-Control", "")
    assert "no-cache" in res_admin.headers.get("Cache-Control", "")

    res_pub = client.get("/")
    assert "no-store" not in res_pub.headers.get("Cache-Control", "")

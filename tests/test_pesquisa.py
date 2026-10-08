import ipaddress
import os
import re
import uuid
from datetime import date, datetime, timedelta

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


@pytest.fixture(autouse=True)
def setup_estabelecimento_padrao():
    with database.db_session() as conn:
        database.atualizar_configuracoes(conn, {
            "horario_abertura": "08:00",
            "horario_fechamento": "19:00",
            "dias_funcionamento": "0,1,2,3,4,5,6",
            "dias_antecedencia_agendamento": "30",
            "intervalo_slot_minutos": "30",
        })
    models._limpar_cache_config()


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


def _proxima_data(dias_a_frente=2):
    hoje = datetime.now().date()
    return (hoje + timedelta(days=dias_a_frente)).strftime("%Y-%m-%d")


def _criar_profissional_e_servico(nome_prof="Profissional Teste", nome_servico="Corte Teste", duracao=30, preco=50.0):
    with database.db_session() as conn:
        cur_p = conn.execute(
            "INSERT INTO profissional (nome, ativo) VALUES (%s, TRUE) RETURNING id",
            (f"{nome_prof}_{uuid.uuid4().hex[:6]}",),
        )
        prof_id = cur_p.fetchone()["id"]

        cur_s = conn.execute(
            "INSERT INTO servico (nome, preco, duracao_minutos, ativo) VALUES (%s, %s, %s, TRUE) RETURNING id",
            (f"{nome_servico}_{uuid.uuid4().hex[:6]}", preco, duracao),
        )
        serv_id = cur_s.fetchone()["id"]

        conn.execute(
            "INSERT INTO profissional_servico (profissional_id, servico_id) VALUES (%s, %s)",
            (prof_id, serv_id),
        )
    return prof_id, serv_id


def test_autenticacao_da_rota(client):
    """Garante que a pesquisa de agendamentos respeita autenticação administrativa."""
    # Acesso não autenticado a /admin?aba=pesquisa deve redirecionar para /admin/login
    resp = client.get("/admin?aba=pesquisa")
    assert resp.status_code == 302
    assert "/admin/login" in resp.headers["Location"]

    # Acesso não autenticado a /admin/pesquisa deve redirecionar para /admin/login
    resp_rota = client.get("/admin/pesquisa")
    assert resp_rota.status_code == 302
    assert "/admin/login" in resp_rota.headers["Location"]


def test_pesquisa_por_nome(client, logged_admin):
    """Permite pesquisar agendamentos por nome do cliente (inclusive busca parcial e case-insensitive)."""
    prof_id, serv_id = _criar_profissional_e_servico()
    data_ag = _proxima_data(4)
    prefixo = uuid.uuid4().hex[:6]
    nome_alvo = f"João da Silva {prefixo}"
    nome_outro = f"Maria Santos {prefixo}"

    id1, _ = models.criar_agendamento(nome_alvo, "(11) 91111-0001", [serv_id], prof_id, data_ag, "09:00")
    id2, _ = models.criar_agendamento(nome_outro, "(11) 91111-0002", [serv_id], prof_id, data_ag, "10:00")
    assert id1 and id2

    # Busca exata por parte do nome
    resp = client.get(f"/admin?aba=pesquisa&cliente={nome_alvo}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert nome_alvo in html
    assert nome_outro not in html

    # Busca case-insensitive e parcial ("joão")
    resp_lower = client.get(f"/admin?aba=pesquisa&cliente=joão da silva {prefixo}")
    assert resp_lower.status_code == 200
    html_lower = resp_lower.get_data(as_text=True)
    assert nome_alvo in html_lower
    assert nome_outro not in html_lower


def test_pesquisa_por_telefone(client, logged_admin):
    """Permite pesquisar agendamentos por telefone (com ou sem máscara/formatação)."""
    prof_id, serv_id = _criar_profissional_e_servico()
    data_ag = _proxima_data(5)
    suffix = uuid.uuid4().hex[:4]
    tel_carlos = f"(11) 98765-{suffix}"
    tel_carlos_digitos = f"1198765{suffix}"
    tel_ana = f"(21) 91234-{suffix}"

    id1, _ = models.criar_agendamento("Carlos Teste Tel", tel_carlos, [serv_id], prof_id, data_ag, "11:00")
    id2, _ = models.criar_agendamento("Ana Teste Tel", tel_ana, [serv_id], prof_id, data_ag, "12:00")
    assert id1 and id2

    # Busca informando apenas os dígitos (sem parênteses nem traço)
    resp_digitos = client.get(f"/admin?aba=pesquisa&telefone={tel_carlos_digitos}")
    assert resp_digitos.status_code == 200
    html_dig = resp_digitos.get_data(as_text=True)
    assert "Carlos Teste Tel" in html_dig
    assert "Ana Teste Tel" not in html_dig

    # Busca informando parte formatada
    resp_fmt = client.get(f"/admin?aba=pesquisa&telefone=(21) 91234")
    assert resp_fmt.status_code == 200
    html_fmt = resp_fmt.get_data(as_text=True)
    assert "Ana Teste Tel" in html_fmt
    assert "Carlos Teste Tel" not in html_fmt


def test_filtro_por_profissional(client, logged_admin):
    """Permite filtrar agendamentos por profissional específico e por todos."""
    prof1_id, serv_id = _criar_profissional_e_servico(nome_prof="Profissional Alfa")
    prof2_id, _ = _criar_profissional_e_servico(nome_prof="Profissional Beta")

    # Vincula o mesmo serviço ao profissional 2
    with database.db_session() as conn:
        conn.execute(
            "INSERT INTO profissional_servico (profissional_id, servico_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (prof2_id, serv_id),
        )

    data_ag = _proxima_data(6)
    tag = uuid.uuid4().hex[:6]
    cliente_p1 = f"Cliente Prof1 {tag}"
    cliente_p2 = f"Cliente Prof2 {tag}"

    id1, _ = models.criar_agendamento(cliente_p1, "(11) 93333-0001", [serv_id], prof1_id, data_ag, "14:00")
    id2, _ = models.criar_agendamento(cliente_p2, "(11) 93333-0002", [serv_id], prof2_id, data_ag, "14:00")
    assert id1 and id2

    # Filtrar apenas Profissional 1
    resp_p1 = client.get(f"/admin?aba=pesquisa&profissional_id={prof1_id}")
    assert resp_p1.status_code == 200
    html_p1 = resp_p1.get_data(as_text=True)
    assert cliente_p1 in html_p1
    assert cliente_p2 not in html_p1

    # Filtrar apenas Profissional 2
    resp_p2 = client.get(f"/admin?aba=pesquisa&profissional_id={prof2_id}")
    assert resp_p2.status_code == 200
    html_p2 = resp_p2.get_data(as_text=True)
    assert cliente_p2 in html_p2
    assert cliente_p1 not in html_p2

    # Filtrar "Todos os profissionais" (vazio)
    resp_todos = client.get("/admin?aba=pesquisa&profissional_id=")
    assert resp_todos.status_code == 200
    html_todos = resp_todos.get_data(as_text=True)
    assert cliente_p1 in html_todos
    assert cliente_p2 in html_todos


def test_filtro_por_status(client, logged_admin):
    """Permite filtrar agendamentos por status (agendado, realizado, nao_compareceu, cancelado)."""
    prof_id, serv_id = _criar_profissional_e_servico()
    data_passada = (datetime.now().date() - timedelta(days=2)).strftime("%Y-%m-%d")
    data_futura = _proxima_data(7)
    tag = uuid.uuid4().hex[:6]

    cli_agendado = f"Cliente Agendado {tag}"
    cli_realizado = f"Cliente Realizado {tag}"
    cli_falta = f"Cliente Falta {tag}"
    cli_cancelado = f"Cliente Cancelado {tag}"

    # Agendado
    id_ag, _ = models.criar_agendamento(cli_agendado, "(11) 94444-0001", [serv_id], prof_id, data_futura, "09:00")

    # Inserções diretas no banco para status realizados no passado e cancelado
    with database.db_session() as conn:
        cur_r = conn.execute(
            """
            INSERT INTO agendamento (cliente_nome, cliente_telefone, servico_id, profissional_id, data, hora, status, profissional_nome_snapshot)
            VALUES (%s, '(11) 94444-0002', %s, %s, %s, '10:00', 'realizado', 'Profissional')
            RETURNING id
            """,
            (cli_realizado, serv_id, prof_id, data_passada),
        )
        id_realizado = cur_r.fetchone()["id"]
        conn.execute(
            "INSERT INTO agendamento_servico (agendamento_id, servico_id, nome_servico, preco_unitario, duracao_minutos) VALUES (%s, %s, 'Corte', 50.0, 30)",
            (id_realizado, serv_id),
        )

        cur_f = conn.execute(
            """
            INSERT INTO agendamento (cliente_nome, cliente_telefone, servico_id, profissional_id, data, hora, status, profissional_nome_snapshot)
            VALUES (%s, '(11) 94444-0003', %s, %s, %s, '11:00', 'nao_compareceu', 'Profissional')
            RETURNING id
            """,
            (cli_falta, serv_id, prof_id, data_passada),
        )
        id_falta = cur_f.fetchone()["id"]
        conn.execute(
            "INSERT INTO agendamento_servico (agendamento_id, servico_id, nome_servico, preco_unitario, duracao_minutos) VALUES (%s, %s, 'Corte', 50.0, 30)",
            (id_falta, serv_id),
        )

        cur_c = conn.execute(
            """
            INSERT INTO agendamento (cliente_nome, cliente_telefone, servico_id, profissional_id, data, hora, status, profissional_nome_snapshot)
            VALUES (%s, '(11) 94444-0004', %s, %s, %s, '12:00', 'cancelado', 'Profissional')
            RETURNING id
            """,
            (cli_cancelado, serv_id, prof_id, data_futura),
        )
        id_cancelado = cur_c.fetchone()["id"]
        conn.execute(
            "INSERT INTO agendamento_servico (agendamento_id, servico_id, nome_servico, preco_unitario, duracao_minutos) VALUES (%s, %s, 'Corte', 50.0, 30)",
            (id_cancelado, serv_id),
        )

    # Filtro por cancelado
    resp_canc = client.get("/admin?aba=pesquisa&status=cancelado")
    assert resp_canc.status_code == 200
    html_canc = resp_canc.get_data(as_text=True)
    assert cli_cancelado in html_canc
    assert cli_agendado not in html_canc
    assert cli_realizado not in html_canc
    assert cli_falta not in html_canc

    # Filtro por realizado
    resp_real = client.get("/admin?aba=pesquisa&status=realizado")
    assert resp_real.status_code == 200
    html_real = resp_real.get_data(as_text=True)
    assert cli_realizado in html_real
    assert cli_agendado not in html_real
    assert cli_cancelado not in html_real

    # Filtro por nao_compareceu
    resp_falta = client.get("/admin?aba=pesquisa&status=nao_compareceu")
    assert resp_falta.status_code == 200
    html_falta = resp_falta.get_data(as_text=True)
    assert cli_falta in html_falta
    assert cli_agendado not in html_falta

    # Filtro por agendado
    resp_ag = client.get("/admin?aba=pesquisa&status=agendado")
    assert resp_ag.status_code == 200
    html_ag = resp_ag.get_data(as_text=True)
    assert cli_agendado in html_ag
    assert cli_cancelado not in html_ag


def test_filtro_por_data_inicial_e_final(client, logged_admin):
    """Permite filtrar por data inicial, data final e período fechado."""
    prof_id, serv_id = _criar_profissional_e_servico()
    hoje = datetime.now().date()
    d1 = (hoje + timedelta(days=2)).strftime("%Y-%m-%d")
    d2 = (hoje + timedelta(days=5)).strftime("%Y-%m-%d")
    d3 = (hoje + timedelta(days=8)).strftime("%Y-%m-%d")
    tag = uuid.uuid4().hex[:6]

    cli_d1 = f"Cliente Dia1 {tag}"
    cli_d2 = f"Cliente Dia2 {tag}"
    cli_d3 = f"Cliente Dia3 {tag}"

    models.criar_agendamento(cli_d1, "(11) 95555-0001", [serv_id], prof_id, d1, "10:00")
    models.criar_agendamento(cli_d2, "(11) 95555-0002", [serv_id], prof_id, d2, "10:00")
    models.criar_agendamento(cli_d3, "(11) 95555-0003", [serv_id], prof_id, d3, "10:00")

    # Apenas data_inicio = d2 (deve trazer d2 e d3)
    resp_ini = client.get(f"/admin?aba=pesquisa&data_inicio={d2}")
    assert resp_ini.status_code == 200
    html_ini = resp_ini.get_data(as_text=True)
    assert cli_d2 in html_ini
    assert cli_d3 in html_ini
    assert cli_d1 not in html_ini

    # Apenas data_fim = d2 (deve trazer d1 e d2)
    resp_fim = client.get(f"/admin?aba=pesquisa&data_fim={d2}")
    assert resp_fim.status_code == 200
    html_fim = resp_fim.get_data(as_text=True)
    assert cli_d1 in html_fim
    assert cli_d2 in html_fim
    assert cli_d3 not in html_fim

    # Período fechado: d2 até d2 (apenas d2)
    resp_periodo = client.get(f"/admin?aba=pesquisa&data_inicio={d2}&data_fim={d2}")
    assert resp_periodo.status_code == 200
    html_per = resp_periodo.get_data(as_text=True)
    assert cli_d2 in html_per
    assert cli_d1 not in html_per
    assert cli_d3 not in html_per


def test_combinacao_de_filtros(client, logged_admin):
    """Verifica que múltiplos filtros podem ser combinados simultaneamente."""
    prof1_id, serv_id = _criar_profissional_e_servico(nome_prof="Profissional 1")
    prof2_id, _ = _criar_profissional_e_servico(nome_prof="Profissional 2")
    with database.db_session() as conn:
        conn.execute(
            "INSERT INTO profissional_servico (profissional_id, servico_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (prof2_id, serv_id),
        )

    d1 = _proxima_data(3)
    d2 = _proxima_data(6)
    tag = uuid.uuid4().hex[:6]

    cli_alvo = f"João Combinado {tag}"
    cli_outro1 = f"João Combinado {tag}" # mesmo nome, mas prof diferente
    cli_outro2 = f"Outro Cliente {tag}"

    id_alvo, _ = models.criar_agendamento(cli_alvo, "(11) 96666-0001", [serv_id], prof1_id, d1, "10:00")
    id_outro1, _ = models.criar_agendamento(cli_outro1, "(11) 96666-0002", [serv_id], prof2_id, d1, "11:00")
    id_outro2, _ = models.criar_agendamento(cli_outro2, "(11) 96666-0003", [serv_id], prof1_id, d2, "10:00")

    # Cancela o agendamento alvo para testar filtro por status cancelado combinado
    with database.db_session() as conn:
        conn.execute("UPDATE agendamento SET status = 'cancelado' WHERE id = %s", (id_alvo,))

    # Combinação: Cliente=João, Status=cancelado, Profissional=prof1_id, Data=d1
    url = f"/admin?aba=pesquisa&cliente=João Combinado {tag}&status=cancelado&profissional_id={prof1_id}&data_inicio={d1}&data_fim={d1}"
    resp = client.get(url)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Somente id_alvo satisfaz todos os critérios combinados
    assert cli_alvo in html
    assert "(11) 96666-0001" in html
    assert "(11) 96666-0002" not in html
    assert "(11) 96666-0003" not in html


def test_ausencia_de_resultados(client, logged_admin):
    """Exibe mensagem clara quando a pesquisa não encontra resultados para os filtros informados."""
    resp = client.get("/admin?aba=pesquisa&cliente=NomeNaoExistenteAbsoluto999999999")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Nenhum agendamento encontrado." in html
    assert "Agendamentos encontrados" in html
    assert "<span>0</span>" in html


def test_limpeza_dos_filtros(client, logged_admin):
    """Permite limpar filtros e retornar ao estado sem parâmetros de pesquisa."""
    resp = client.get("/admin?aba=pesquisa")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'id="btn-limpar-filtros"' in html
    assert 'href="/admin?aba=pesquisa"' in html
    assert 'value="" placeholder="Nome do cliente"' in html or 'id="filtro-cliente" name="cliente" value=""' in html


def test_preservacao_filtros_nas_acoes(client, logged_admin):
    """Garante que as ações (cancelar, status, reagendar) preservam os filtros de pesquisa após execução."""
    prof_id, serv_id = _criar_profissional_e_servico()
    data_futura = _proxima_data(4)
    data_passada = (datetime.now().date() - timedelta(days=1)).strftime("%Y-%m-%d")
    tag = uuid.uuid4().hex[:6]

    cli_nome = f"Cliente Acao {tag}"
    cli_tel = f"(11) 97777-{tag[:4]}"

    ag_futuro_id, _ = models.criar_agendamento(cli_nome, cli_tel, [serv_id], prof_id, data_futura, "15:00")

    with database.db_session() as conn:
        cur = conn.execute(
            """
            INSERT INTO agendamento (cliente_nome, cliente_telefone, servico_id, profissional_id, data, hora, status, profissional_nome_snapshot)
            VALUES (%s, %s, %s, %s, %s, '10:00', 'agendado', 'Profissional')
            RETURNING id
            """,
            (cli_nome, cli_tel, serv_id, prof_id, data_passada),
        )
        ag_passado_id = cur.fetchone()["id"]
        conn.execute(
            "INSERT INTO agendamento_servico (agendamento_id, servico_id, nome_servico, preco_unitario, duracao_minutos) VALUES (%s, %s, 'Corte', 50.0, 30)",
            (ag_passado_id, serv_id),
        )

    token = _csrf_token(client, "/admin?aba=pesquisa")

    # 1. Ação de marcar como Realizado deve preservar filtros
    resp_real = client.post(
        f"/admin/agendamento/{ag_passado_id}/status",
        data={
            "csrf_token": token,
            "status": "realizado",
            "aba": "pesquisa",
            "cliente": cli_nome,
            "telefone": cli_tel,
            "filtro_status": "agendado",
            "data_inicio": data_passada,
            "data_fim": data_passada,
        },
    )
    assert resp_real.status_code == 302
    loc = resp_real.headers["Location"]
    assert "aba=pesquisa" in loc
    assert f"cliente=Cliente+Acao+{tag}" in loc or f"cliente={cli_nome}" in loc
    assert "sucesso=" in loc

    # 2. Ação de Cancelar deve preservar filtros
    token = _csrf_token(client, "/admin?aba=pesquisa")
    resp_canc = client.post(
        f"/admin/agendamento/{ag_futuro_id}/cancelar",
        data={
            "csrf_token": token,
            "aba": "pesquisa",
            "cliente": cli_nome,
            "telefone": cli_tel,
            "filtro_status": "agendado",
            "data_inicio": data_futura,
            "data_fim": data_futura,
        },
    )
    assert resp_canc.status_code == 302
    loc_canc = resp_canc.headers["Location"]
    assert "aba=pesquisa" in loc_canc
    assert "sucesso=" in loc_canc
    assert f"cliente=Cliente+Acao+{tag}" in loc_canc or f"cliente={cli_nome}" in loc_canc

import io
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

import app as app_module
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


def _proxima_data_dia_semana(dia_semana_alvo):
    """Retorna uma data futura YYYY-MM-DD para o dia da semana alvo (0=Dom, 1=Seg..6=Sab)."""
    hoje = datetime.now().date()
    for i in range(1, 14):
        candidata = hoje + timedelta(days=i)
        if (candidata.weekday() + 1) % 7 == dia_semana_alvo:
            return candidata.strftime("%Y-%m-%d")
    return (hoje + timedelta(days=7)).strftime("%Y-%m-%d")


def test_persistencia_disponibilidade(client, logged_admin):
    """Testa salvar, editar e recuperar a disponibilidade individual do profissional."""
    suffix = uuid.uuid4().hex[:6]
    servico_id, _ = models.criar_servico(f"Corte {suffix}", "50.00", 30, True, "Descricao")
    prof_id, _ = models.criar_profissional(f"Carlos {suffix}", True, [servico_id])

    path_edit = f"/admin/profissionais/{prof_id}/editar"
    token = _csrf_token(client, path_edit)

    payload = {
        "csrf_token": token,
        "nome": f"Carlos {suffix}",
        "ativo": "on",
        "servicos": [servico_id],
        # Segunda ativa: 08:00 - 18:00
        "disp_ativo_1": "on",
        "disp_entrada_1": "08:00",
        "disp_saida_1": "18:00",
        # Terça ativa: 09:00 - 17:00
        "disp_ativo_2": "on",
        "disp_entrada_2": "09:00",
        "disp_saida_2": "17:00",
        # Quarta inativa
        "disp_entrada_3": "08:00",
        "disp_saida_3": "18:00",
        # Quinta ativa: 08:00 - 12:00
        "disp_ativo_4": "on",
        "disp_entrada_4": "08:00",
        "disp_saida_4": "12:00",
        # Sexta inativa
        # Sábado inativo
        # Domingo inativo
    }

    resp = client.post(path_edit, data=payload, follow_redirects=True)
    assert resp.status_code == 200

    disp = models.obter_disponibilidade_profissional(prof_id)
    disp_por_dia = {d["dia_semana"]: d for d in disp}

    # Verifica Segunda (1)
    assert disp_por_dia[1]["ativo"] is True
    assert disp_por_dia[1]["horario_entrada"] == "08:00"
    assert disp_por_dia[1]["horario_saida"] == "18:00"

    # Verifica Terça (2)
    assert disp_por_dia[2]["ativo"] is True
    assert disp_por_dia[2]["horario_entrada"] == "09:00"
    assert disp_por_dia[2]["horario_saida"] == "17:00"

    # Verifica Quarta (3) - inativa
    assert disp_por_dia[3]["ativo"] is False

    # Verifica Quinta (4)
    assert disp_por_dia[4]["ativo"] is True
    assert disp_por_dia[4]["horario_entrada"] == "08:00"
    assert disp_por_dia[4]["horario_saida"] == "12:00"

    # Verifica Sexta, Sábado, Domingo - inativos
    assert disp_por_dia[5]["ativo"] is False
    assert disp_por_dia[6]["ativo"] is False
    assert disp_por_dia[0]["ativo"] is False

    # Edição subsequente: alterar Segunda para 10:00 - 16:00
    token2 = _csrf_token(client, path_edit)
    payload["csrf_token"] = token2
    payload["disp_entrada_1"] = "10:00"
    payload["disp_saida_1"] = "16:00"
    resp2 = client.post(path_edit, data=payload, follow_redirects=True)
    assert resp2.status_code == 200

    disp_atual = models.obter_disponibilidade_profissional(prof_id)
    disp_atual_dia = {d["dia_semana"]: d for d in disp_atual}
    assert disp_atual_dia[1]["horario_entrada"] == "10:00"
    assert disp_atual_dia[1]["horario_saida"] == "16:00"


def test_validacao_disponibilidade(client, logged_admin):
    """Testa rejeições por validação de horários no backend."""
    suffix = uuid.uuid4().hex[:6]
    servico_id, _ = models.criar_servico(f"Barba {suffix}", "30.00", 30, True)
    prof_id, _ = models.criar_profissional(f"Rafael {suffix}", True, [servico_id])

    path_edit = f"/admin/profissionais/{prof_id}/editar"

    # Caso 1: Dia ativo sem entrada
    token = _csrf_token(client, path_edit)
    resp = client.post(
        path_edit,
        data={
            "csrf_token": token,
            "nome": f"Rafael {suffix}",
            "ativo": "on",
            "servicos": [servico_id],
            "disp_ativo_1": "on",
            "disp_entrada_1": "",
            "disp_saida_1": "18:00",
        },
    )
    assert resp.status_code == 200
    assert "obrigatórios quando o dia estiver ativo" in resp.get_data(as_text=True)

    # Caso 2: Dia ativo sem saída
    token = _csrf_token(client, path_edit)
    resp = client.post(
        path_edit,
        data={
            "csrf_token": token,
            "nome": f"Rafael {suffix}",
            "ativo": "on",
            "servicos": [servico_id],
            "disp_ativo_1": "on",
            "disp_entrada_1": "08:00",
            "disp_saida_1": "",
        },
    )
    assert resp.status_code == 200
    assert "obrigatórios quando o dia estiver ativo" in resp.get_data(as_text=True)

    # Caso 3: Saída anterior à entrada
    token = _csrf_token(client, path_edit)
    resp = client.post(
        path_edit,
        data={
            "csrf_token": token,
            "nome": f"Rafael {suffix}",
            "ativo": "on",
            "servicos": [servico_id],
            "disp_ativo_1": "on",
            "disp_entrada_1": "18:00",
            "disp_saida_1": "08:00",
        },
    )
    assert resp.status_code == 200
    assert "deve ser posterior ao horário de entrada" in resp.get_data(as_text=True)

    # Caso 4: Saída igual à entrada
    token = _csrf_token(client, path_edit)
    resp = client.post(
        path_edit,
        data={
            "csrf_token": token,
            "nome": f"Rafael {suffix}",
            "ativo": "on",
            "servicos": [servico_id],
            "disp_ativo_1": "on",
            "disp_entrada_1": "10:00",
            "disp_saida_1": "10:00",
        },
    )
    assert resp.status_code == 200
    assert "deve ser posterior ao horário de entrada" in resp.get_data(as_text=True)


def test_calculo_disponibilidade_profissional(client, logged_admin):
    """Testa que a disponibilidade individual restringe rigorosamente os horários gerados."""
    suffix = uuid.uuid4().hex[:6]
    # Serviço de 60 minutos
    servico_id, _ = models.criar_servico(f"Combo {suffix}", "80.00", 60, True)
    prof_id, _ = models.criar_profissional(f"Especialista {suffix}", True, [servico_id])

    # Configura disponibilidade: trabalha apenas na Terça-feira (dia 2), das 09:00 às 12:00
    itens_disp = [
        {"dia_semana": 1, "ativo": False, "horario_entrada": "", "horario_saida": ""},
        {"dia_semana": 2, "ativo": True, "horario_entrada": "09:00", "horario_saida": "12:00"},
        {"dia_semana": 3, "ativo": False, "horario_entrada": "", "horario_saida": ""},
        {"dia_semana": 4, "ativo": False, "horario_entrada": "", "horario_saida": ""},
        {"dia_semana": 5, "ativo": False, "horario_entrada": "", "horario_saida": ""},
        {"dia_semana": 6, "ativo": False, "horario_entrada": "", "horario_saida": ""},
        {"dia_semana": 0, "ativo": False, "horario_entrada": "", "horario_saida": ""},
    ]
    models.salvar_disponibilidade_profissional(prof_id, itens_disp)

    data_terca = _proxima_data_dia_semana(2)
    data_quarta = _proxima_data_dia_semana(3)

    # 1. Na Terça-feira (dia que trabalha):
    # Com jornada 09:00-12:00 e serviço de 60 min (slots de 30 min):
    # 09:00 (termina 10:00) -> OK
    # 09:30 (termina 10:30) -> OK
    # 10:00 (termina 11:00) -> OK
    # 10:30 (termina 11:30) -> OK
    # 11:00 (termina 12:00) -> OK
    # 11:30 (terminaria 12:30 > 12:00) -> NÃO PODE APARECER
    resp_terca = client.get(
        f"/api/availability?profissional_id={prof_id}&servico_id={servico_id}&data={data_terca}"
    )
    assert resp_terca.status_code == 200
    horarios_terca = resp_terca.get_json()["horarios"]
    assert "09:00" in horarios_terca
    assert "11:00" in horarios_terca
    assert "11:30" not in horarios_terca
    assert "08:30" not in horarios_terca
    assert "12:00" not in horarios_terca

    # 2. Na Quarta-feira (dia que NÃO trabalha):
    resp_quarta = client.get(
        f"/api/availability?profissional_id={prof_id}&servico_id={servico_id}&data={data_quarta}"
    )
    assert resp_quarta.status_code == 200
    assert resp_quarta.get_json()["horarios"] == []


def test_dois_profissionais_jornadas_distintas(client):
    """Testa que profissionais diferentes possuem jornadas e disponibilidades independentes na mesma data."""
    suffix = uuid.uuid4().hex[:6]
    servico_id, _ = models.criar_servico(f"Corte {suffix}", "40.00", 30, True)

    prof1_id, _ = models.criar_profissional(f"Carlos {suffix}", True, [servico_id])
    prof2_id, _ = models.criar_profissional(f"Rafael {suffix}", True, [servico_id])

    # Carlos: Quinta-feira das 09:00 às 12:00
    # Rafael: Quinta-feira das 14:00 às 18:00
    disp_carlos = [
        {"dia_semana": 4, "ativo": True, "horario_entrada": "09:00", "horario_saida": "12:00"},
    ]
    disp_rafael = [
        {"dia_semana": 4, "ativo": True, "horario_entrada": "14:00", "horario_saida": "18:00"},
    ]
    models.salvar_disponibilidade_profissional(prof1_id, disp_carlos)
    models.salvar_disponibilidade_profissional(prof2_id, disp_rafael)

    data_quinta = _proxima_data_dia_semana(4)

    resp_carlos = client.get(
        f"/api/availability?profissional_id={prof1_id}&servico_id={servico_id}&data={data_quinta}"
    )
    resp_rafael = client.get(
        f"/api/availability?profissional_id={prof2_id}&servico_id={servico_id}&data={data_quinta}"
    )

    horarios_carlos = resp_carlos.get_json()["horarios"]
    horarios_rafael = resp_rafael.get_json()["horarios"]

    assert "09:00" in horarios_carlos
    assert "11:30" in horarios_carlos
    assert "14:00" not in horarios_carlos

    assert "14:00" in horarios_rafael
    assert "17:30" in horarios_rafael
    assert "09:00" not in horarios_rafael


def test_conflito_agendamento_com_jornada_individual(client):
    """Testa que agendamentos ocupados continuam bloqueando horários dentro da jornada individual."""
    suffix = uuid.uuid4().hex[:6]
    servico_id, _ = models.criar_servico(f"Barba {suffix}", "35.00", 30, True)
    prof_id, _ = models.criar_profissional(f"Barbeiro {suffix}", True, [servico_id])

    data_sexta = _proxima_data_dia_semana(5)
    disp = [
        {"dia_semana": 5, "ativo": True, "horario_entrada": "09:00", "horario_saida": "13:00"},
    ]
    models.salvar_disponibilidade_profissional(prof_id, disp)

    # Cria um agendamento às 10:00
    agendamento_id, erro = models.criar_agendamento(
        cliente_nome="Cliente Conflito",
        cliente_telefone="11999998888",
        servico_ids=[servico_id],
        profissional_id=prof_id,
        data_str=data_sexta,
        hora_str="10:00",
    )
    assert erro is None
    assert agendamento_id is not None

    resp = client.get(
        f"/api/availability?profissional_id={prof_id}&servico_id={servico_id}&data={data_sexta}"
    )
    horarios = resp.get_json()["horarios"]

    assert "09:30" in horarios
    assert "10:00" not in horarios  # Conflito bloqueado
    assert "10:30" in horarios


def test_regressao_profissional_sem_jornada_customizada(client):
    """Testa que um profissional sem jornada customizada cadastrada continua operando pelo horário geral do estabelecimento."""
    suffix = uuid.uuid4().hex[:6]
    servico_id, _ = models.criar_servico(f"Padrao {suffix}", "45.00", 30, True)
    prof_id, _ = models.criar_profissional(f"Sem Customizacao {suffix}", True, [servico_id])

    data_segunda = _proxima_data_dia_semana(1)
    resp = client.get(
        f"/api/availability?profissional_id={prof_id}&servico_id={servico_id}&data={data_segunda}"
    )
    assert resp.status_code == 200
    horarios = resp.get_json()["horarios"]
    # Como o estabelecimento abre às 09:00 e fecha às 19:00, os horários padrão são gerados
    assert len(horarios) > 0
    assert "09:00" in horarios

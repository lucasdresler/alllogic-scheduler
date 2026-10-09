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
from app import app, normalizar_para_tel, normalizar_para_whatsapp
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


def test_cancelamento_administrativo(client, logged_admin):
    prof_id, serv_id = _criar_profissional_e_servico()
    data_ag = _proxima_data(3)
    hora_ag = "10:00"

    ag_id, erro = models.criar_agendamento(
        "Cliente Cancelamento", "(11) 99999-1111", [serv_id], prof_id, data_ag, hora_ag
    )
    assert erro is None
    assert ag_id is not None

    # Horário 10:00 agora deve estar ocupado
    horarios_antes = models.horarios_disponiveis(prof_id, data_ag, [serv_id])
    assert hora_ag not in horarios_antes

    # Cancelar agendamento via POST com CSRF
    token = _csrf_token(client, "/admin")
    resp = client.post(
        f"/admin/agendamento/{ag_id}/cancelar",
        data={"csrf_token": token, "aba": "semana"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Agendamento cancelado com sucesso" in html

    # Verificar banco: status cancelado
    ag = models.obter_agendamento_completo(ag_id)
    assert ag["status"] == "cancelado"

    # Verificar que foi registrado no histórico
    with database.db_session() as conn:
        row = conn.execute(
            "SELECT status_anterior, status_novo FROM agendamento_status_historico WHERE agendamento_id = %s",
            (ag_id,),
        ).fetchone()
        assert row is not None
        assert row["status_anterior"] == "agendado"
        assert row["status_novo"] == "cancelado"

    # Tentar cancelar novamente deve ser impedido
    token2 = _csrf_token(client, "/admin")
    resp2 = client.post(
        f"/admin/agendamento/{ag_id}/cancelar",
        data={"csrf_token": token2, "aba": "semana"},
        follow_redirects=True,
    )
    assert resp2.status_code == 200
    assert "já está cancelado" in resp2.get_data(as_text=True)

    # Horário 10:00 deve voltar a estar livre
    horarios_depois = models.horarios_disponiveis(prof_id, data_ag, [serv_id])
    assert hora_ag in horarios_depois


def test_reagendamento_valido_e_historico(client, logged_admin):
    prof_id, serv_id = _criar_profissional_e_servico()
    data1 = _proxima_data(3)
    hora1 = "10:00"
    data2 = _proxima_data(4)
    hora2 = "14:00"

    ag_id, erro = models.criar_agendamento(
        "Cliente Reagendamento", "(11) 98888-2222", [serv_id], prof_id, data1, hora1
    )
    assert erro is None

    # Reagendar via POST
    token = _csrf_token(client, f"/admin/agendamento/{ag_id}/reagendar")
    resp = client.post(
        f"/admin/agendamento/{ag_id}/reagendar",
        data={
            "csrf_token": token,
            "nova_data": data2,
            "novo_horario": hora2,
            "aba": "semana",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Reagendamento realizado com sucesso" in resp.get_data(as_text=True)

    # Verificar que data e hora foram atualizadas e status continua 'agendado'
    ag_atualizado = models.obter_agendamento_completo(ag_id)
    assert ag_atualizado["data"] == data2
    assert ag_atualizado["hora"] == hora2
    assert ag_atualizado["status"] == "agendado"
    assert ag_atualizado["cliente_nome"] == "Cliente Reagendamento"

    # Verificar histórico gravado em agendamento_reagendamento
    hist = models.obter_historico_reagendamentos(ag_id)
    assert len(hist) == 1
    assert hist[0]["data_anterior"] == data1
    assert hist[0]["hora_anterior"] == hora1
    assert hist[0]["data_nova"] == data2
    assert hist[0]["hora_nova"] == hora2

    # Horário 1 original liberado; Horário 2 agora ocupado
    assert hora1 in models.horarios_disponiveis(prof_id, data1, [serv_id])
    assert hora2 not in models.horarios_disponiveis(prof_id, data2, [serv_id])


def test_tela_confirmacao_reagendamento(client, logged_admin):
    """Testa tela/estado de confirmação após reagendamento com sucesso:
    - Retorna status 200 (não redireciona imediatamente ao dashboard)
    - Informa: Reagendamento realizado com sucesso, Cliente, Serviço, Nova data, Novo horário, Profissional, Valor
    - Redirecionamento automático configurado para aproximadamente 3 segundos (3000ms / meta refresh)
    - Preserva contexto da agenda (aba, profissional_id, filtros de pesquisa)
    """
    prof_id, serv_id = _criar_profissional_e_servico(nome_prof="Carlos", nome_servico="Barba Premium", preco=60.0)
    data_orig = _proxima_data(2)
    data_nova = _proxima_data(4)
    hora_orig = "10:00"
    hora_nova = "14:00"

    ag_id, _ = models.criar_agendamento(
        "Maria Santos", "(11) 98888-7777", [serv_id], prof_id, data_orig, hora_orig
    )

    token = _csrf_token(client, f"/admin/agendamento/{ag_id}/reagendar")
    resp = client.post(
        f"/admin/agendamento/{ag_id}/reagendar",
        data={
            "csrf_token": token,
            "nova_data": data_nova,
            "novo_horario": hora_nova,
            "aba": "semana",
            "profissional_id": str(prof_id),
            "cliente": "Maria",
        },
        follow_redirects=False,
    )

    # Não deve retornar imediatamente com redirect (302) para o dashboard
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Mensagem de sucesso
    assert "Reagendamento realizado com sucesso" in html
    assert "Agendamento reagendado com sucesso" not in html

    # Dados do agendamento confirmados
    assert "Maria Santos" in html
    assert "Barba Premium" in html
    assert f"{data_nova[8:10]}/{data_nova[5:7]}/{data_nova[0:4]}" in html
    assert hora_nova in html
    assert "Carlos" in html
    assert "60,00" in html

    # Retorno automático em ~5 segundos
    assert "5000" in html
    assert 'content="5;url=' in html or "setTimeout" in html
    assert "Retornando para a Agenda em 5 segundos" in html

    # Botão de retorno imediato
    assert "Ir para a Agenda agora" in html
    assert 'id="btn-retorno-agenda"' in html

    # Preservação do contexto (aba=semana, profissional_id, filtros)
    assert "aba=semana" in html
    assert f"profissional_id={prof_id}" in html
    assert "cliente=Maria" in html


def test_reagendamento_conflito(client, logged_admin):
    prof_id, serv_id = _criar_profissional_e_servico()
    data = _proxima_data(3)

    ag1_id, _ = models.criar_agendamento("Cliente Um", "(11) 91111-1111", [serv_id], prof_id, data, "10:00")
    ag2_id, _ = models.criar_agendamento("Cliente Dois", "(11) 92222-2222", [serv_id], prof_id, data, "11:00")

    # Tenta reagendar ag2 para 10:00 (onde ag1 já está)
    ok, erro = models.reagendar_agendamento(ag2_id, data, "10:00", usuario=logged_admin)
    assert ok is False
    assert "Horário indisponível" in erro

    # ag2 deve permanecer às 11:00
    ag2 = models.obter_agendamento_completo(ag2_id)
    assert ag2["hora"] == "11:00"


def test_reagendamento_ignora_proprio_conflito(client, logged_admin):
    # Agendamento de 60 minutos das 10:00 às 11:00
    prof_id, serv_id = _criar_profissional_e_servico(duracao=60)
    data = _proxima_data(3)

    ag_id, _ = models.criar_agendamento("Cliente Slot", "(11) 93333-3333", [serv_id], prof_id, data, "10:00")

    # Mover para 10:30 no mesmo dia (sobrepõe o próprio agendamento antigo 10:00-11:00)
    ok, erro = models.reagendar_agendamento(ag_id, data, "10:30", usuario=logged_admin)
    assert ok is True
    assert erro is None

    ag = models.obter_agendamento_completo(ag_id)
    assert ag["hora"] == "10:30"


def test_reagendamento_jornada_e_estabelecimento(client, logged_admin):
    prof_id, serv_id = _criar_profissional_e_servico()
    data_valida = _proxima_data(2)
    ag_id, erro_c = models.criar_agendamento("Cliente Jornada", "(11) 94444-4444", [serv_id], prof_id, data_valida, "10:00")
    assert ag_id is not None, f"Falha ao criar agendamento: {erro_c}"

    # Configurar profissional para trabalhar apenas das 09:00 às 12:00 na terça-feira (dia 2)
    with database.db_session() as conn:
        conn.execute(
            """
            INSERT INTO profissional_disponibilidade (profissional_id, dia_semana, horario_entrada, horario_saida, ativo)
            VALUES (%s, 2, '09:00', '12:00', TRUE)
            ON CONFLICT (profissional_id, dia_semana) DO UPDATE SET
                horario_entrada = '09:00', horario_saida = '12:00', ativo = TRUE
            """,
            (prof_id,),
        )

    # Achar próxima terça-feira
    hoje = datetime.now().date()
    terca = None
    for i in range(1, 14):
        c = hoje + timedelta(days=i)
        if (c.weekday() + 1) % 7 == 2:
            terca = c.strftime("%Y-%m-%d")
            break

    # Tenta reagendar para terça-feira às 15:00 (fora da jornada do profissional que acaba às 12:00)
    ok, erro = models.reagendar_agendamento(ag_id, terca, "15:00", usuario=logged_admin)
    assert ok is False
    assert "Horário indisponível" in erro

    # Tenta reagendar para terça-feira às 10:00 (dentro da jornada)
    ok2, erro2 = models.reagendar_agendamento(ag_id, terca, "10:00", usuario=logged_admin)
    assert ok2 is True
    assert erro2 is None


def test_reagendamento_antecedencia_maxima(client, logged_admin):
    prof_id, serv_id = _criar_profissional_e_servico()
    data_valida = _proxima_data(2)

    ag_id, _ = models.criar_agendamento("Cliente Antecedencia", "(11) 95555-5555", [serv_id], prof_id, data_valida, "10:00")

    # Limitar antecedência para 5 dias
    with database.db_session() as conn:
        database.atualizar_configuracao(conn, "dias_antecedencia_agendamento", "5")
    models._limpar_cache_config()

    # Tentar reagendar para 10 dias no futuro
    data_longe = (datetime.now().date() + timedelta(days=10)).strftime("%Y-%m-%d")
    ok, erro = models.reagendar_agendamento(ag_id, data_longe, "10:00", usuario=logged_admin)
    assert ok is False
    assert "indisponível" in erro


def test_status_realizado_e_nao_compareceu(client, logged_admin):
    prof_id, serv_id = _criar_profissional_e_servico()
    data_passada = (datetime.now().date() - timedelta(days=1)).strftime("%Y-%m-%d")

    # Inserir agendamento no passado diretamente no banco
    with database.db_session() as conn:
        cur = conn.execute(
            """
            INSERT INTO agendamento (cliente_nome, cliente_telefone, servico_id, profissional_id, data, hora, status, profissional_nome_snapshot)
            VALUES ('Cliente Passado', '(11) 96666-6666', %s, %s, %s, '10:00', 'agendado', 'Profissional')
            RETURNING id
            """,
            (serv_id, prof_id, data_passada),
        )
        ag_id = cur.fetchone()["id"]
        conn.execute(
            """
            INSERT INTO agendamento_servico (agendamento_id, servico_id, nome_servico, preco_unitario, duracao_minutos)
            VALUES (%s, %s, 'Corte', 50.0, 30)
            """,
            (ag_id, serv_id),
        )

    # Marcar como realizado
    token = _csrf_token(client, "/admin")
    resp = client.post(
        f"/admin/agendamento/{ag_id}/status",
        data={"csrf_token": token, "status": "realizado", "aba": "mes"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "realizado com sucesso" in resp.get_data(as_text=True)

    ag = models.obter_agendamento_completo(ag_id)
    assert ag["status"] == "realizado"

    # Criar outro agendamento no passado e marcar como nao_compareceu
    with database.db_session() as conn:
        cur2 = conn.execute(
            """
            INSERT INTO agendamento (cliente_nome, cliente_telefone, servico_id, profissional_id, data, hora, status, profissional_nome_snapshot)
            VALUES ('Cliente Faltoso', '(11) 97777-7777', %s, %s, %s, '14:00', 'agendado', 'Profissional')
            RETURNING id
            """,
            (serv_id, prof_id, data_passada),
        )
        ag2_id = cur2.fetchone()["id"]
        conn.execute(
            """
            INSERT INTO agendamento_servico (agendamento_id, servico_id, nome_servico, preco_unitario, duracao_minutos)
            VALUES (%s, %s, 'Corte', 50.0, 30)
            """,
            (ag2_id, serv_id),
        )

    token2 = _csrf_token(client, "/admin")
    resp2 = client.post(
        f"/admin/agendamento/{ag2_id}/status",
        data={"csrf_token": token2, "status": "nao_compareceu", "aba": "mes"},
        follow_redirects=True,
    )
    assert resp2.status_code == 200
    assert "não compareceu" in resp2.get_data(as_text=True)

    ag2 = models.obter_agendamento_completo(ag2_id)
    assert ag2["status"] == "nao_compareceu"


def test_bloqueio_status_atendimento_futuro(client, logged_admin):
    prof_id, serv_id = _criar_profissional_e_servico()
    data_futura = _proxima_data(3)

    ag_id, _ = models.criar_agendamento(
        "Cliente Futuro", "(11) 98888-8888", [serv_id], prof_id, data_futura, "15:00"
    )

    # Tentar marcar atendimento futuro como realizado deve falhar
    token = _csrf_token(client, "/admin")
    resp = client.post(
        f"/admin/agendamento/{ag_id}/status",
        data={"csrf_token": token, "status": "realizado", "aba": "semana"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "futuros" in resp.get_data(as_text=True)

    ag = models.obter_agendamento_completo(ag_id)
    assert ag["status"] == "agendado"


def test_filtro_por_profissional(client, logged_admin):
    prof_a, serv_id = _criar_profissional_e_servico(nome_prof="Profissional A")
    prof_b, _ = _criar_profissional_e_servico(nome_prof="Profissional B")
    hoje_str = datetime.now().date().strftime("%Y-%m-%d")

    # Inserir agendamentos hoje para ambos
    with database.db_session() as conn:
        cur_a = conn.execute(
            """
            INSERT INTO agendamento (cliente_nome, cliente_telefone, servico_id, profissional_id, data, hora, status, profissional_nome_snapshot)
            VALUES ('Cliente A', '(11) 91111-2222', %s, %s, %s, '10:00', 'agendado', 'Profissional A')
            RETURNING id
            """,
            (serv_id, prof_a, hoje_str),
        )
        conn.execute(
            "INSERT INTO agendamento_servico VALUES (%s, %s, 'Corte', 40.0, 30)",
            (cur_a.fetchone()["id"], serv_id),
        )

        cur_b = conn.execute(
            """
            INSERT INTO agendamento (cliente_nome, cliente_telefone, servico_id, profissional_id, data, hora, status, profissional_nome_snapshot)
            VALUES ('Cliente B', '(11) 93333-4444', %s, %s, %s, '11:00', 'agendado', 'Profissional B')
            RETURNING id
            """,
            (serv_id, prof_b, hoje_str),
        )
        conn.execute(
            "INSERT INTO agendamento_servico VALUES (%s, %s, 'Corte', 60.0, 30)",
            (cur_b.fetchone()["id"], serv_id),
        )

    # Filtrar por Profissional A
    resp_a = client.get(f"/admin?aba=hoje&profissional_id={prof_a}")
    assert resp_a.status_code == 200
    html_a = resp_a.get_data(as_text=True)
    assert "Cliente A" in html_a
    assert "Cliente B" not in html_a

    # Filtrar por Profissional B
    resp_b = client.get(f"/admin?aba=hoje&profissional_id={prof_b}")
    assert resp_b.status_code == 200
    html_b = resp_b.get_data(as_text=True)
    assert "Cliente B" in html_b
    assert "Cliente A" not in html_b

    # Sem filtro (todos)
    resp_todos = client.get("/admin?aba=hoje")
    assert resp_todos.status_code == 200
    html_todos = resp_todos.get_data(as_text=True)
    assert "Cliente A" in html_todos
    assert "Cliente B" in html_todos


def test_telefone_e_whatsapp(client, logged_admin):
    # Teste unitário das normalizações
    assert normalizar_para_whatsapp("(11) 98765-4321") == "5511987654321"
    assert normalizar_para_whatsapp("11987654321") == "5511987654321"
    assert normalizar_para_whatsapp("5511987654321") == "5511987654321"

    assert normalizar_para_tel("(11) 98765-4321") == "+5511987654321"
    assert normalizar_para_tel("11987654321") == "+5511987654321"

    # Teste de renderização no dashboard
    prof_id, serv_id = _criar_profissional_e_servico()
    hoje_str = datetime.now().date().strftime("%Y-%m-%d")

    with database.db_session() as conn:
        cur = conn.execute(
            """
            INSERT INTO agendamento (cliente_nome, cliente_telefone, servico_id, profissional_id, data, hora, status, profissional_nome_snapshot)
            VALUES ('Cliente Contato', '(11) 98765-4321', %s, %s, %s, '10:00', 'agendado', 'Profissional')
            RETURNING id
            """,
            (serv_id, prof_id, hoje_str),
        )
        conn.execute(
            "INSERT INTO agendamento_servico VALUES (%s, %s, 'Corte', 40.0, 30)",
            (cur.fetchone()["id"], serv_id),
        )

    resp = client.get("/admin?aba=hoje")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'href="tel:+5511987654321"' in html
    assert 'href="https://wa.me/5511987654321"' in html
    assert "WhatsApp" in html

import ipaddress
import os
import re
import uuid
import pytest
from datetime import datetime, timedelta, timezone

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
from app import app, limiter
import models

app.config["TESTING"] = True
app.config["WTF_CSRF_ENABLED"] = False
limiter.enabled = False


@pytest.fixture
def client():
    with app.test_client() as test_client:
        yield test_client


def test_rota_experimente_redireciona_301_para_agillex(client):
    """Garante que /experimente redireciona permanentemente (301) para /agillex."""
    resp = client.get("/experimente", follow_redirects=False)
    assert resp.status_code == 301
    assert "/agillex" in resp.headers["Location"]


def test_rota_agillex_get_sucesso(client):
    """Garante que /agillex renderiza a página comercial e o formulário de cadastro."""
    resp = client.get("/agillex")
    assert resp.status_code == 200
    conteudo = resp.data.decode("utf-8")
    assert "Agillex Agenda para o seu Negócio" in conteudo
    assert "Cadastre seu Estabelecimento" in conteudo
    assert "Sem necessidade de cartão de crédito" in conteudo
    assert 'name="nome_estabelecimento"' in conteudo
    assert 'name="nome_responsavel"' in conteudo
    assert 'name="email"' in conteudo
    assert 'name="telefone"' in conteudo
    assert 'name="usuario"' in conteudo
    assert 'name="senha"' in conteudo
    assert 'name="confirmar_senha"' in conteudo
    assert 'name="termos"' in conteudo


def test_cadastro_agillex_campos_obrigatorios(client):
    """Validação de campos obrigatórios ausentes."""
    resp = client.post("/agillex", data={
        "nome_estabelecimento": "",
        "nome_responsavel": "",
        "email": "",
        "telefone": "",
        "usuario": "",
        "senha": "",
        "confirmar_senha": "",
    })
    assert resp.status_code == 200
    assert "Por favor, preencha todos os campos obrigatórios." in resp.data.decode("utf-8")


def test_cadastro_agillex_termos_nao_aceitos(client):
    """Validação de recusa dos termos de uso."""
    resp = client.post("/agillex", data={
        "nome_estabelecimento": "Salão Teste",
        "nome_responsavel": "Responsável Teste",
        "email": "teste@empresa.com",
        "telefone": "11987654321",
        "usuario": "salaoteste",
        "senha": "senhaSegura123",
        "confirmar_senha": "senhaSegura123",
        # termos não enviado
    })
    assert resp.status_code == 200
    assert "Você precisa concordar com os termos de uso" in resp.data.decode("utf-8")


def test_cadastro_agillex_email_invalido(client):
    """Validação de formato de e-mail inválido."""
    resp = client.post("/agillex", data={
        "nome_estabelecimento": "Salão Teste",
        "nome_responsavel": "Responsável Teste",
        "email": "email_invalido_sem_arroba",
        "telefone": "11987654321",
        "usuario": "salaoteste",
        "senha": "senhaSegura123",
        "confirmar_senha": "senhaSegura123",
        "termos": "1",
    })
    assert resp.status_code == 200
    assert "e-mail comercial válido" in resp.data.decode("utf-8")


def test_cadastro_agillex_senha_curta_ou_divergente(client):
    """Validação de senha curta e divergência na confirmação."""
    # Senha curta
    resp_curta = client.post("/agillex", data={
        "nome_estabelecimento": "Salão Teste",
        "nome_responsavel": "Responsável Teste",
        "email": "contato@salaoteste.com",
        "telefone": "11987654321",
        "usuario": "salaoteste",
        "senha": "123",
        "confirmar_senha": "123",
        "termos": "1",
    })
    assert resp_curta.status_code == 200
    assert "mínimo 8 caracteres" in resp_curta.data.decode("utf-8")

    # Confirmação divergente
    resp_div = client.post("/agillex", data={
        "nome_estabelecimento": "Salão Teste",
        "nome_responsavel": "Responsável Teste",
        "email": "contato@salaoteste.com",
        "telefone": "11987654321",
        "usuario": "salaoteste",
        "senha": "senhaSegura123",
        "confirmar_senha": "outraSenhaDiferente",
        "termos": "1",
    })
    assert resp_div.status_code == 200
    assert "confirmação de senha não confere" in resp_div.data.decode("utf-8")


def test_cadastro_agillex_criacao_com_sucesso_e_trial_14_dias(client):
    """Cadastro bem-sucedido com ativação real de 14 dias de teste."""
    sufixo = uuid.uuid4().hex[:6]
    usuario = f"user_{sufixo}"
    email = f"empresa_{sufixo}@teste.com"
    nome_estab = f"Studio Agillex {sufixo}"

    resp = client.post("/agillex", data={
        "nome_estabelecimento": nome_estab,
        "nome_responsavel": "Ana Souza",
        "email": email,
        "telefone": "(11) 98765-4321",
        "usuario": usuario,
        "senha": "senhaValida123",
        "confirmar_senha": "senhaValida123",
        "termos": "1",
    }, follow_redirects=False)

    assert resp.status_code == 302
    assert "/admin" in resp.headers["Location"]

    # Verificar dados no banco
    with database.db_session() as conn:
        admin_row = database.obter_admin_com_estabelecimento(conn, usuario)
        assert admin_row is not None
        assert admin_row["email"] == email
        assert admin_row["estabelecimento_nome"] == nome_estab
        assert admin_row["estabelecimento_status"] == "ativo"
        assert admin_row["estabelecimento_id"] is not None

        # Validação do período de 14 dias
        inicio = admin_row["trial_inicio"]
        fim = admin_row["trial_fim"]
        assert fim > inicio
        delta = fim - inicio
        assert delta.days == 14

        # Verificar helper de status do trial
        status_info = database.verificar_status_trial(conn, admin_row["estabelecimento_id"])
        assert status_info["status"] == "ativo"
        assert status_info["expirado"] is False
        assert status_info["dias_restantes"] in (13, 14)


def test_cadastro_agillex_anti_duplicidade(client):
    """Impede cadastro duplicado de usuário e e-mail."""
    sufixo = uuid.uuid4().hex[:6]
    usuario = f"user_{sufixo}"
    email = f"empresa_{sufixo}@teste.com"

    # Primeiro cadastro
    client.post("/agillex", data={
        "nome_estabelecimento": "Primeiro Salão",
        "nome_responsavel": "Carlos",
        "email": email,
        "telefone": "11988887777",
        "usuario": usuario,
        "senha": "senhaValida123",
        "confirmar_senha": "senhaValida123",
        "termos": "1",
    })

    # Tentativa de reutilizar mesmo usuário com e-mail diferente
    resp_dupl_user = client.post("/agillex", data={
        "nome_estabelecimento": "Outro Salão",
        "nome_responsavel": "Outro Carlos",
        "email": f"outro_{sufixo}@teste.com",
        "telefone": "11988887777",
        "usuario": usuario,
        "senha": "senhaValida123",
        "confirmar_senha": "senhaValida123",
        "termos": "1",
    })
    assert resp_dupl_user.status_code == 200
    assert "nome de usuário informado já está em uso" in resp_dupl_user.data.decode("utf-8")

    # Tentativa de reutilizar mesmo e-mail com usuário diferente
    resp_dupl_email = client.post("/agillex", data={
        "nome_estabelecimento": "Terceiro Salão",
        "nome_responsavel": "Maria",
        "email": email,
        "telefone": "11988887777",
        "usuario": f"outro_user_{sufixo}",
        "senha": "senhaValida123",
        "confirmar_senha": "senhaValida123",
        "termos": "1",
    })
    assert resp_dupl_email.status_code == 200
    assert "endereço de e-mail já está cadastrado" in resp_dupl_email.data.decode("utf-8")


def test_comportamento_trial_expirado(client):
    """Garante que estabelecimento expirado é redirecionado para tela de aviso sem exclusão de dados."""
    sufixo = uuid.uuid4().hex[:6]
    usuario = f"exp_{sufixo}"
    email = f"exp_{sufixo}@teste.com"

    # Criar conta diretamente no banco com trial já vencido
    with database.db_session() as conn:
        agora = datetime.now(timezone.utc)
        trial_passado_fim = agora - timedelta(days=1)
        trial_passado_inicio = agora - timedelta(days=15)

        row_est = conn.execute(
            """
            INSERT INTO estabelecimento (slug, nome, nome_responsavel, email, telefone, trial_inicio, trial_fim, status)
            VALUES (%s, 'Salão Vencido', 'Responsavel', %s, '11999999999', %s, %s, 'ativo')
            RETURNING id
            """,
            (f"exp-{sufixo}", email, trial_passado_inicio, trial_passado_fim),
        ).fetchone()
        estab_id = row_est["id"]

        from werkzeug.security import generate_password_hash
        conn.execute(
            """
            INSERT INTO admin (usuario, senha_hash, senha_inicial_alterada, email, nome_responsavel, estabelecimento_id)
            VALUES (%s, %s, TRUE, %s, 'Responsavel', %s)
            """,
            (usuario, generate_password_hash("senhaValida123"), email, estab_id),
        )

    # Fazer login como este admin
    login_resp = client.post("/admin/login", data={
        "usuario": usuario,
        "senha": "senhaValida123",
    }, follow_redirects=False)

    assert login_resp.status_code == 302
    assert "/admin/trial-expirado" in login_resp.headers["Location"]

    # Acessar a tela de trial expirado
    resp_exp = client.get("/admin/trial-expirado")
    assert resp_exp.status_code == 200
    conteudo = resp_exp.data.decode("utf-8")
    assert "Seu período de teste terminou" in conteudo
    assert "Seus dados continuam 100% seguros e preservados" in conteudo
    assert "WhatsApp Comercial" in conteudo
    assert "contato@alllogiconline.com.br" in conteudo

    # Tentar acessar dashboard enquanto expirado -> deve redirecionar para /admin/trial-expirado
    resp_dash = client.get("/admin", follow_redirects=False)
    assert resp_dash.status_code == 302
    assert "/admin/trial-expirado" in resp_dash.headers["Location"]

    # Confirmar no banco que os dados NÃO foram excluídos
    with database.db_session() as conn:
        est = database.obter_estabelecimento_por_id(conn, estab_id)
        assert est is not None
        assert est["nome"] == "Salão Vencido"
        assert est["status"] == "expirado"

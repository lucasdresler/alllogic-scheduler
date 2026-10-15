import ipaddress
import os
import re
import uuid
from datetime import datetime, timezone, timedelta

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
app.config["WTF_CSRF_ENABLED"] = False
app.config["RATELIMIT_ENABLED"] = False
from app import limiter
limiter.enabled = False


@pytest.fixture
def client():
    with app.test_client() as test_client:
        yield test_client


def test_agillex_get_renderiza_formulario(client):
    """GET /agillex deve renderizar o formulário de cadastro com 14 dias de teste e sem cartão."""
    resp = client.get("/agillex")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "14 Dias de Teste Grátis" in html
    assert "Cadastre seu Estabelecimento" in html
    assert "Sem cartão de crédito" in html
    assert 'name="nome_responsavel"' in html
    assert 'name="nome_estabelecimento"' in html
    assert 'name="cnpj_cpf"' in html
    assert 'name="telefone"' in html
    assert 'name="email"' in html
    assert 'name="senha"' in html
    assert 'name="confirmar_senha"' in html
    assert 'name="termos"' in html


def test_agillex_post_validacoes_campos_obrigatorios(client):
    """POST /agillex sem preenchimento deve acusar campos obrigatórios e termos."""
    # Vazio
    resp = client.post("/agillex", data={})
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Por favor, preencha todos os campos obrigatórios." in html

    # Sem termos
    resp_termos = client.post("/agillex", data={
        "nome_responsavel": "Carlos Silva",
        "nome_estabelecimento": "Barbearia Top",
        "cnpj_cpf": "12.345.678/0001-90",
        "telefone": "(11) 98765-4321",
        "email": f"teste_{uuid.uuid4().hex[:6]}@empresa.com",
        "senha": "password123",
        "confirmar_senha": "password123",
        # sem termos
    })
    assert resp_termos.status_code == 200
    assert "Você precisa concordar com os termos de uso" in resp_termos.data.decode("utf-8")


def test_agillex_post_validacoes_formato_documento_e_senha(client):
    """POST /agillex deve validar e-mail, CNPJ/CPF, telefone e senha mínima."""
    base_dados = {
        "nome_responsavel": "Carlos Silva",
        "nome_estabelecimento": "Barbearia Top",
        "cnpj_cpf": "123",  # Documento inválido
        "telefone": "(11) 98765-4321",
        "email": "invalido",  # Email inválido
        "senha": "123",  # Senha curta
        "confirmar_senha": "123",
        "termos": "1",
    }
    resp = client.post("/agillex", data=base_dados)
    html = resp.data.decode("utf-8")
    assert "Por favor, informe um endereço de e-mail válido." in html

    # Documento com menos dígitos
    base_dados["email"] = "carlos@empresa.com"
    resp_doc = client.post("/agillex", data=base_dados)
    assert "O documento informado deve ser um CPF (11 dígitos) ou CNPJ (14 dígitos) válido." in resp_doc.data.decode("utf-8")

    # Senha curta
    base_dados["cnpj_cpf"] = "12345678901"
    resp_senha = client.post("/agillex", data=base_dados)
    assert "A senha deve ter no mínimo 8 caracteres." in resp_senha.data.decode("utf-8")

    # Confirmação divergente
    base_dados["senha"] = "senhaSegura123"
    base_dados["confirmar_senha"] = "outraSenha123"
    resp_conf = client.post("/agillex", data=base_dados)
    assert "A confirmação de senha não confere" in resp_conf.data.decode("utf-8")


def test_agillex_post_cadastro_sucesso_calcula_14_dias(client):
    """POST /agillex com sucesso deve criar o estabelecimento com 14 dias exatos e logar."""
    import random
    suffix = uuid.uuid4().hex[:6]
    email = f"empresa_{suffix}@alllogiconline.com.br"
    cnpj = f"12345678{random.randint(100000, 999999)}"

    resp = client.post(
        "/agillex",
        data={
            "nome_responsavel": "Lucas Dresler",
            "nome_estabelecimento": "Salão Premium Alpha",
            "cnpj_cpf": cnpj,
            "telefone": "(11) 99887-7665",
            "email": email,
            "senha": "superSenha123",
            "confirmar_senha": "superSenha123",
            "termos": "1",
        },
        follow_redirects=False,
    )

    # Redireciona para /admin/estabelecimento com parâmetro boas_vindas=1
    assert resp.status_code == 302
    assert "admin/estabelecimento" in resp.headers["Location"]
    assert "boas_vindas=1" in resp.headers["Location"]

    # Verifica no banco de dados
    with database.db_session() as conn:
        est = database.obter_estabelecimento_por_email(conn, email)
        assert est is not None
        assert est["nome"] == "Salão Premium Alpha"
        assert est["nome_responsavel"] == "Lucas Dresler"
        assert est["status"] == "ativo"
        assert est["slug"].startswith("salao-premium-alpha")

        # Verifica cálculo de 14 dias de trial
        delta = est["trial_fim"] - est["trial_inicio"]
        assert delta.days == 14

        # Verifica conta admin associada
        adm = conn.execute("SELECT * FROM admin WHERE usuario = %s", (email,)).fetchone()
        assert adm is not None
        assert adm["estabelecimento_id"] == est["id"]
        assert adm["nome_responsavel"] == "Lucas Dresler"


def test_agillex_post_duplicidade_email_e_cnpj(client):
    """Não deve permitir duplicar e-mail ou criar novo trial para o mesmo CNPJ/CPF ativo."""
    import random
    suffix = uuid.uuid4().hex[:6]
    email = f"duplicado_{suffix}@empresa.com"
    cpf = f"111222{random.randint(10000, 99999)}"

    dados = {
        "nome_responsavel": "João Silva",
        "nome_estabelecimento": "Studio João",
        "cnpj_cpf": cpf,
        "telefone": "(11) 97777-6666",
        "email": email,
        "senha": "minhaSenha888",
        "confirmar_senha": "minhaSenha888",
        "termos": "1",
    }

    # Primeiro cadastro: OK
    resp1 = client.post("/agillex", data=dados)
    assert resp1.status_code == 302

    # Segundo cadastro com o mesmo email: erro
    resp2 = client.post("/agillex", data=dados)
    assert resp2.status_code == 200
    assert "Este endereço de e-mail já está cadastrado" in resp2.data.decode("utf-8")

    # Terceiro cadastro com email diferente mas mesmo CPF: erro de trial ativo
    dados["email"] = f"outro_{suffix}@empresa.com"
    resp3 = client.post("/agillex", data=dados)
    assert resp3.status_code == 200
    assert "Já existe uma avaliação de 14 dias ativa para este CNPJ/CPF" in resp3.data.decode("utf-8")


def test_pre_preenchimento_admin_estabelecimento(client):
    """Ao logar na conta recém criada, /admin/estabelecimento deve pré-preencher dados cadastrais."""
    import random
    suffix = uuid.uuid4().hex[:6]
    email = f"gestor_{suffix}@empresa.com"
    cnpj = f"98765432{random.randint(100000, 999999)}"

    # Cadastra via /agillex
    resp_cad = client.post(
        "/agillex",
        data={
            "nome_responsavel": "Mariana Santos",
            "nome_estabelecimento": "Clínica Bem Estar",
            "cnpj_cpf": cnpj,
            "telefone": "(11) 91234-5678",
            "email": email,
            "senha": "senhaMaster123",
            "confirmar_senha": "senhaMaster123",
            "termos": "1",
        },
    )
    assert resp_cad.status_code == 302

    # Acessa /admin/estabelecimento
    resp = client.get("/admin/estabelecimento?boas_vindas=1")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")

    # Verifica mensagem de boas vindas
    assert "Bem-vindo ao Agillex Agenda!" in html
    assert "14 dias de teste gratuito" in html

    # Verifica dados pré-preenchidos nos inputs
    assert 'value="Clínica Bem Estar"' in html
    assert 'value="Mariana Santos"' in html
    assert f'value="{cnpj}"' in html
    assert 'value="(11) 91234-5678"' in html
    assert f'value="{email}"' in html


def test_trial_expirado_redirecionamento(client):
    """Quando o período de 14 dias expirar, o admin é redirecionado para /admin/trial-expirado."""
    import random
    suffix = uuid.uuid4().hex[:6]
    email = f"expirado_{suffix}@empresa.com"
    cnpj = f"55544433{random.randint(100000, 999999)}"

    resp_cad = client.post(
        "/agillex",
        data={
            "nome_responsavel": "Pedro Alves",
            "nome_estabelecimento": "Barbearia Expirada",
            "cnpj_cpf": cnpj,
            "telefone": "(11) 95555-4444",
            "email": email,
            "senha": "senhaPedro123",
            "confirmar_senha": "senhaPedro123",
            "termos": "1",
        },
    )
    assert resp_cad.status_code == 302

    # Simula expiração alterando trial_fim para o passado
    with database.db_session() as conn:
        est = database.obter_estabelecimento_por_email(conn, email)
        assert est is not None
        passado = datetime.now(timezone.utc) - timedelta(days=1)
        conn.execute(
            "UPDATE estabelecimento SET trial_fim = %s WHERE id = %s",
            (passado, est["id"]),
        )

    # Tenta acessar dashboard: deve ser redirecionado para /admin/trial-expirado
    resp_dash = client.get("/admin", follow_redirects=False)
    assert resp_dash.status_code == 302
    assert "admin/trial-expirado" in resp_dash.headers["Location"]

    # Acessa /admin/trial-expirado
    resp_exp = client.get("/admin/trial-expirado")
    assert resp_exp.status_code == 200
    html = resp_exp.data.decode("utf-8")
    assert "Seu período de avaliação gratuita encerrou" in html
    assert "100% preservados e seguros" in html
    assert "Falar no WhatsApp para Ativar Plano" in html


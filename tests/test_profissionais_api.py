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

from app import app, limiter
import database
import models

app.config["TESTING"] = True
app.config["WTF_CSRF_ENABLED"] = False
app.config["RATELIMIT_ENABLED"] = False
limiter.enabled = False


@pytest.fixture
def client():
    with app.test_client() as test_client:
        yield test_client


def test_api_professionals_multitenant_carregamento_com_sucesso(client):
    """
    Testa se o endpoint /api/professionals responde HTTP 200 com a lista de profissionais
    para instâncias com estabelecimento_id != 1 (ex: petshop, clinica-odonto, barbearia),
    evitando a regressão de ordem de parâmetros SQL em listar_profissionais_para_servicos.
    """
    database.init_db()

    suffix = uuid.uuid4().hex[:6]
    email = f"dono_{suffix}@petshop.com"
    cnpj = f"99887766{random.randint(100000, 999999)}"

    # 1. Cria estabelecimento via /agillex
    resp = client.post(
        "/agillex",
        data={
            "nome_responsavel": f"Responsavel Pet {suffix}",
            "nome_estabelecimento": f"Pet Spa {suffix}",
            "cnpj_cpf": cnpj,
            "telefone": "(11) 98888-7777",
            "email": email,
            "senha": "senhaValida123",
            "confirmar_senha": "senhaValida123",
            "termos": "1",
            "plano": "pro",
        },
    )
    assert resp.status_code == 302

    with database.db_session() as conn:
        estab = database.obter_estabelecimento_por_email(conn, email)
        assert estab is not None
        estab_id = estab["id"]
        assert estab_id > 1

        # 2. Cria serviço e profissional vinculado ao estabelecimento
        sid, _ = models.criar_servico(
            f"Banho e Tosa {suffix}", 80.0, 60, True, estabelecimento_id=estab_id
        )
        pid, _ = models.criar_profissional(
            f"Groomer {suffix}", True, [sid], estabelecimento_id=estab_id
        )

        # 3. Teste unitário da função models.listar_profissionais_para_servicos
        profs_model = models.listar_profissionais_para_servicos([sid], estabelecimento_id=estab_id)
        assert len(profs_model) == 1
        assert profs_model[0]["id"] == pid
        assert profs_model[0]["nome"] == f"Groomer {suffix}"

    # 4. Teste de integração HTTP no endpoint público consumido pela Etapa 2 de agendamento
    api_url = f"/api/professionals?servico_id={sid}&estabelecimento_id={estab_id}"
    api_resp = client.get(api_url)
    assert api_resp.status_code == 200, f"Falha na API: {api_resp.status_code} - {api_resp.data}"

    dados = api_resp.get_json()
    assert isinstance(dados, list)
    assert len(dados) == 1
    assert dados[0]["id"] == pid
    assert dados[0]["nome"] == f"Groomer {suffix}"

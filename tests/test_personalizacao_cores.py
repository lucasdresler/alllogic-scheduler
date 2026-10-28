import pytest
import os

if os.environ.get("SCHEDULER_TEST_DATABASE") != "1" and not os.environ.get("POSTGRES_DB"):
    pytest.skip("Testes exigem banco PostgreSQL ativo.", allow_module_level=True)

from app import app
from database import db_session, init_db

app.config["TESTING"] = True
app.config["WTF_CSRF_ENABLED"] = False
app.config["RATELIMIT_ENABLED"] = False


def test_fluxo_personalizacao_cores():
    """Valida o fluxo completo de personalização de cores do estabelecimento e injeção de CSS."""
    init_db()
    client = app.test_client()

    with client.session_transaction() as sess:
        sess["admin_logado"] = True
        sess["estabelecimento_id"] = 1
        sess["admin_usuario"] = "lucasdresler"

    # 1. GET no formulário administrativo
    res_get = client.get("/admin/estabelecimento")
    assert res_get.status_code == 200
    html_get = res_get.data.decode("utf-8")
    assert "Paleta de Cores & Personalização" in html_get
    assert 'id="cor_primaria"' in html_get
    assert 'id="cor_secundaria"' in html_get
    assert 'id="cor_fundo"' in html_get

    # 2. POST com nova paleta
    dados = {
        "nome_estabelecimento": "Salão Teste Cores",
        "nome_responsavel": "Responsável Teste",
        "cpf_cnpj": "12.345.678/0001-90",
        "telefone": "(11) 98888-7777",
        "whatsapp": "(11) 98888-7777",
        "email_comercial": "teste@empresa.com",
        "cor_primaria": "#1E3A8A",
        "cor_secundaria": "#38BDF8",
        "cor_fundo": "#F0F9FF",
    }
    res_post = client.post("/admin/estabelecimento", data=dados, follow_redirects=True)
    assert res_post.status_code == 200

    # 3. Persistência no banco
    with db_session() as conn:
        row = conn.execute("SELECT cor_primaria, cor_secundaria, cor_fundo FROM estabelecimento WHERE id = 1").fetchone()
        assert row["cor_primaria"] == "#1E3A8A"
        assert row["cor_secundaria"] == "#38BDF8"
        assert row["cor_fundo"] == "#F0F9FF"

    # 4. Injeção de CSS no :root na vitrine pública
    res_pub = client.get("/")
    assert res_pub.status_code == 200
    html_pub = res_pub.data.decode("utf-8")
    assert "custom-palette-style" in html_pub
    assert "--navy-profundo: #1E3A8A;" in html_pub
    assert "--champagne-dourado: #38BDF8;" in html_pub
    assert "--fundo-marfim: #F0F9FF;" in html_pub

    # Restaurar padrão
    dados_padrao = dict(dados)
    dados_padrao.update({
        "nome_estabelecimento": "Minha Empresa",
        "cor_primaria": "#14213D",
        "cor_secundaria": "#E5C78B",
        "cor_fundo": "#F6F1E8",
    })
    client.post("/admin/estabelecimento", data=dados_padrao)

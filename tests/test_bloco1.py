import io
import ipaddress
import os
import re
import uuid
from datetime import date, timedelta

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


def test_nome_responsavel_read_and_update(client, logged_admin):
    """Testa leitura e persistência do nome do responsável na tela Dados do estabelecimento."""
    # GET deve mostrar o nome do responsável cadastrado na conta
    resp = client.get("/admin/estabelecimento")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'name="nome_responsavel"' in html
    assert 'value="Responsavel Teste"' in html

    token = _csrf_token(client, "/admin/estabelecimento")

    # POST com nome do responsável vazio deve falhar
    err_post = client.post(
        "/admin/estabelecimento",
        data={
            "csrf_token": token,
            "nome_estabelecimento": "Barbearia Alpha",
            "nome_responsavel": "",
        },
    )
    assert err_post.status_code == 200
    assert "O nome do responsável é obrigatório." in err_post.get_data(as_text=True)

    # POST com atualização do nome do responsável
    novo_resp = f"Carlos Silva {uuid.uuid4().hex[:6]}"
    token = _csrf_token(client, "/admin/estabelecimento")
    save_post = client.post(
        "/admin/estabelecimento",
        data={
            "csrf_token": token,
            "nome_estabelecimento": "Barbearia Alpha",
            "nome_responsavel": novo_resp,
            "telefone": "11988887777",
        },
    )
    assert save_post.status_code == 200
    assert "Dados do estabelecimento salvos com sucesso." in save_post.get_data(as_text=True)

    # Verifica persistência no banco (tabela admin)
    with database.db_session() as conn:
        admin_db = conn.execute(
            "SELECT nome_responsavel FROM admin WHERE usuario = %s",
            (logged_admin,),
        ).fetchone()
        assert admin_db["nome_responsavel"] == novo_resp

    # Nova consulta GET deve trazer o novo valor
    resp_get2 = client.get("/admin/estabelecimento")
    assert f'value="{novo_resp}"' in resp_get2.get_data(as_text=True)


def test_gerenciamento_logotipo(client, logged_admin):
    """Testa upload, visualização, substituição e remoção do logotipo."""
    # 1. Enviar logotipo válido (PNG)
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
    token = _csrf_token(client, "/admin/estabelecimento")
    upload_resp = client.post(
        "/admin/estabelecimento",
        data={
            "csrf_token": token,
            "nome_estabelecimento": "Estúdio Design",
            "nome_responsavel": "Responsável",
            "logotipo": (io.BytesIO(png_bytes), "logo.png"),
        },
        content_type="multipart/form-data",
    )
    assert upload_resp.status_code == 200
    html_upload = upload_resp.get_data(as_text=True)
    assert "Dados do estabelecimento salvos com sucesso." in html_upload
    assert "Remover logotipo" in html_upload
    assert 'uploads/logo_' in html_upload

    # Obtém caminho salvo
    with database.db_session() as conn:
        logo_path = database.obter_configuracao(conn, "logotipo")
        assert logo_path and logo_path.startswith("uploads/logo_")

    disco_path = os.path.join(app.root_path, "static", logo_path)
    assert os.path.isfile(disco_path)

    # 2. Visualização nas páginas administrativas
    dash_resp = client.get("/admin")
    assert logo_path in dash_resp.get_data(as_text=True)

    # 3. Substituir logotipo por SVG
    svg_content = b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>'
    token = _csrf_token(client, "/admin/estabelecimento")
    subst_resp = client.post(
        "/admin/estabelecimento",
        data={
            "csrf_token": token,
            "nome_estabelecimento": "Estúdio Design",
            "nome_responsavel": "Responsável",
            "logotipo": (io.BytesIO(svg_content), "novo_logo.svg"),
        },
        content_type="multipart/form-data",
    )
    assert subst_resp.status_code == 200
    with database.db_session() as conn:
        novo_logo_path = database.obter_configuracao(conn, "logotipo")
        assert novo_logo_path != logo_path
        assert novo_logo_path.endswith(".svg")

    # Arquivo antigo deve ter sido removido
    assert not os.path.isfile(disco_path)
    assert os.path.isfile(os.path.join(app.root_path, "static", novo_logo_path))

    # 4. Remover logotipo
    token = _csrf_token(client, "/admin/estabelecimento")
    rem_resp = client.post(
        "/admin/estabelecimento",
        data={
            "csrf_token": token,
            "nome_estabelecimento": "Estúdio Design",
            "nome_responsavel": "Responsável",
            "remover_logo": "1",
        },
    )
    assert rem_resp.status_code == 200
    assert "Logotipo removido com sucesso." in rem_resp.get_data(as_text=True)

    with database.db_session() as conn:
        logo_pos_rem = database.obter_configuracao(conn, "logotipo")
        assert logo_pos_rem == ""

    # Arquivo do logo substituído deve ter sido removido do disco
    assert not os.path.isfile(os.path.join(app.root_path, "static", novo_logo_path))


def test_validacao_upload_logotipo(client, logged_admin):
    """Testa validações de tamanho e formato no upload de logo."""
    # Arquivo com extensão inválida
    token = _csrf_token(client, "/admin/estabelecimento")
    bad_ext = client.post(
        "/admin/estabelecimento",
        data={
            "csrf_token": token,
            "nome_estabelecimento": "Teste",
            "nome_responsavel": "Responsável",
            "logotipo": (io.BytesIO(b"conteudo"), "documento.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert "Formato de imagem inválido" in bad_ext.get_data(as_text=True)

    # Imagem com extensão PNG mas conteúdo inválido
    token = _csrf_token(client, "/admin/estabelecimento")
    bad_bytes = client.post(
        "/admin/estabelecimento",
        data={
            "csrf_token": token,
            "nome_estabelecimento": "Teste",
            "nome_responsavel": "Responsável",
            "logotipo": (io.BytesIO(b"NOT_A_PNG"), "logo.png"),
        },
        content_type="multipart/form-data",
    )
    assert "não é uma imagem válida" in bad_bytes.get_data(as_text=True)


def test_configuracoes_da_agenda_sem_duplicidade(client, logged_admin):
    """Testa tela Configurações da agenda e garante que dados de identidade não são sobrescritos."""
    # Define dados em Dados do estabelecimento
    token = _csrf_token(client, "/admin/estabelecimento")
    client.post(
        "/admin/estabelecimento",
        data={
            "csrf_token": token,
            "nome_estabelecimento": "Estabelecimento Exclusivo",
            "nome_responsavel": "Dono Responsável",
            "telefone": "11977776666",
            "logradouro": "Rua Principal",
            "numero": "100",
            "cidade": "São Paulo",
            "estado": "SP",
        },
    )

    # Acessa Configurações da agenda
    resp = client.get("/admin/configuracoes")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Configurações da agenda" in html
    assert "Permitir agendamento com até" in html
    # Não deve ter campos técnicos de identidade para edição
    assert 'name="telefone_estabelecimento"' not in html
    assert 'name="endereco_estabelecimento"' not in html
    assert 'name="nome_publico"' not in html

    # Deve conter checkboxes dos dias da semana
    assert 'name="dias_funcionamento" value="1"' in html
    assert 'Segunda-feira' in html
    assert 'name="dias_funcionamento" value="0"' in html
    assert 'Domingo' in html

    # Salva novas regras operacionais
    token = _csrf_token(client, "/admin/configuracoes")
    save_resp = client.post(
        "/admin/configuracoes",
        data={
            "csrf_token": token,
            "dias_antecedencia_agendamento": "21",
            "horario_abertura": "08:00",
            "horario_fechamento": "18:00",
            "intervalo_slot_minutos": "30",
            "dias_funcionamento": ["1", "2", "3", "4", "5"],
        },
    )
    assert save_resp.status_code == 200
    assert "Configurações da agenda atualizadas com sucesso." in save_resp.get_data(as_text=True)

    # Verifica que nome, telefone e endereço continuam intactos (não foram sobrescritos!)
    with database.db_session() as conn:
        cfg = database.obter_todas_configuracoes(conn)
        assert cfg["nome_estabelecimento"] == "Estabelecimento Exclusivo"
        assert cfg["telefone_estabelecimento"] == "11977776666"
        assert "Rua Principal, 100" in cfg["endereco_estabelecimento"]
        assert cfg["dias_antecedencia_agendamento"] == "21"
        assert cfg["horario_abertura"] == "08:00"
        assert cfg["horario_fechamento"] == "18:00"
        assert cfg["dias_funcionamento"] == "1,2,3,4,5"


def test_identidade_cabecalhos_administrativos(client, logged_admin):
    """Testa se o nome e logotipo aparecem de forma consistente em todos os cabeçalhos administrativos."""
    with database.db_session() as conn:
        database.atualizar_configuracao(conn, "nome_estabelecimento", "Salão Magnífico")

    rotas = [
        "/admin/login",
        "/admin",
        "/admin/servicos",
        "/admin/servicos/novo",
        "/admin/profissionais",
        "/admin/profissionais/novo",
        "/admin/estabelecimento",
        "/admin/configuracoes",
        "/admin/alterar-senha",
    ]

    for rota in rotas:
        resp = client.get(rota)
        assert resp.status_code == 200, f"Rota {rota} retornou {resp.status_code}"
        conteudo = resp.get_data(as_text=True)
        assert "Salão Magnífico" in conteudo, f"Nome do estabelecimento não encontrado em {rota}"


def test_pagina_publica_e_rodape(client):
    """Testa página pública: logotipo, nome real, ausência do cliente na confirmação e rodapé público."""
    with database.db_session() as conn:
        database.atualizar_configuracao(conn, "nome_estabelecimento", "Barbearia do Bairro")
        database.atualizar_configuracao(conn, "endereco_estabelecimento", "Av. Brasil, 500 - Centro")
        database.atualizar_configuracao(conn, "telefone_estabelecimento", "(11) 98765-4321")

    models._limpar_cache_config()

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Nome real no header e title
    assert "Barbearia do Bairro" in html
    assert "<title>Barbearia do Bairro — Agendar Horário</title>" in html

    # Etapa 5 (Confirmação): NÃO deve conter a linha Cliente
    assert '<span>Cliente</span><span id="resumo-cliente"></span>' not in html
    assert '<span>Serviço</span><span id="resumo-servico"></span>' in html
    assert '<span>Preço</span><span id="resumo-preco"></span>' in html
    assert '<span>Profissional</span><span id="resumo-profissional"></span>' in html
    assert '<span>Data</span><span id="resumo-data"></span>' in html
    assert '<span>Horário</span><span id="resumo-hora"></span>' in html

    # Rodapé público discreto com endereço e telefone clicável
    assert '<footer class="rodape-publico">' in html
    assert 'Av. Brasil, 500 - Centro' in html
    assert 'href="tel:11987654321"' in html
    assert '(11) 98765-4321' in html


def test_tela_sucesso_retorno_automatico(client, monkeypatch):
    """Testa tela de sucesso com retorno automático após ~5s, mensagem discreta e sem botão voltar."""
    with database.db_session() as conn:
        database.atualizar_configuracao(conn, "nome_estabelecimento", "Barbearia do Bairro")
        database.atualizar_configuracao(conn, "endereco_estabelecimento", "Av. Brasil, 500 - Centro")
        database.atualizar_configuracao(conn, "telefone_estabelecimento", "11987654321")

    models._limpar_cache_config()

    monkeypatch.setattr(
        models,
        "obter_agendamento_completo",
        lambda appointment_id: {
            "servico_nome": "Corte Moderno",
            "servico_preco": 45.0,
            "profissional_nome": "Carlos",
            "data": "2030-05-10",
            "hora": "14:00",
            "cliente_nome": "Cliente VIP",
        },
    )

    resp = client.get("/agendamento/sucesso/999")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Mensagem de sucesso
    assert "Agendamento realizado com sucesso!" in html
    # Mensagem discreta de redirecionamento
    assert "Você será direcionado ao início em alguns segundos." in html
    # SEM botão 'Voltar ao início'
    assert "Voltar ao início" not in html
    # Script de redirecionamento em 5000ms
    assert "5000" in html
    assert "window.location.href" in html
    # Rodapé público
    assert '<footer class="rodape-publico">' in html
    assert 'Av. Brasil, 500 - Centro' in html
    assert 'href="tel:11987654321"' in html

import ipaddress
import os
import re
import uuid
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

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
import whatsapp_service

app.config["TESTING"] = True


@pytest.fixture
def client():
    with app.test_client() as test_client:
        yield test_client


def _csrf_token(client, path):
    response = client.get(path)
    assert response.status_code == 200
    match = re.search(
        r'name="csrf_token"\s+value="([^"]+)"',
        response.get_data(as_text=True),
    )
    assert match, f"csrf_token not found in {path}"
    return match.group(1)


def test_normalizacao_telefone_whatsapp():
    assert whatsapp_service.normalizar_numero_whatsapp("(11) 96638-1915") == "5511966381915"
    assert whatsapp_service.normalizar_numero_whatsapp("11966381915") == "5511966381915"
    assert whatsapp_service.normalizar_numero_whatsapp("5511966381915") == "5511966381915"
    assert whatsapp_service.normalizar_numero_whatsapp("") == ""


def test_formatacao_mensagem_cliente_contem_telefone_e_reserva():
    agendamento = {
        "cliente_nome": "Lucas Silva",
        "cliente_telefone": "(11) 99999-8888",
        "data": "2026-10-20",
        "hora": "14:30",
        "servico_nome": "Corte de Cabelo",
        "profissional_nome": "Rafael",
        "servico_preco": 45.0,
        "token_acesso": "token-teste-12345",
    }
    config = {
        "nome_estabelecimento": "Salão Premium",
        "telefone_estabelecimento": "(11) 96638-1915",
        "endereco_estabelecimento": "Rua da Paz, 100",
    }
    msg = whatsapp_service.formatar_mensagem_cliente(
        agendamento, config, "https://agenda.alllogiconline.com.br"
    )

    assert "Lucas Silva" in msg
    assert "Salão Premium" in msg
    assert "20/10/2026 às 14:30" in msg
    assert "Corte de Cabelo" in msg
    assert "Rafael" in msg
    assert "R$ 45,00" in msg
    assert "Rua da Paz, 100" in msg
    assert "(11) 96638-1915" in msg  # Telefone do salão exigido pelo usuário!
    assert "https://agenda.alllogiconline.com.br/reserva/token-teste-12345" in msg


def test_enviar_mensagem_evolution_api_mock():
    with patch.dict(
        os.environ,
        {
            "EVOLUTION_API_URL": "https://evolution.alllogiconline.com.br",
            "EVOLUTION_API_KEY": "teste-key-123",
            "EVOLUTION_INSTANCE_NAME": "instancia-teste",
        },
    ):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            ok, err = whatsapp_service.enviar_mensagem_evolution_api(
                "(11) 96638-1915", "Teste de mensagem"
            )
            assert ok is True
            assert err is None
            assert mock_urlopen.called


def test_pagina_reserva_publica_e_cancelamento(client):
    suffix = uuid.uuid4().hex[:6]
    sid, _ = models.criar_servico(f"Servico {suffix}", 40.0, 30, True)
    pid, _ = models.criar_profissional(f"Prof {suffix}", True, [sid])

    dias = models.dias_funcionamento()
    d = date.today() + timedelta(days=2)
    while d.weekday() not in dias:
        d += timedelta(days=1)
    data_str = d.strftime("%Y-%m-%d")

    horarios = models.horarios_disponiveis(pid, data_str, [sid])
    assert len(horarios) > 0

    ag_id, err = models.criar_agendamento(
        f"Cliente {suffix}", "(11) 97777-1111", [sid], pid, data_str, horarios[0]
    )
    assert err is None
    ag = models.obter_agendamento_completo(ag_id)
    token = ag["token_acesso"]
    assert token is not None and len(token) > 10

    # 1. Acesso à página da reserva
    res = client.get(f"/reserva/{token}")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Gerenciamento de Reserva" in html
    assert f"Cliente {suffix}" in html
    assert "Confirmado" in html

    # 2. Tela de sucesso do agendamento
    res_sucesso = client.get(f"/agendamento/sucesso/{ag_id}")
    assert res_sucesso.status_code == 200
    html_suc = res_sucesso.get_data(as_text=True)
    assert f"/reserva/{token}" in html_suc
    assert "Enviar / Abrir Comprovante no WhatsApp" in html_suc

    # 3. Cancelamento pelo cliente via token
    csrf = _csrf_token(client, f"/reserva/{token}")
    res_canc = client.post(
        f"/reserva/{token}/cancelar",
        data={"csrf_token": csrf},
        follow_redirects=True,
    )
    assert res_canc.status_code == 200
    html_pos_canc = res_canc.get_data(as_text=True)
    assert "cancelado com sucesso" in html_pos_canc
    assert "Cancelado" in html_pos_canc

    # 4. Verificar no banco que o status mudou para cancelado
    ag_atualizado = models.obter_agendamento_completo(ag_id)
    assert ag_atualizado["status"] == "cancelado"

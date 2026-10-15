import json
import logging
import os
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

logger = logging.getLogger("whatsapp_service")


def normalizar_numero_whatsapp(telefone):
    """
    Normaliza telefone para formato aceito pela Evolution API (DDI + DDD + número).
    Exemplo: '(11) 96638-1915' -> '5511966381915'
    """
    if not telefone:
        return ""
    digitos = re.sub(r"\D", "", str(telefone))
    if not digitos:
        return ""
    if len(digitos) in (10, 11):
        return f"55{digitos}"
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        return digitos
    return digitos


def enviar_mensagem_evolution_api(numero, texto):
    """
    Envia mensagem de texto via Evolution API v2.
    Retorna (True, None) em caso de sucesso ou (False, erro_str) em caso de falha.
    """
    numero_limpo = normalizar_numero_whatsapp(numero)
    if not numero_limpo:
        return False, "Número de telefone inválido."

    api_url = os.environ.get("EVOLUTION_API_URL", "https://evolution.alllogiconline.com.br").rstrip("/")
    api_key = os.environ.get("EVOLUTION_API_KEY", "").strip()
    instance_name = os.environ.get("EVOLUTION_INSTANCE_NAME", "").strip()

    if not api_key or not instance_name:
        msg = "Evolution API não configurada (EVOLUTION_API_KEY ou EVOLUTION_INSTANCE_NAME ausente no .env)."
        logger.info(msg)
        return False, msg

    endpoint = f"{api_url}/message/sendText/{instance_name}"
    payload = json.dumps({
        "number": numero_limpo,
        "text": texto,
    }).encode("utf-8")

    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "apikey": api_key,
            "User-Agent": "AllLogic-Scheduler/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            status_code = response.getcode()
            if status_code in (200, 201):
                logger.info(f"Mensagem WhatsApp enviada com sucesso para {numero_limpo} via Evolution API.")
                return True, None
            corpo = response.read().decode("utf-8", errors="ignore")
            logger.warning(f"Evolution API retornou status {status_code}: {corpo}")
            return False, f"Status {status_code}: {corpo}"
    except urllib.error.HTTPError as e:
        corpo = e.read().decode("utf-8", errors="ignore")
        logger.error(f"Erro HTTP na Evolution API ({e.code}): {corpo}")
        return False, f"HTTP {e.code}: {corpo}"
    except Exception as e:
        logger.error(f"Exceção ao conectar na Evolution API: {e}")
        return False, str(e)


def _formatar_data_br(data_str):
    if not data_str:
        return ""
    try:
        partes = data_str.split("-")
        if len(partes) == 3:
            return f"{partes[2]}/{partes[1]}/{partes[0]}"
    except Exception:
        pass
    return data_str


def formatar_telefone_br(telefone):
    """Formata telefone brasileiro para (XX) XXXXX-XXXX ou (XX) XXXX-XXXX."""
    if not telefone:
        return ""
    digitos = re.sub(r"\D", "", str(telefone))
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        digitos = digitos[2:]
    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
    elif len(digitos) == 10:
        return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"
    return str(telefone).strip()


def formatar_mensagem_cliente(agendamento, config, url_base):
    """
    Monta a mensagem de confirmação para o cliente incluindo telefone do estabelecimento e link da reserva.
    """
    nome_estabelecimento = config.get("nome_estabelecimento") or "Salão"
    telefone_bruto = (
        config.get("telefone_estabelecimento")
        or config.get("telefone")
        or config.get("whatsapp")
        or "(11) 96638-1915"
    )
    telefone_estabelecimento = formatar_telefone_br(telefone_bruto)
    endereco = config.get("endereco_estabelecimento") or config.get("endereco") or ""

    cliente_nome = agendamento.get("cliente_nome", "Cliente")
    data_fmt = _formatar_data_br(agendamento.get("data", ""))
    hora = agendamento.get("hora", "")
    servicos = agendamento.get("servico_nome", "Serviço")
    profissional = agendamento.get("profissional_nome", "Profissional")
    preco = agendamento.get("servico_preco", 0.0)
    preco_fmt = f"{preco:.2f}".replace(".", ",")

    token = agendamento.get("token_acesso", "")
    url_base_limpa = (url_base or "https://agenda.alllogiconline.com.br").rstrip("/")
    url_reserva = f"{url_base_limpa}/reserva/{token}" if token else url_base_limpa

    linhas = [
        "✅ *Agendamento Confirmado!*",
        f"💈 *{nome_estabelecimento}*",
        "",
        f"Olá, *{cliente_nome}*!",
        "Seu horário foi agendado com sucesso:",
        "",
        f"✂️ *Serviço:* {servicos}",
        f"👤 *Profissional:* {profissional}",
        f"📅 *Data:* {data_fmt} às {hora}",
        f"💰 *Valor:* R$ {preco_fmt}",
    ]

    if endereco:
        linhas.append(f"📍 *Endereço:* {endereco}")
    if telefone_estabelecimento:
        linhas.append(f"📞 *Contato:* {telefone_estabelecimento}")

    linhas.extend([
        "",
        "👉 *Para consultar os detalhes ou gerenciar sua reserva, acesse:*",
        url_reserva,
    ])

    return "\n".join(linhas)


def formatar_mensagem_admin(agendamento, config, url_base):
    """
    Monta a mensagem de aviso de novo agendamento para o administrador/estabelecimento.
    """
    nome_estabelecimento = config.get("nome_estabelecimento") or "Salão"
    cliente_nome = agendamento.get("cliente_nome", "Cliente")
    cliente_telefone = formatar_telefone_br(agendamento.get("cliente_telefone", ""))
    data_fmt = _formatar_data_br(agendamento.get("data", ""))
    hora = agendamento.get("hora", "")
    servicos = agendamento.get("servico_nome", "Serviço")
    profissional = agendamento.get("profissional_nome", "Profissional")
    preco = agendamento.get("servico_preco", 0.0)
    preco_fmt = f"{preco:.2f}".replace(".", ",")

    url_base_limpa = (url_base or "https://agenda.alllogiconline.com.br").rstrip("/")
    url_admin = f"{url_base_limpa}/admin"

    linhas = [
        f"🔔 *Novo Agendamento Recebido! — {nome_estabelecimento}*",
        "",
        f"👤 *Cliente:* {cliente_nome}",
        f"📱 *WhatsApp:* {cliente_telefone}",
        f"📅 *Data:* {data_fmt} às {hora}",
        f"✂️ *Serviços:* {servicos}",
        f"💈 *Profissional:* {profissional}",
        f"💰 *Valor:* R$ {preco_fmt}",
        "",
        f"Acesse o painel para gerenciar: {url_admin}",
    ]

    return "\n".join(linhas)


def formatar_mensagem_cancelamento_cliente(agendamento, config):
    """Monta mensagem de confirmação de cancelamento para o cliente."""
    nome_estabelecimento = config.get("nome_estabelecimento") or "Salão"
    cliente_nome = agendamento.get("cliente_nome", "Cliente")
    data_fmt = _formatar_data_br(agendamento.get("data", ""))
    hora = agendamento.get("hora", "")
    servicos = agendamento.get("servico_nome", "Serviço")

    return (
        f"❌ *Agendamento Cancelado — {nome_estabelecimento}*\n\n"
        f"Olá, {cliente_nome}. Seu agendamento para o dia {data_fmt} às {hora} ({servicos}) foi cancelado com sucesso.\n\n"
        f"Quando desejar agendar um novo horário, estaremos à disposição!"
    )


def formatar_mensagem_cancelamento_admin(agendamento, config, url_base):
    """Monta mensagem de aviso de cancelamento para o administrador."""
    nome_estabelecimento = config.get("nome_estabelecimento") or "Salão"
    cliente_nome = agendamento.get("cliente_nome", "Cliente")
    cliente_telefone = formatar_telefone_br(agendamento.get("cliente_telefone", ""))
    data_fmt = _formatar_data_br(agendamento.get("data", ""))
    hora = agendamento.get("hora", "")
    servicos = agendamento.get("servico_nome", "Serviço")
    url_base_limpa = (url_base or "https://agenda.alllogiconline.com.br").rstrip("/")

    return (
        f"⚠️ *Agendamento Cancelado — {nome_estabelecimento}*\n\n"
        f"👤 *Cliente:* {cliente_nome} ({cliente_telefone})\n"
        f"📅 *Data:* {data_fmt} às {hora}\n"
        f"✂️ *Serviços:* {servicos}\n\n"
        f"O horário foi liberado na agenda: {url_base_limpa}/admin"
    )


def gerar_link_wa_me(numero, texto):
    """
    Gera link direto para WhatsApp com mensagem URL-encoded.
    Usa api.whatsapp.com/send para evitar o bug de redirecionamento 302 do wa.me que corrompe emojis e quebras de linha.
    """
    numero_limpo = normalizar_numero_whatsapp(numero)
    texto_encoded = urllib.parse.quote(texto)
    if numero_limpo:
        return f"https://api.whatsapp.com/send?phone={numero_limpo}&text={texto_encoded}"
    return f"https://api.whatsapp.com/send?text={texto_encoded}"


def notificar_novo_agendamento_whatsapp(agendamento_id, url_base=None):
    """
    Dispara notificações de novo agendamento para o cliente e para o administrador em background.
    """
    def _worker():
        try:
            import models
            from database import db_session, obter_todas_configuracoes

            agendamento = models.obter_agendamento_completo(agendamento_id)
            if not agendamento:
                logger.warning(f"Agendamento {agendamento_id} não encontrado para notificação WhatsApp.")
                return

            with db_session() as conn:
                config = obter_todas_configuracoes(conn)

            base_url = url_base or os.environ.get("APP_URL_BASE", "https://agenda.alllogiconline.com.br")

            # 1. Enviar mensagem para o Cliente
            telefone_cliente = agendamento.get("cliente_telefone")
            if telefone_cliente:
                msg_cliente = formatar_mensagem_cliente(agendamento, config, base_url)
                enviar_mensagem_evolution_api(telefone_cliente, msg_cliente)

            # 2. Enviar mensagem para o Administrador / Estabelecimento
            telefone_admin = (
                config.get("whatsapp")
                or config.get("telefone_estabelecimento")
                or config.get("telefone")
                or os.environ.get("ADMIN_WHATSAPP")
            )
            if telefone_admin:
                msg_admin = formatar_mensagem_admin(agendamento, config, base_url)
                enviar_mensagem_evolution_api(telefone_admin, msg_admin)

        except Exception as e:
            logger.error(f"Erro no envio de notificações WhatsApp do agendamento {agendamento_id}: {e}")

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


def notificar_cancelamento_whatsapp(agendamento_id, url_base=None):
    """
    Dispara notificações de cancelamento para o cliente e para o administrador em background.
    """
    def _worker():
        try:
            import models
            from database import db_session, obter_todas_configuracoes

            agendamento = models.obter_agendamento_completo(agendamento_id)
            if not agendamento:
                return

            with db_session() as conn:
                config = obter_todas_configuracoes(conn)

            base_url = url_base or os.environ.get("APP_URL_BASE", "https://agenda.alllogiconline.com.br")

            # Mensagem cliente
            telefone_cliente = agendamento.get("cliente_telefone")
            if telefone_cliente:
                msg_cliente = formatar_mensagem_cancelamento_cliente(agendamento, config)
                enviar_mensagem_evolution_api(telefone_cliente, msg_cliente)

            # Mensagem admin
            telefone_admin = (
                config.get("whatsapp")
                or config.get("telefone_estabelecimento")
                or config.get("telefone")
                or os.environ.get("ADMIN_WHATSAPP")
            )
            if telefone_admin:
                msg_admin = formatar_mensagem_cancelamento_admin(agendamento, config, base_url)
                enviar_mensagem_evolution_api(telefone_admin, msg_admin)

        except Exception as e:
            logger.error(f"Erro no envio de notificação de cancelamento WhatsApp: {e}")

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("alllogic.email")


def enviar_email_recuperacao(destinatario, link_recuperacao, nome_responsavel=None):
    """
    Envia o e-mail de recuperação de senha.
    Em desenvolvimento local sem SMTP configurado, registra o link no console de forma segura.
    """
    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_password = os.environ.get("SMTP_PASSWORD", "").strip()
    smtp_from = os.environ.get("SMTP_FROM", "").strip() or smtp_user or "nao-responda@alllogiconline.com.br"
    smtp_use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

    app_env = os.environ.get("APP_ENV", os.environ.get("FLASK_ENV", "development")).lower()
    is_dev = app_env in ("development", "dev", "local", "testing")

    nome = nome_responsavel or "Administrador"
    assunto = "Recuperação de Senha — AllLogic Scheduler"

    texto_plano = f"""Olá, {nome}.

Recebemos uma solicitação para redefinir a senha de acesso da sua conta de administrador no AllLogic Scheduler.

Para definir uma nova senha, utilize o link abaixo:
{link_recuperacao}

Este link é seguro, possui validade de 30 minutos e só pode ser utilizado uma única vez.

Se você não solicitou a redefinição de senha, desconsidere esta mensagem. Sua conta permanece segura.
"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #e6e6e6; background-color: #0f0f11; padding: 30px 20px;">
    <div style="max-width: 560px; margin: 0 auto; background-color: #1a1a1f; padding: 32px; border-radius: 12px; border: 1px solid #2e2e38;">
        <h2 style="color: #c5a059; margin-top: 0; font-size: 1.4rem;">Recuperação de Senha</h2>
        <p style="margin-bottom: 16px;">Olá, <strong>{nome}</strong>.</p>
        <p style="margin-bottom: 24px;">Recebemos uma solicitação para redefinir a senha da sua conta de administrador no <strong>AllLogic Scheduler</strong>.</p>
        <div style="text-align: center; margin: 32px 0;">
            <a href="{link_recuperacao}" style="background-color: #c5a059; color: #0d0d0d; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block; font-size: 1rem;">Redefinir Senha</a>
        </div>
        <p style="font-size: 0.85rem; color: #a0a0a8; word-break: break-all;">
            Ou acesse diretamente pelo link:<br>
            <a href="{link_recuperacao}" style="color: #c5a059;">{link_recuperacao}</a>
        </p>
        <div style="border-top: 1px solid #2e2e38; margin-top: 28px; padding-top: 16px; font-size: 0.8rem; color: #70707a;">
            <p style="margin: 0 0 6px 0;">Este link é válido por <strong>30 minutos</strong> e só pode ser usado uma vez.</p>
            <p style="margin: 0;">Se você não solicitou esta redefinição, nenhuma ação é necessária.</p>
        </div>
    </div>
</body>
</html>
"""

    if not smtp_host:
        if is_dev:
            print(f"\n=======================================================")
            print(f"[SIMULAÇÃO LOCAL DE E-MAIL - SEM SMTP]")
            print(f"Para: {destinatario}")
            print(f"Assunto: {assunto}")
            print(f"Link de Recuperação: {link_recuperacao}")
            print(f"Validade: 30 minutos (uso único)")
            print(f"=======================================================\n")
            logger.info("E-mail de recuperação simulado com sucesso para %s", destinatario)
            return True, None
        else:
            logger.error("Servidor SMTP não configurado em ambiente de produção.")
            return False, "Serviço de e-mail não configurado no servidor."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = smtp_from
        msg["To"] = destinatario
        msg.attach(MIMEText(texto_plano, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))

        server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
        if smtp_use_tls:
            server.starttls()
        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)
        server.sendmail(smtp_from, [destinatario], msg.as_string())
        server.quit()
        return True, None
    except Exception as e:
        logger.exception("Falha ao enviar e-mail via SMTP: %s", e)
        return False, "Não foi possível enviar o e-mail no momento. Tente novamente mais tarde."

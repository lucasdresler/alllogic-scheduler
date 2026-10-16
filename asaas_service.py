import os
import time
import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

def _obter_asaas_config():
    api_key = os.environ.get("ASAAS_API_KEY", "").strip()
    env = os.environ.get("ASAAS_ENVIRONMENT", "production").strip().lower()

    # Se não estiver no os.environ, tenta ler de arquivos .env conhecidos
    if not api_key:
        candidate_paths = [
            "/home/dresler/matriz-saas/.env.production",
            os.path.expanduser("~/matriz-saas/.env.production"),
            ".env.production",
            ".env",
        ]
        for p in candidate_paths:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("ASAAS_API_KEY="):
                                api_key = line.split("=", 1)[1].strip().strip("'\"")
                            elif line.startswith("ASAAS_ENVIRONMENT="):
                                env = line.split("=", 1)[1].strip().strip("'\"").lower()
                except Exception as e:
                    logger.debug(f"Erro ao ler {p}: {e}")
                if api_key:
                    break

    base_url = "https://api.asaas.com/v3" if env == "production" else "https://sandbox.asaas.com/api/v3"
    is_configured = bool(api_key and api_key != "sua_chave_asaas_aqui")
    return api_key, base_url, is_configured


def gerar_pix_agendamento(nome_cliente, telefone_cliente, valor, descricao, wallet_id=None, taxa_alllogic=1.99, external_reference=None):
    """
    Gera cobrança PIX para agendamento com suporte a split de pagamento (taxa fixa da AllLogic).
    Retorna dicionário com: payment_id, copy_paste, qr_code_base64, expiracao
    """
    api_key, base_url, is_configured = _obter_asaas_config()
    timestamp = int(time.time() * 1000)

    if not is_configured:
        logger.info("[Agillex Pay] Modo simulação ativo. Gerando PIX de homologação.")
        mock_payload = (
            f"00020101021226840014br.gov.bcb.pix2562alllogic-pay-{timestamp}"
            f"5204000053039865802BR5920AllLogic Online6009Sao Paulo62070503***6304ABCD"
        )
        mock_qr = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        return {
            "payment_id": f"pay_mock_{timestamp}",
            "copy_paste": mock_payload,
            "qr_code_base64": mock_qr,
            "expiracao": "24 horas",
            "modo": "simulacao",
        }

    try:
        # 1. Criar ou buscar cliente
        cust_payload = {
            "name": nome_cliente,
            "mobilePhone": "".join(filter(str.isdigit, telefone_cliente)),
            "notificationDisabled": False,
        }
        req_cust = urllib.request.Request(
            f"{base_url}/customers",
            data=json.dumps(cust_payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "access_token": api_key},
            method="POST",
        )
        with urllib.request.urlopen(req_cust, timeout=10) as resp:
            cust_data = json.loads(resp.read().decode("utf-8"))
            customer_id = cust_data.get("id")

        # 2. Criar cobrança PIX
        today_str = time.strftime("%Y-%m-%d")
        pay_payload = {
            "customer": customer_id,
            "billingType": "PIX",
            "value": round(float(valor), 2),
            "dueDate": today_str,
            "description": descricao,
        }
        if external_reference:
            pay_payload["externalReference"] = str(external_reference)

        # Adicionar split de pagamento se houver wallet_id
        if wallet_id:
            valor_estabelecimento = round(float(valor) - float(taxa_alllogic), 2)
            if valor_estabelecimento > 0:
                pay_payload["split"] = [
                    {
                        "walletId": wallet_id,
                        "fixedValue": valor_estabelecimento,
                    }
                ]

        req_pay = urllib.request.Request(
            f"{base_url}/payments",
            data=json.dumps(pay_payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "access_token": api_key},
            method="POST",
        )
        with urllib.request.urlopen(req_pay, timeout=10) as resp:
            pay_data = json.loads(resp.read().decode("utf-8"))
            payment_id = pay_data.get("id")

        # 3. Buscar QR Code PIX
        req_qr = urllib.request.Request(
            f"{base_url}/payments/{payment_id}/pixQrCode",
            headers={"Content-Type": "application/json", "access_token": api_key},
            method="GET",
        )
        with urllib.request.urlopen(req_qr, timeout=10) as resp:
            qr_data = json.loads(resp.read().decode("utf-8"))
            return {
                "payment_id": payment_id,
                "copy_paste": qr_data.get("payload"),
                "qr_code_base64": qr_data.get("encodedImage"),
                "expiracao": qr_data.get("expirationDate"),
                "modo": "producao",
            }

    except Exception as e:
        logger.error(f"[Agillex Pay] Erro ao comunicar com Asaas: {e}")
        # Fallback de segurança para não travar o cliente se houver instabilidade
        mock_payload = (
            f"00020101021226840014br.gov.bcb.pix2562alllogic-pay-fallback-{timestamp}"
            f"5204000053039865802BR5920AllLogic Online6009Sao Paulo62070503***6304ABCD"
        )
        return {
            "payment_id": f"pay_fallback_{timestamp}",
            "copy_paste": mock_payload,
            "qr_code_base64": "",
            "expiracao": "24 horas",
            "modo": "fallback",
        }


def consultar_status_pix(payment_id):
    """Verifica se uma cobrança PIX foi liquidada."""
    api_key, base_url, is_configured = _obter_asaas_config()
    if not is_configured or payment_id.startswith("pay_mock_") or payment_id.startswith("pay_fallback_"):
        return {"pago": False, "status": "PENDING"}

    try:
        req = urllib.request.Request(
            f"{base_url}/payments/{payment_id}",
            headers={"Content-Type": "application/json", "access_token": api_key},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            status = data.get("status")
            is_paid = status in ("RECEIVED", "CONFIRMED")
            return {"pago": is_paid, "status": status}
    except Exception as e:
        logger.error(f"[Agillex Pay] Erro ao consultar pagamento {payment_id}: {e}")
        return {"pago": False, "status": "ERROR"}

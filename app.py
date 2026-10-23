import hashlib
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Flask, abort, g, jsonify, redirect, render_template, request, session, url_for, send_file
from flask_wtf.csrf import CSRFProtect
import io
import qrcode
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import SECRET_KEY
from database import (
    init_db,
    db_session,
    obter_todas_configuracoes,
    obter_configuracao,
    atualizar_configuracao,
    atualizar_configuracoes,
    obter_configuracoes_estabelecimento,
    atualizar_configuracoes_estabelecimento,
    admin_precisa_alterar_senha,
    admin_alterar_senha as db_admin_alterar_senha,
    admin_concluir_primeiro_acesso as db_admin_concluir_primeiro_acesso,
    obter_admin_por_email,
    criar_token_recuperacao,
    validar_token_recuperacao,
    redefinir_senha_com_token,
    criar_estabelecimento_com_admin,
    obter_estabelecimento_por_id,
    obter_estabelecimento_por_email,
    obter_estabelecimento_por_cnpj_cpf,
    obter_estabelecimento_por_slug,
    verificar_status_trial,
    obter_admin_com_estabelecimento,
    PLANOS_CONFIG,
    obter_limite_profissionais,
    atualizar_plano_estabelecimento,
)
from email_service import enviar_email_recuperacao

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

# CSRF Protection
csrf = CSRFProtect(app)

# Rate Limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

init_db()
import models

def normalizar_para_whatsapp(telefone):
    if not telefone:
        return ""
    digitos = "".join(c for c in str(telefone) if c.isdigit())
    if len(digitos) in (10, 11):
        return f"55{digitos}"
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        return digitos
    return digitos


def normalizar_para_tel(telefone):
    if not telefone:
        return ""
    digitos = "".join(c for c in str(telefone) if c.isdigit())
    if len(digitos) in (10, 11):
        return f"+55{digitos}"
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        return f"+{digitos}"
    return f"+{digitos}" if digitos else ""


def obter_nome_dia_semana(data_str):
    if not data_str:
        return ""
    try:
        dt = datetime.strptime(str(data_str)[:10], "%Y-%m-%d").date()
        dias = [
            "Segunda-feira",
            "Terça-feira",
            "Quarta-feira",
            "Quinta-feira",
            "Sexta-feira",
            "Sábado",
            "Domingo",
        ]
        return dias[dt.weekday()]
    except Exception:
        return ""


app.jinja_env.filters["zap_link"] = normalizar_para_whatsapp
app.jinja_env.filters["tel_link"] = normalizar_para_tel
app.jinja_env.filters["dia_semana_nome"] = obter_nome_dia_semana


@app.after_request
def adicionar_cabecalhos_cache_admin(response):
    if request.path.startswith("/admin") and not request.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

EXTENSOES_IMAGEM_PERMITIDAS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
TAMANHO_MAXIMO_IMAGEM = 2 * 1024 * 1024  # 2 MB


def _remover_arquivo_logo(caminho_relativo):
    if not caminho_relativo:
        return
    caminho_relativo = caminho_relativo.replace("\\", "/").lstrip("/")
    if not caminho_relativo.startswith("uploads/"):
        return
    caminho_completo = os.path.join(app.root_path, "static", caminho_relativo)
    try:
        if os.path.isfile(caminho_completo):
            os.remove(caminho_completo)
    except OSError:
        pass


def _validar_e_salvar_logotipo(arquivo_storage, logo_atual=""):
    if not arquivo_storage or not arquivo_storage.filename:
        return logo_atual, None

    nome_original = arquivo_storage.filename
    _, ext = os.path.splitext(nome_original)
    ext = ext.lower()

    if ext not in EXTENSOES_IMAGEM_PERMITIDAS:
        return None, "Formato de imagem inválido. Formatos aceitos: PNG, JPG, JPEG, WEBP e SVG."

    arquivo_storage.seek(0, os.SEEK_END)
    tamanho = arquivo_storage.tell()
    arquivo_storage.seek(0)

    if tamanho == 0:
        return None, "O arquivo enviado está vazio."
    if tamanho > TAMANHO_MAXIMO_IMAGEM:
        return None, "O logotipo deve ter no máximo 2 MB."

    conteudo_inicial = arquivo_storage.read(512)
    arquivo_storage.seek(0)

    valido = False
    if ext == ".png" and conteudo_inicial.startswith(b"\x89PNG\r\n\x1a\n"):
        valido = True
    elif ext in (".jpg", ".jpeg") and conteudo_inicial.startswith(b"\xff\xd8\xff"):
        valido = True
    elif (
        ext == ".webp"
        and conteudo_inicial.startswith(b"RIFF")
        and len(conteudo_inicial) >= 12
        and conteudo_inicial[8:12] == b"WEBP"
    ):
        valido = True
    elif ext == ".svg":
        texto = conteudo_inicial.decode("utf-8", errors="ignore").lower()
        if "<svg" in texto or "<?xml" in texto:
            valido = True

    if not valido:
        return None, "O arquivo selecionado não é uma imagem válida."

    pasta_uploads = os.path.join(app.root_path, "static", "uploads")
    os.makedirs(pasta_uploads, exist_ok=True)

    nome_arquivo = f"logo_{uuid.uuid4().hex[:12]}{ext}"
    caminho_destino = os.path.join(pasta_uploads, nome_arquivo)
    arquivo_storage.save(caminho_destino)

    if logo_atual and logo_atual != f"uploads/{nome_arquivo}":
        _remover_arquivo_logo(logo_atual)

    return f"uploads/{nome_arquivo}", None


def _carregar_config_template(estabelecimento_id=None):
    """Carrega configurações do banco para uso nos templates."""
    estab_id = estabelecimento_id or session.get("estabelecimento_id") or getattr(g, "estabelecimento_id", 1) or 1
    with db_session() as conn:
        config = obter_configuracoes_estabelecimento(conn, estab_id)
        est = obter_estabelecimento_por_id(conn, estab_id)

    logotipo = config.get("logotipo", "")
    if logotipo:
        caminho_disco = os.path.join(app.root_path, "static", logotipo)
        if not os.path.isfile(caminho_disco):
            logotipo = ""

    telefone = config.get("telefone_estabelecimento", "")
    telefone_limpo = re.sub(r"[^\d+]", "", telefone) if telefone else ""

    url_base = _obter_url_base_whatsapp()
    slug = (est.get("slug") if est else "") or ""
    if estab_id == 1 or slug in ("default", ""):
        url_publica_agendamento = f"{url_base}/"
    else:
        url_publica_agendamento = f"{url_base}/{slug}"

    dias_func = config.get("dias_funcionamento", "1,2,3,4,5,6")
    if isinstance(dias_func, str):
        dias_funcionamento_lista = [int(x.strip()) for x in dias_func.split(",") if x.strip()]
    elif isinstance(dias_func, (list, tuple)):
        dias_funcionamento_lista = [int(x) for x in dias_func]
    else:
        dias_funcionamento_lista = [0, 1, 2, 3, 4, 5]

    eh_demo = estab_id in ESTABELECIMENTOS_DEMONSTRACAO_IDS or slug in SLUGS_DEMONSTRACAO

    return {
        "nome_estabelecimento": config.get("nome_estabelecimento", "AllLogic Scheduler"),
        "telefone_estabelecimento": telefone,
        "telefone_limpo": telefone_limpo,
        "endereco_estabelecimento": config.get("endereco_estabelecimento", ""),
        "nome_publico": config.get("nome_publico", "AllLogic Scheduler"),
        "logotipo": logotipo,
        "dias_antecedencia": int(config.get("dias_antecedencia_agendamento", 14)),
        "dias_funcionamento": dias_funcionamento_lista,
        "estabelecimento_id": estab_id,
        "estabelecimento_slug": slug,
        "url_publica_agendamento": url_publica_agendamento,
        "eh_demo": eh_demo,
    }


@app.context_processor
def inject_config_template():
    estab_id = session.get("estabelecimento_id") or getattr(g, "estabelecimento_id", 1) or 1
    try:
        dados = _carregar_config_template(estab_id)
    except TypeError:
        dados = _carregar_config_template()
    if session.get("admin_logado") and session.get("estabelecimento_id"):
        try:
            with db_session() as conn:
                if estab_id != 1:
                    dados["info_trial"] = verificar_status_trial(conn, estab_id)
                est = obter_estabelecimento_por_id(conn, estab_id)
                if est:
                    dados["estabelecimento_atual"] = est
                    plano_nome = est.get("plano", "intermediario")
                    dados["plano_atual"] = plano_nome
                    dados["plano_config"] = PLANOS_CONFIG.get(plano_nome, PLANOS_CONFIG["intermediario"])
        except Exception:
            pass
    return dados


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def _validar_email(email):
    if not email or len(email) > 254:
        return False
    return bool(EMAIL_REGEX.match(email))


def _obter_url_base_whatsapp():
    """Retorna URL base com domínio público para garantir que links e QR codes funcionem externamente."""
    url_env = os.environ.get("APP_URL_BASE", "").strip().rstrip("/")
    if url_env:
        return url_env
    try:
        host = request.host if request else ""
        if not host or "127.0.0.1" in host or "localhost" in host:
            return "https://agenda.alllogiconline.com.br"
        scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
        if "alllogiconline.com.br" in host or request.headers.get("X-Forwarded-Ssl") == "on" or request.headers.get("X-Forwarded-ssl") == "on":
            scheme = "https"
        return f"{scheme}://{host}".rstrip("/")
    except Exception:
        return "https://agenda.alllogiconline.com.br"


def _obter_total_profissionais_ativos(conn, estab_id):
    """Retorna a contagem exata de profissionais ativos do estabelecimento (com isolamento multi-tenant)."""
    if estab_id and estab_id != 1:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM profissional WHERE ativo = TRUE AND estabelecimento_id = %s",
            (estab_id,)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM profissional WHERE ativo = TRUE AND (estabelecimento_id = 1 OR estabelecimento_id IS NULL)"
        ).fetchone()
    return row["c"] if row else 0


def login_requerido(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        if not session.get("admin_logado"):
            return redirect(url_for("admin_login"))
        if request.endpoint not in ("admin_configuracao_inicial", "admin_logout", "admin_trial_expirado"):
            usuario = session.get("admin_usuario")
            estab_id = session.get("estabelecimento_id")
            with db_session() as conn:
                if admin_precisa_alterar_senha(conn, usuario, estab_id):
                    return redirect(url_for("admin_configuracao_inicial"))
                if estab_id and estab_id != 1:
                    info_trial = verificar_status_trial(conn, estab_id)
                    if info_trial.get("expirado"):
                        return redirect(url_for("admin_trial_expirado"))
        return f(*args, **kwargs)

    return decorada


def _validar_configuracoes_operacionais(dados):
    try:
        antecedencia = int(dados["dias_antecedencia_agendamento"])
        intervalo = int(dados["intervalo_slot_minutos"])
        partes_dias = [parte.strip() for parte in dados["dias_funcionamento"].split(",")]
        dias = [int(parte) for parte in partes_dias]
        abertura = datetime.strptime(dados["horario_abertura"], "%H:%M")
        fechamento = datetime.strptime(dados["horario_fechamento"], "%H:%M")
    except (TypeError, ValueError):
        return "Informe dias, intervalo e horários válidos."

    if antecedencia < 0:
        return "A antecedência não pode ser negativa."
    if intervalo < 15 or intervalo % 15 != 0:
        return "O intervalo deve ser múltiplo de 15 minutos e no mínimo 15."
    if abertura.strftime("%H:%M") != dados["horario_abertura"]:
        return "Horário de abertura inválido."
    if fechamento.strftime("%H:%M") != dados["horario_fechamento"]:
        return "Horário de fechamento inválido."
    if abertura >= fechamento:
        return "O fechamento deve ser posterior à abertura."
    if not partes_dias or any(parte == "" for parte in partes_dias):
        return "Selecione ao menos um dia de funcionamento."
    if any(dia < 0 or dia > 6 for dia in dias) or len(set(dias)) != len(dias):
        return "Os dias devem ser únicos e estar entre 0 e 6."

    dados["dias_funcionamento"] = ",".join(str(dia) for dia in sorted(dias))
    return None


# ---------------------------------------------------------------------------
# Páginas públicas
# ---------------------------------------------------------------------------

ROTAS_RESERVADAS = {
    "admin", "api", "agillex", "experimente", "reserva", "agendamento",
    "static", "favicon.ico", "robots.txt", "sitemap.xml", "health", "healthz"
}

# Lista branca estrita de instâncias de demonstração pública
SLUGS_DEMONSTRACAO = {"default", "salao-premium", "petshop", "clinica-odonto", "barbearia"}
ESTABELECIMENTOS_DEMONSTRACAO_IDS = {1, 3, 4, 5}


def eh_slug_demonstracao(slug):
    if not slug:
        return False
    s = slug.strip().lower()
    return s in SLUGS_DEMONSTRACAO

DADOS_PORTFOLIO_POR_NICHO = {
    "petshop": {
        "subtitulo_publico": "Agende o cuidado, banho e tosa do seu pet com carinho e comodidade",
        "badge_reputacao": {
            "estrelas": "★★★★★",
            "nota": "4.9",
            "selo": "Espaço Pet Seguro & Higienizado",
            "atendimentos": "+350 pets atendidos",
        },
        "portfolio_itens": [
            {
                "img": "images/portfolio/petshop/pet_1.jpg",
                "tag": "Banho & Spa",
                "titulo": "Banho Relaxante",
                "subtitulo": "Espuma Hipoalergênica",
                "desc": "Banho morno com produtos dermatológicos especiais, massagem relaxante e secagem carinhosa sem estresse."
            },
            {
                "img": "images/portfolio/petshop/pet_2.jpg",
                "tag": "Tosa Tesoura",
                "titulo": "Tosa Teddy Bear",
                "subtitulo": "Poodle Toy Estilizado",
                "desc": "Acabamento primoroso na tesoura estilo ursinho de pelúcia, preservando o conforto e a higiene."
            },
            {
                "img": "images/portfolio/petshop/pet_3.jpg",
                "tag": "Pelagem Volumosa",
                "titulo": "Escovação & Desembolo",
                "subtitulo": "Spitz Alemão / Lulu",
                "desc": "Tratamento reconstrutor para pelagens densas, garantindo brilho, maciez e toque suave de nuvem."
            },
            {
                "img": "images/portfolio/petshop/pet_4.jpg",
                "tag": "Spa Felino",
                "titulo": "Spa & Higiene Felina",
                "subtitulo": "Gato Persa Tranquilo",
                "desc": "Ambiente silencioso e calmo com escovação delicada e manuseio suave adaptado para felinos."
            },
        ],
        "avaliacoes_clientes": [
            {
                "iniciais": "JM",
                "autor": "Juliana Mendes",
                "estrelas": "★★★★★",
                "data": "Há 2 dias",
                "texto": "O Thor voltou parecendo uma nuvem de tão macio e cheiroso! O Bruno teve muita paciência com ele, que sempre tinha medo de secador. O agendamento pelo link foi super rápido!"
            },
            {
                "iniciais": "RN",
                "autor": "Rodrigo Nogueira",
                "estrelas": "★★★★★",
                "data": "Há 4 dias",
                "texto": "Excelente estrutura e muito carinho com os animais. Receber o lembrete de horário no WhatsApp facilitou muito minha rotina corrida."
            },
            {
                "iniciais": "CB",
                "autor": "Carla Bezerra",
                "estrelas": "★★★★★",
                "data": "Há 1 semana",
                "texto": "A tosa na tesoura da Mel ficou uma perfeição! Melhor pet shop da região, recomendo de olhos fechados."
            },
        ],
        "politicas_atendimento": [
            {
                "icone": "🐾",
                "titulo": "Carteirinha de Vacinação em Dia:",
                "texto": "Para a segurança e saúde de todos os pets, solicitamos a comprovação das vacinas atualizadas."
            },
            {
                "icone": "⏰",
                "titulo": "Tolerância de 15 minutos:",
                "texto": "Para mantermos o ritmo calmo e individual de cada banho e tosa sem pressa."
            },
            {
                "icone": "🔄",
                "titulo": "Cancelamento ou Reagendamento:",
                "texto": "Gratuito avisando com pelo menos 2 horas de antecedência pelo WhatsApp."
            },
            {
                "icone": "📲",
                "titulo": "Avisos pelo WhatsApp:",
                "texto": "Você receberá confirmação e aviso imediato assim que seu pet estiver pronto para ser buscado."
            },
        ],
    },
    "clinica-odonto": {
        "subtitulo_publico": "Agende sua consulta odontológica e cuide do seu sorriso com especialistas",
        "badge_reputacao": {
            "estrelas": "★★★★★",
            "nota": "4.9",
            "selo": "Consultório Verificado & ANVISA",
            "atendimentos": "+500 pacientes atendidos",
        },
        "portfolio_itens": [
            {
                "img": "images/portfolio/odonto/odonto_1.jpg",
                "tag": "Estética Dental",
                "titulo": "Estética do Sorriso",
                "subtitulo": "Clareamento & Harmonia",
                "desc": "Sorriso radiante com clareamento a laser de alta potência e alinhamento funcional perfeito."
            },
            {
                "img": "images/portfolio/odonto/odonto_2.jpg",
                "tag": "Infraestrutura",
                "titulo": "Consultório High-Tech",
                "subtitulo": "Conforto & Tecnologia",
                "desc": "Ambiente acolhedor com equipamentos odontológicos ergonômicos e diagnóstico por imagem de alta definição."
            },
            {
                "img": "images/portfolio/odonto/odonto_3.jpg",
                "tag": "Ortodontia",
                "titulo": "Alinhadores Invisíveis",
                "subtitulo": "Correção Discreta",
                "desc": "Planejamento ortodôntico digital com placas transparentes removíveis, confortáveis e imperceptíveis."
            },
            {
                "img": "images/portfolio/odonto/odonto_4.jpg",
                "tag": "Prevenção",
                "titulo": "Profilaxia & Check-up",
                "subtitulo": "Saúde Bucal Integral",
                "desc": "Remoção ultrassônica de tártaro e polimento profilático para um sorriso saudável e protegido."
            },
        ],
        "avaliacoes_clientes": [
            {
                "iniciais": "EP",
                "autor": "Dr. Eduardo Paiva",
                "estrelas": "★★★★★",
                "data": "Há 2 dias",
                "texto": "Ambiente muito agradável e tecnologia de ponta. Fiz a limpeza e o clareamento com a Dra. Beatriz e o resultado superou minhas expectativas!"
            },
            {
                "iniciais": "RV",
                "autor": "Renata Vasconcellos",
                "estrelas": "★★★★★",
                "data": "Há 3 dias",
                "texto": "Pontualidade britânica no atendimento e muita clareza nas explicações. Agendar online e receber a confirmação no WhatsApp é uma comodidade fantástica."
            },
            {
                "iniciais": "TL",
                "autor": "Thiago Leite",
                "estrelas": "★★★★★",
                "data": "Há 6 dias",
                "texto": "Tinha receio de dentista por traumas passados, mas o atendimento humanizado do Dr. Marcos me deixou super tranquilo. Recomendo demais!"
            },
        ],
        "politicas_atendimento": [
            {
                "icone": "🩺",
                "titulo": "Biossegurança Rigorosa:",
                "texto": "Instrumentais 100% esterilizados em autoclave com monitoramento biológico estrito."
            },
            {
                "icone": "⏰",
                "titulo": "Chegada com 10 minutos de antecedência:",
                "texto": "Importante para atualização da anamnese e preparo calmo da consulta clínica."
            },
            {
                "icone": "🔄",
                "titulo": "Reagendamento Sem Custo:",
                "texto": "Avisando com pelo menos 4 horas de antecedência pelo WhatsApp ou link de reserva."
            },
            {
                "icone": "📲",
                "titulo": "Lembretes Automáticos:",
                "texto": "Notificações de confirmação de consulta enviadas no WhatsApp para você não esquecer."
            },
        ],
    },
    "barbearia": {
        "subtitulo_publico": "Agende seu corte e barba sem filas com mestres barbeiros",
        "badge_reputacao": {
            "estrelas": "★★★★★",
            "nota": "4.9",
            "selo": "Barbearia Premium Verificada",
            "atendimentos": "+600 cortes realizados",
        },
        "portfolio_itens": [
            {
                "img": "images/portfolio/barbearia/barber_1.jpg",
                "tag": "Fade Clássico",
                "titulo": "Skin Fade Degradê",
                "subtitulo": "Acabamento na Navalha",
                "desc": "Degradê suave e milimétrico com transição limpa e penteado finalizado com pomada matte de fixação média."
            },
            {
                "img": "images/portfolio/barbearia/barber_2.jpg",
                "tag": "Barboterapia",
                "titulo": "Ritual da Toalha Quente",
                "subtitulo": "Navalha & Óleos Nobres",
                "desc": "Abertura dos poros com toalha a vapor aromática, navalhete afiado e massagem facial revitalizante."
            },
            {
                "img": "images/portfolio/barbearia/barber_3.jpg",
                "tag": "Visagismo",
                "titulo": "Barba Alinhada & Estilo",
                "subtitulo": "Design & Contornos",
                "desc": "Escultura de barba adaptada ao formato do rosto com alinhamento preciso de bochechas e queixo."
            },
            {
                "img": "images/portfolio/barbearia/barber_4.jpg",
                "tag": "Ambiance",
                "titulo": "Vintage Lounge",
                "subtitulo": "Cerveja & Boa Música",
                "desc": "Espaço clássico acolhedor com poltronas retrô de couro e chopp gelado de cortesia na recepção."
            },
        ],
        "avaliacoes_clientes": [
            {
                "iniciais": "LS",
                "autor": "Lucas Silveira",
                "estrelas": "★★★★★",
                "data": "Há 1 dia",
                "texto": "Melhor barbearia de São Paulo! O atendimento do Gustavo no degradê é cirúrgico. E a cerveja gelada na recepção fecha com chave de ouro."
            },
            {
                "iniciais": "MP",
                "autor": "Marcelo Prado",
                "estrelas": "★★★★★",
                "data": "Há 3 dias",
                "texto": "Sensacional o combo de barba na toalha quente. Relaxa de verdade e a barba fica perfeita. Poder agendar online sem esperar na fila foi a melhor coisa."
            },
            {
                "iniciais": "GD",
                "autor": "Gabriel Diniz",
                "estrelas": "★★★★★",
                "data": "Há 5 dias",
                "texto": "Profissionais de altíssimo nível, ambiente com música boa e pontualidade no horário marcado. Sou cliente fixo toda quinzena!"
            },
        ],
        "politicas_atendimento": [
            {
                "icone": "⏱️",
                "titulo": "Sem Espera / Pontualidade:",
                "texto": "Atendimento rigoroso no horário agendado para respeitar o seu tempo e sua agenda."
            },
            {
                "icone": "☕",
                "titulo": "Lounge & Bebidas Cortesia:",
                "texto": "Chegue 10 minutinhos antes para relaxar no lounge e tomar um espresso ou chopp gelado."
            },
            {
                "icone": "🔄",
                "titulo": "Cancelamento Fácil:",
                "texto": "Pedimos aviso com pelo menos 1 hora de antecedência para liberar a vaga."
            },
            {
                "icone": "📲",
                "titulo": "Lembrete no WhatsApp:",
                "texto": "Aviso pontual no WhatsApp para você se programar e não esquecer seu corte."
            },
        ],
    },
    "default": {
        "subtitulo_publico": "Agende seu horário",
        "badge_reputacao": {
            "estrelas": "★★★★★",
            "nota": "4.9",
            "selo": "Profissional Verificado",
            "atendimentos": "+100 atendimentos",
        },
        "portfolio_itens": [
            {
                "img": "images/portfolio/portfolio_1.jpg",
                "tag": "Alongamento",
                "titulo": "Alongamento Fibra",
                "subtitulo": "Baby boomer & Ouro",
                "desc": "Técnica baby boomer com acabamento elegante em folha de ouro e alinhamento impecável."
            },
            {
                "img": "images/portfolio/portfolio_2.jpg",
                "tag": "Esmaltação Gel",
                "titulo": "Esmaltação em Gel",
                "subtitulo": "Vermelho Cherry",
                "desc": "Vermelho cherry clássico com cuticulagem alinhada e durabilidade de até 20 dias."
            },
            {
                "img": "images/portfolio/portfolio_3.jpg",
                "tag": "Nail Art",
                "titulo": "Francesinha & Chrome",
                "subtitulo": "Minimalista Chic",
                "desc": "Design fino com sorriso perfeito e detalhe chrome minimalista contemporâneo."
            },
            {
                "img": "images/portfolio/portfolio_4.jpg",
                "tag": "Especial",
                "titulo": "Marmorizada",
                "subtitulo": "Milky Ombre Suave",
                "desc": "Milky ombre sofisticada com efeito mármore delicado na filha única e acabamento primoroso."
            },
        ],
        "avaliacoes_clientes": [
            {
                "iniciais": "MC",
                "autor": "Mariana Costa",
                "estrelas": "★★★★★",
                "data": "Há 2 dias",
                "texto": "Atendimento impecável! O agendamento online foi super prático e o resultado ficou perfeito. Muito pontual e caprichosa!"
            },
            {
                "iniciais": "FA",
                "autor": "Fernanda Alves",
                "estrelas": "★★★★★",
                "data": "Há 4 dias",
                "texto": "Amei a facilidade de agendar direto pelo link da bio. O lembrete no WhatsApp me salvou. Super recomendo!"
            },
            {
                "iniciais": "BS",
                "autor": "Beatriz Silva",
                "estrelas": "★★★★★",
                "data": "Há 1 semana",
                "texto": "Profissional excelente, ambiente aconchegante e cuidado em cada detalhe. Já virei cliente fiel!"
            },
        ],
        "politicas_atendimento": [
            {
                "icone": "⏰",
                "titulo": "Tolerância de 10 minutos:",
                "texto": "Para manter os horários do dia sem atrasos, solicitamos pontualidade na sua chegada."
            },
            {
                "icone": "🔄",
                "titulo": "Cancelamento ou Reagendamento:",
                "texto": "Gratuito e simples, avisando com pelo menos 2 horas de antecedência pelo WhatsApp."
            },
            {
                "icone": "📲",
                "titulo": "Lembretes Automáticos:",
                "texto": "Você receberá confirmação e avisos no seu WhatsApp para não esquecer o horário."
            },
        ],
    }
}


def _obter_dados_nicho(slug=""):
    slug_limpo = (slug or "").strip().lower()
    if "pet" in slug_limpo:
        return DADOS_PORTFOLIO_POR_NICHO["petshop"]
    elif "odonto" in slug_limpo or "dent" in slug_limpo:
        return DADOS_PORTFOLIO_POR_NICHO["clinica-odonto"]
    elif "barb" in slug_limpo:
        return DADOS_PORTFOLIO_POR_NICHO["barbearia"]
    return DADOS_PORTFOLIO_POR_NICHO["default"]


@app.route("/")
def index():
    servicos = models.listar_servicos(apenas_ativos=True, estabelecimento_id=1)
    profissionais = models.listar_profissionais(apenas_ativos=True, estabelecimento_id=1)
    config = _carregar_config_template(1)
    dados_nicho = _obter_dados_nicho("default")
    return render_template(
        "index.html",
        servicos=servicos,
        profissionais=profissionais,
        slug="",
        **dados_nicho,
        **config,
    )


@app.route("/agendar/<slug>")
def agendar_por_slug(slug):
    slug_limpo = slug.strip().lower()
    with db_session() as conn:
        est = obter_estabelecimento_por_slug(conn, slug_limpo)
    if not est:
        abort(404)

    estab_id = est["id"]
    servicos = models.listar_servicos(apenas_ativos=True, estabelecimento_id=estab_id)
    profissionais = models.listar_profissionais(apenas_ativos=True, estabelecimento_id=estab_id)
    config = _carregar_config_template(estab_id)
    dados_nicho = _obter_dados_nicho(slug_limpo)

    return render_template(
        "index.html",
        servicos=servicos,
        profissionais=profissionais,
        estabelecimento=est,
        slug=slug_limpo,
        **dados_nicho,
        **config,
    )


@app.route("/<slug>")
def rota_slug_estabelecimento(slug):
    slug_limpo = slug.strip().lower()
    if slug_limpo in ROTAS_RESERVADAS:
        abort(404)
    with db_session() as conn:
        est = obter_estabelecimento_por_slug(conn, slug_limpo)
    if not est:
        abort(404)
    return agendar_por_slug(slug_limpo)


@app.route("/agendamento/sucesso/<int:agendamento_id>")
def agendamento_sucesso(agendamento_id):
    agendamento = models.obter_agendamento_completo(agendamento_id)
    if not agendamento:
        return redirect(url_for("index"))

    estab_id = agendamento.get("estabelecimento_id") or 1
    try:
        config_template = _carregar_config_template(estab_id)
    except TypeError:
        config_template = _carregar_config_template()
    url_base_local = request.host_url.rstrip("/")
    url_base_zap = _obter_url_base_whatsapp()

    from whatsapp_service import formatar_mensagem_cliente, gerar_link_wa_me
    texto_zap = formatar_mensagem_cliente(agendamento, config_template, url_base_zap)
    link_whatsapp = gerar_link_wa_me(agendamento.get("cliente_telefone"), texto_zap)

    return render_template(
        "sucesso.html",
        agendamento=agendamento,
        link_whatsapp=link_whatsapp,
        url_reserva=f"{url_base_local}/reserva/{agendamento.get('token_acesso')}" if agendamento.get("token_acesso") else "",
        **config_template,
    )


@app.route("/admin/qrcode")
@app.route("/admin/qrcode/<slug>")
@app.route("/admin/estabelecimento/qrcode/<slug>")
@login_requerido
def admin_estabelecimento_qrcode(slug=None):
    """Gera o QR code em PNG para divulgação da página pública de agendamento do estabelecimento."""
    estab_id = session.get("estabelecimento_id") or 1
    if not slug:
        with db_session() as conn:
            est = obter_estabelecimento_por_id(conn, estab_id)
            slug = est.get("slug") if est else "default"
    base_url = _obter_url_base_whatsapp()
    if not slug or slug in ("default", ""):
        public_url = f"{base_url}/"
    else:
        public_url = f"{base_url}/agendar/{slug}"
    img = qrcode.make(public_url)
    buf = io.BytesIO()
    try:
        img.save(buf, format="PNG")
    except TypeError:
        img.save(buf)
    buf.seek(0)
    nome_slug = slug if slug and slug != "default" else "agenda"
    return send_file(
        buf,
        mimetype="image/png",
        as_attachment=True,
        download_name=f"qrcode-{nome_slug}.png",
    )


@app.route("/reserva/<token>")
def public_ver_reserva(token):
    agendamento = models.obter_agendamento_por_token(token)
    config_template = _carregar_config_template()
    if not agendamento:
        return render_template(
            "reserva.html",
            agendamento=None,
            erro="Reserva não encontrada. Verifique o link informado.",
            **config_template,
        )

    url_base_zap = _obter_url_base_whatsapp()
    from whatsapp_service import formatar_mensagem_cliente, gerar_link_wa_me, formatar_telefone_br
    texto_zap = formatar_mensagem_cliente(agendamento, config_template, url_base_zap)
    link_whatsapp = gerar_link_wa_me(agendamento.get("cliente_telefone"), texto_zap)
    telefone_formatado = formatar_telefone_br(config_template.get("telefone_estabelecimento", ""))

    sucesso = request.args.get("sucesso")
    erro = request.args.get("erro")

    return render_template(
        "reserva.html",
        agendamento=agendamento,
        link_whatsapp=link_whatsapp,
        telefone_formatado=telefone_formatado,
        sucesso=sucesso,
        erro=erro,
        **config_template,
    )


@app.route("/reserva/<token>/cancelar", methods=["POST"])
def public_cancelar_reserva(token):
    agendamento = models.obter_agendamento_por_token(token)
    if not agendamento:
        return redirect(url_for("index"))

    ok, erro = models.cancelar_agendamento_por_cliente(token)
    if not ok:
        return redirect(url_for("public_ver_reserva", token=token, erro=erro))

    try:
        from whatsapp_service import notificar_cancelamento_whatsapp
        url_base = request.host_url.rstrip("/")
        notificar_cancelamento_whatsapp(agendamento["id"], url_base=url_base)
    except Exception as e:
        app.logger.warning(f"Erro ao disparar cancelamento WhatsApp: {e}")

    return redirect(url_for("public_ver_reserva", token=token, sucesso="Seu agendamento foi cancelado com sucesso."))


@app.route("/experimente")
def experimente():
    return redirect(url_for("agillex"), code=302)


@app.route("/agillex", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def agillex():
    erro = None
    valores = {}
    config = _carregar_config_template()

    # Leitura e sanitização do plano selecionado via query string ou padrão
    plano_selecionado = request.args.get("plano", "intermediario").strip().lower()
    if plano_selecionado not in PLANOS_CONFIG:
        plano_selecionado = "intermediario"
    valores["plano"] = plano_selecionado

    if request.method == "POST":
        nome_responsavel = request.form.get("nome_responsavel", "").strip()
        nome_estabelecimento = request.form.get("nome_estabelecimento", "").strip()
        cnpj_cpf = request.form.get("cnpj_cpf", "").strip()
        telefone = request.form.get("telefone", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")
        termos = request.form.get("termos") == "1"
        plano = request.form.get("plano", plano_selecionado).strip().lower()
        if plano not in PLANOS_CONFIG:
            plano = "intermediario"

        valores = {
            "nome_responsavel": nome_responsavel,
            "nome_estabelecimento": nome_estabelecimento,
            "cnpj_cpf": cnpj_cpf,
            "telefone": telefone,
            "email": email,
            "termos": termos,
            "plano": plano,
        }

        digitos_doc = re.sub(r"\D", "", cnpj_cpf)
        digitos_tel = re.sub(r"\D", "", telefone)

        if not (nome_responsavel and nome_estabelecimento and cnpj_cpf and telefone and email and senha and confirmar_senha):
            erro = "Por favor, preencha todos os campos obrigatórios."
        elif not termos:
            erro = "Você precisa concordar com os termos de uso para ativar o período de teste de 14 dias."
        elif not _validar_email(email):
            erro = "Por favor, informe um endereço de e-mail válido."
        elif len(digitos_doc) not in (11, 14):
            erro = "O documento informado deve ser um CPF (11 dígitos) ou CNPJ (14 dígitos) válido."
        elif len(digitos_tel) < 10:
            erro = "O telefone informado deve conter DDD e pelo menos 10 dígitos numéricos."
        elif len(senha) < 8:
            erro = "A senha deve ter no mínimo 8 caracteres."
        elif senha != confirmar_senha:
            erro = "A confirmação de senha não confere com a senha informada."
        else:
            with db_session() as conn:
                admin_existente = conn.execute(
                    "SELECT id FROM admin WHERE LOWER(usuario) = %s OR (email IS NOT NULL AND LOWER(email) = %s)",
                    (email, email),
                ).fetchone()
                estab_email = obter_estabelecimento_por_email(conn, email)
                if admin_existente or estab_email:
                    erro = "Este endereço de e-mail já está cadastrado. Se já possui uma conta, faça login no painel."
                else:
                    estab_doc = obter_estabelecimento_por_cnpj_cpf(conn, cnpj_cpf)
                    if estab_doc and estab_doc["status"] == "ativo":
                        erro = "Já existe uma avaliação de 14 dias ativa para este CNPJ/CPF."
                    else:
                        from werkzeug.security import generate_password_hash
                        senha_hash = generate_password_hash(senha)
                        novo_estab = criar_estabelecimento_com_admin(
                            conn,
                            nome_estabelecimento=nome_estabelecimento,
                            nome_responsavel=nome_responsavel,
                            cnpj_cpf=cnpj_cpf,
                            email=email,
                            telefone=telefone,
                            usuario=email,
                            senha_hash=senha_hash,
                            plano=plano,
                        )
                        session["admin_logado"] = True
                        session["admin_usuario"] = email
                        session["estabelecimento_id"] = novo_estab["estabelecimento_id"]
                        session["estabelecimento_plano"] = novo_estab["plano"]

                        return redirect(url_for("admin_estabelecimento", boas_vindas="1"))

    return render_template(
        "agillex.html",
        erro=erro,
        valores=valores,
        planos_config=PLANOS_CONFIG,
        plano_selecionado=valores.get("plano", "intermediario"),
        **config,
    )


@app.route("/admin/trial-expirado")
def admin_trial_expirado():
    if not session.get("admin_logado"):
        return redirect(url_for("admin_login"))
    estab_id = session.get("estabelecimento_id")
    with db_session() as conn:
        info_trial = verificar_status_trial(conn, estab_id)
    return render_template(
        "admin_trial_expirado.html",
        info_trial=info_trial,
        **_carregar_config_template(),
    )


@app.route("/admin/upgrade", methods=["GET", "POST"])
@login_requerido
def admin_upgrade():
    estab_id = session.get("estabelecimento_id")
    with db_session() as conn:
        estab = obter_estabelecimento_por_id(conn, estab_id)
        if not estab:
            return redirect(url_for("admin_dashboard"))

        info_trial = (
            verificar_status_trial(conn, estab_id)
            if estab_id != 1
            else {"status": "ativo", "expirado": False, "dias_restantes": 3650}
        )
        total_profissionais = _obter_total_profissionais_ativos(conn, estab_id)
        plano_atual = estab.get("plano", "intermediario")
        cfg_atual = PLANOS_CONFIG.get(plano_atual, PLANOS_CONFIG["intermediario"])
        limite_atual = cfg_atual["limite_profissionais"]

        import urllib.parse

        msg_sucesso = None
        erro = None
        if request.method == "POST":
            novo_plano = request.form.get("novo_plano", "").strip().lower()
            if novo_plano in PLANOS_CONFIG:
                checkout_url = (
                    f"https://hub.alllogiconline.com.br/checkout?modulo=agenda&plano=agenda_{novo_plano}"
                    f"&email={urllib.parse.quote(estab.get('email') or '')}"
                    f"&nome={urllib.parse.quote(estab.get('nome_responsavel') or estab.get('nome') or '')}"
                )
                return redirect(checkout_url)
            else:
                erro = "Plano selecionado é inválido."

        msg_whatsapp = (
            f"Olá! Sou da empresa {estab['nome']} (responsável: {estab.get('nome_responsavel') or ''}, "
            f"email: {estab.get('email') or ''}). "
            f"Gostaria de solicitar uma proposta corporativa sob medida para mais de 10 profissionais no Agillex Agenda."
        )
        link_whatsapp_upgrade = (
            f"https://wa.me/5511966381915?text={urllib.parse.quote(msg_whatsapp)}"
        )

        return render_template(
            "admin_upgrade.html",
            estab=estab,
            info_trial=info_trial,
            plano_atual=plano_atual,
            cfg_atual=cfg_atual,
            total_profissionais=total_profissionais,
            limite_atual=limite_atual,
            planos_config=PLANOS_CONFIG,
            link_whatsapp_upgrade=link_whatsapp_upgrade,
            msg_sucesso=msg_sucesso,
            erro=erro,
            pagina_ativa="upgrade",
            **_carregar_config_template(),
        )


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

@app.route("/api/services")
def api_services():
    estab_id = request.args.get("estabelecimento_id", type=int)
    slug = request.args.get("slug")
    if not estab_id and slug:
        with db_session() as conn:
            est = obter_estabelecimento_por_slug(conn, slug)
            if est:
                estab_id = est["id"]
    return jsonify(models.listar_servicos(apenas_ativos=True, estabelecimento_id=estab_id))


@app.route("/api/professionals")
def api_professionals():
    estab_id = request.args.get("estabelecimento_id", type=int)
    slug = request.args.get("slug")
    if not estab_id and slug:
        with db_session() as conn:
            est = obter_estabelecimento_por_slug(conn, slug)
            if est:
                estab_id = est["id"]

    servico_ids = request.args.getlist("servico_id", type=int)
    if not servico_ids:
        return jsonify(models.listar_profissionais(apenas_ativos=True, estabelecimento_id=estab_id))

    servico_ids = list(dict.fromkeys(servico_ids))
    if any(
        not (servico := models.obter_servico(servico_id)) or not servico["ativo"]
        for servico_id in servico_ids
    ):
        return jsonify({"erro": "Serviço inválido."}), 400
    return jsonify(models.listar_profissionais_para_servicos(servico_ids, estabelecimento_id=estab_id))


@app.route("/api/horarios-disponiveis")
@app.route("/api/availability")
def api_availability():
    profissional_id = request.args.get("profissional_id", type=int)
    data_str = request.args.get("data", type=str)
    ignorar_agendamento_id = request.args.get("ignorar_agendamento_id", type=int)

    servico_ids = request.args.getlist("servico_id", type=int)
    if not servico_ids:
        servico_id = request.args.get("servico_id", type=int)
        if servico_id:
            servico_ids = [servico_id]

    if not profissional_id or not servico_ids or not data_str:
        return jsonify({
            "erro": "Parâmetros obrigatórios: profissional_id, servico_id, data"
        }), 400

    try:
        datetime.strptime(data_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"erro": "Data inválida. Use o formato YYYY-MM-DD."}), 400

    servico_ids = list(dict.fromkeys(servico_ids))

    if any(
        not (servico := models.obter_servico(servico_id)) or not servico["ativo"]
        for servico_id in servico_ids
    ):
        return jsonify({"erro": "Serviço inválido."}), 400

    profissional = models.obter_profissional(profissional_id)
    if not profissional or not profissional["ativo"]:
        return jsonify({"erro": "Profissional inválido."}), 400

    horarios = models.horarios_disponiveis(
        profissional_id,
        data_str,
        servico_ids,
        ignorar_agendamento_id=ignorar_agendamento_id,
    )
    return jsonify({"horarios": horarios})


@app.route("/api/appointments", methods=["POST"])
def api_appointments():
    dados = request.get_json(silent=True) or {}

    cliente_nome = (dados.get("cliente_nome") or "").strip()
    cliente_telefone = (dados.get("cliente_telefone") or "").strip()

    servico_ids = dados.get("servico_ids")
    if servico_ids is None:
        servico_id = dados.get("servico_id")
        servico_ids = [servico_id] if servico_id else []

    if isinstance(servico_ids, int):
        servico_ids = [servico_ids]

    profissional_id = dados.get("profissional_id")
    data_str = dados.get("data")
    hora_str = dados.get("hora")
    estabelecimento_id = dados.get("estabelecimento_id")
    slug = dados.get("slug")
    if not estabelecimento_id and slug:
        with db_session() as conn:
            est = obter_estabelecimento_por_slug(conn, slug)
            if est:
                estabelecimento_id = est["id"]

    erros = []
    if not cliente_nome:
        erros.append("Nome é obrigatório.")
    if not cliente_telefone:
        erros.append("Telefone é obrigatório.")
    if not isinstance(servico_ids, list) or not servico_ids:
        erros.append("Serviço é obrigatório.")
    if not profissional_id:
        erros.append("Profissional é obrigatório.")
    if not data_str:
        erros.append("Data é obrigatória.")
    if not hora_str:
        erros.append("Horário é obrigatório.")

    estab_final = estabelecimento_id or 1
    if not erros:
        servico_ids = list(dict.fromkeys(servico_ids))

        for servico_id in servico_ids:
            servico = models.obter_servico(servico_id) if type(servico_id) is int else None
            if not servico or not servico["ativo"]:
                erros.append("Serviço inválido.")
                break

        profissional = (
            models.obter_profissional(profissional_id)
            if type(profissional_id) is int
            else None
        )
        if not profissional or not profissional["ativo"]:
            erros.append("Profissional inválido.")

        if profissional and profissional.get("estabelecimento_id"):
            estab_final = profissional["estabelecimento_id"]

        if not erros and not models.data_permitida(data_str, estabelecimento_id=estab_final):
            erros.append("Data indisponível para agendamento.")

    if erros:
        return jsonify({"erro": " ".join(erros)}), 400

    agendamento_id, erro = models.criar_agendamento(
        cliente_nome,
        cliente_telefone,
        servico_ids,
        profissional_id,
        data_str,
        hora_str,
        estabelecimento_id=estab_final,
    )

    if erro:
        return jsonify({"erro": erro}), 409

    ag = models.obter_agendamento_completo(agendamento_id)
    token_acesso = ag["token_acesso"] if ag and "token_acesso" in ag else None

    # Agillex Pay — Gestão de Pagamentos Online & Sinal
    pagamento_requerido = False
    pix_dados = None
    try:
        with db_session() as conn:
            config_estab = obter_configuracoes_estabelecimento(conn, estab_final)

        if config_estab.get("pagamento_online_ativo"):
            tipo_pagamento = config_estab.get("pagamento_tipo") or "sinal"
            if tipo_pagamento == "sinal":
                valor_cobranca = float(config_estab.get("pagamento_sinal_valor") or 30.00)
            else:
                valor_cobranca = float(ag.get("servico_preco") or 0.0)

            if valor_cobranca > 0:
                taxa_alllogic = float(config_estab.get("taxa_intermediacao_fixa") or 1.99)
                valor_liquido = max(0.0, round(valor_cobranca - taxa_alllogic, 2))
                from asaas_service import gerar_pix_agendamento
                pix_dados = gerar_pix_agendamento(
                    nome_cliente=cliente_nome,
                    telefone_cliente=cliente_telefone,
                    valor=valor_cobranca,
                    descricao=f"Agendamento #{agendamento_id} - {config_estab.get('nome_estabelecimento')}",
                    wallet_id=config_estab.get("asaas_wallet_id"),
                    taxa_alllogic=taxa_alllogic,
                    external_reference=str(agendamento_id),
                )
                models.atualizar_pagamento_agendamento(
                    agendamento_id=agendamento_id,
                    status="pendente",
                    asaas_payment_id=pix_dados.get("payment_id"),
                    pix_copia_cola=pix_dados.get("copy_paste"),
                    pix_qr_code=pix_dados.get("qr_code_base64"),
                    valor=valor_cobranca,
                    taxa=taxa_alllogic,
                    valor_liquido=valor_liquido,
                )
                pagamento_requerido = True
        else:
            models.atualizar_pagamento_agendamento(
                agendamento_id=agendamento_id,
                status="isento",
            )
    except Exception as e:
        app.logger.error(f"[Agillex Pay] Erro ao processar cobrança online do agendamento {agendamento_id}: {e}")

    # Dispara notificações de WhatsApp via Evolution API em background
    try:
        from whatsapp_service import notificar_novo_agendamento_whatsapp
        url_base_zap = _obter_url_base_whatsapp()
        notificar_novo_agendamento_whatsapp(agendamento_id, url_base=url_base_zap)
    except Exception as e:
        app.logger.warning(f"Erro ao disparar notificações de WhatsApp: {e}")

    resposta = {"agendamento_id": agendamento_id, "token_acesso": token_acesso, "pagamento_requerido": pagamento_requerido}
    if pix_dados:
        resposta["pix"] = pix_dados
    return jsonify(resposta), 201


@app.route("/api/agendamento/<int:agendamento_id>/pix-status", methods=["GET"])
def api_agendamento_pix_status(agendamento_id):
    ag = models.obter_agendamento_completo(agendamento_id)
    if not ag:
        return jsonify({"erro": "Agendamento não encontrado"}), 404

    status_atual = ag.get("pagamento_status") or "isento"
    if status_atual == "pago":
        return jsonify({"pago": True, "status": "CONFIRMED", "pago_em": str(ag.get("pago_em"))})

    if status_atual in ("isento", "nao_aplicavel"):
        return jsonify({"pago": True, "status": "EXEMPT"})

    payment_id = ag.get("asaas_payment_id")
    if payment_id:
        from asaas_service import consultar_status_pix
        resultado = consultar_status_pix(payment_id)
        if resultado.get("pago"):
            models.atualizar_pagamento_agendamento(agendamento_id, status="pago")
            return jsonify({"pago": True, "status": resultado.get("status", "CONFIRMED")})

    return jsonify({"pago": False, "status": status_atual})


@app.route("/api/webhooks/asaas-agendamento", methods=["POST"])
def webhook_asaas_agendamento():
    payload = request.get_json(silent=True) or {}
    evento = payload.get("event")
    payment = payload.get("payment") or {}

    payment_id = payment.get("id")
    external_ref = payment.get("externalReference")

    app.logger.info(f"[Webhook Asaas Agendamento] Evento: {evento} | ID: {payment_id} | Ref: {external_ref}")

    if evento in ("PAYMENT_RECEIVED", "PAYMENT_CONFIRMED"):
        ag = None
        if external_ref and external_ref.isdigit():
            ag = models.obter_agendamento_completo(int(external_ref))
        if not ag and payment_id:
            ag = models.obter_agendamento_por_asaas_id(payment_id)

        if ag:
            ag_id = ag["id"]
            models.atualizar_pagamento_agendamento(ag_id, status="pago")
            app.logger.info(f"[Webhook Asaas Agendamento] Pagamento confirmado com sucesso para agendamento #{ag_id}")
            return jsonify({"status": "success", "agendamento_id": ag_id}), 200

    return jsonify({"status": "ignored"}), 200


@app.route("/admin/demo/<slug>")
@app.route("/admin/acesso/<slug>")
def admin_acesso_demo(slug):
    slug_limpo = (slug or "default").strip().lower()
    if slug_limpo in ("", "default"):
        slug_limpo = "default"

    # Isolamento de segurança: apenas slugs e estabelecimentos da whitelist de demonstração
    if not eh_slug_demonstracao(slug_limpo):
        return redirect(url_for("admin_login", slug=slug_limpo))

    with db_session() as conn:
        est = obter_estabelecimento_por_slug(conn, slug_limpo)
    if not est:
        abort(404)

    estab_id = est["id"]
    if estab_id not in ESTABELECIMENTOS_DEMONSTRACAO_IDS:
        return redirect(url_for("admin_login", slug=slug_limpo))

    session["admin_logado"] = True
    session["admin_usuario"] = "admin"
    session["estabelecimento_id"] = estab_id
    session["estabelecimento_slug"] = slug_limpo
    session["flash_sucesso"] = f"Painel Administrativo: {est['nome']}"
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/trocar/<slug>")
@login_requerido
def admin_trocar_estabelecimento(slug):
    slug_limpo = (slug or "").strip().lower()
    if not eh_slug_demonstracao(slug_limpo):
        session["flash_erro"] = "Acesso negado: troca rápida restrita a instâncias de demonstração."
        return redirect(url_for("admin_dashboard"))
    return admin_acesso_demo(slug_limpo)


@app.route("/admin/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def admin_login():
    erro = None
    sucesso = None
    if request.args.get("redefinida") == "1":
        sucesso = "Senha redefinida com sucesso. Faça login com a sua nova senha."

    slug_alvo = (request.args.get("slug") or request.args.get("estab") or "").strip().lower()
    target_estab_id = None
    if slug_alvo:
        with db_session() as conn:
            est_alvo = obter_estabelecimento_por_slug(conn, slug_alvo)
            if est_alvo:
                target_estab_id = est_alvo["id"]

    estab_id_config = target_estab_id or session.get("estabelecimento_id") or 1
    config = _carregar_config_template(estab_id_config)
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")
        post_estab_id = request.form.get("estabelecimento_id")
        if post_estab_id:
            try:
                target_estab_id = int(post_estab_id)
            except ValueError:
                pass
        admin_data = models.verificar_admin(usuario, senha, estabelecimento_id=target_estab_id or session.get("estabelecimento_id"))
        if admin_data:
            admin_usuario = admin_data["usuario"] if isinstance(admin_data, dict) else usuario
            session["admin_logado"] = True
            session["admin_usuario"] = admin_usuario
            if isinstance(admin_data, dict) and admin_data.get("estabelecimento_id"):
                session["estabelecimento_id"] = admin_data["estabelecimento_id"]
            else:
                with db_session() as conn:
                    adm = conn.execute("SELECT estabelecimento_id FROM admin WHERE usuario = %s", (admin_usuario,)).fetchone()
                    if adm and adm["estabelecimento_id"]:
                        session["estabelecimento_id"] = adm["estabelecimento_id"]
            with db_session() as conn:
                if admin_precisa_alterar_senha(conn, admin_usuario, session.get("estabelecimento_id")):
                    return redirect(url_for("admin_configuracao_inicial"))
            return redirect(url_for("admin_dashboard"))
        erro = "Usuário ou senha inválidos."
    return render_template("admin_login.html", erro=erro, sucesso=sucesso, target_estab_id=target_estab_id, **config)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin/servicos")
@login_requerido
def admin_servicos():
    estab_id = session.get("estabelecimento_id") or 1
    servicos = models.listar_servicos_admin(estabelecimento_id=estab_id)
    erro = session.pop("flash_erro", None)
    sucesso = session.pop("flash_sucesso", None)
    return render_template(
        "admin_servicos.html",
        servicos=servicos,
        erro=erro,
        sucesso=sucesso,
        **_carregar_config_template(estab_id),
    )


@app.route("/admin/servicos/novo", methods=["GET", "POST"])
@login_requerido
def admin_servico_novo():
    estab_id = session.get("estabelecimento_id") or 1
    erro = None
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        descricao = request.form.get("descricao", "").strip()
        preco = request.form.get("preco", "")
        duracao_minutos = request.form.get("duracao_minutos", "")
        ativo = request.form.get("ativo") == "on"

        servico_id, erro = models.criar_servico(
            nome,
            preco,
            duracao_minutos,
            ativo,
            descricao,
            estabelecimento_id=estab_id,
        )
        if servico_id:
            return redirect(url_for("admin_servicos"))

    return render_template(
        "admin_servico_form.html",
        erro=erro,
        servico=None,
        titulo="Novo serviço",
        **_carregar_config_template(estab_id),
    )


@app.route("/admin/servicos/<int:servico_id>/editar", methods=["GET", "POST"])
@login_requerido
def admin_servico_editar(servico_id):
    servico = models.obter_servico(servico_id)
    if not servico:
        return redirect(url_for("admin_servicos"))

    erro = None
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        descricao = request.form.get("descricao", "").strip()
        preco = request.form.get("preco", "")
        duracao_minutos = request.form.get("duracao_minutos", "")
        ativo = request.form.get("ativo") == "on"

        ok, erro = models.atualizar_servico(
            servico_id,
            nome,
            preco,
            duracao_minutos,
            ativo,
            descricao,
        )
        if ok:
            return redirect(url_for("admin_servicos"))

    return render_template(
        "admin_servico_form.html",
        erro=erro,
        servico=servico,
        titulo="Editar serviço",
        **_carregar_config_template(),
    )


@app.route("/admin/servicos/<int:servico_id>/toggle", methods=["POST"])
@login_requerido
def admin_servico_toggle(servico_id):
    servico = models.obter_servico(servico_id)
    if servico:
        models.alterar_status_servico(servico_id, not servico["ativo"])
    return redirect(url_for("admin_servicos"))


@app.route("/admin/servicos/<int:servico_id>/excluir", methods=["POST"])
@login_requerido
def admin_servico_excluir(servico_id):
    estab_id = session.get("estabelecimento_id") or 1
    ok, erro = models.excluir_servico(servico_id, estabelecimento_id=estab_id)
    if not ok:
        session["flash_erro"] = erro
    else:
        session["flash_sucesso"] = "Serviço excluído com sucesso."
    return redirect(url_for("admin_servicos"))


@app.route("/admin/profissionais")
@login_requerido
def admin_profissionais():
    estab_id = session.get("estabelecimento_id") or 1
    profissionais = models.listar_profissionais_admin(estabelecimento_id=estab_id)
    servicos = models.listar_servicos_admin(estabelecimento_id=estab_id)
    total_ativos = sum(1 for p in profissionais if p.get("ativo"))
    with db_session() as conn:
        estab = obter_estabelecimento_por_id(conn, estab_id)
    plano = estab.get("plano", "intermediario") if estab else "intermediario"
    limite = obter_limite_profissionais(plano)
    cfg_plano = PLANOS_CONFIG.get(plano, PLANOS_CONFIG["intermediario"])
    erro = session.pop("flash_erro", None)
    sucesso = session.pop("flash_sucesso", None)

    return render_template(
        "admin_profissionais.html",
        profissionais=profissionais,
        servicos=servicos,
        total_ativos=total_ativos,
        limite_profissionais=limite,
        atingiu_limite=(total_ativos >= limite),
        plano_config=cfg_plano,
        erro=erro,
        sucesso=sucesso,
        **_carregar_config_template(estab_id),
    )


@app.route("/admin/profissionais/novo", methods=["GET", "POST"])
@login_requerido
def admin_profissional_novo():
    estab_id = session.get("estabelecimento_id") or 1
    erro = None
    servicos = models.listar_servicos_admin(estabelecimento_id=estab_id)
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        ativo = request.form.get("ativo") == "on"
        servico_ids = request.form.getlist("servicos", type=int)

        with db_session() as conn:
            estab = obter_estabelecimento_por_id(conn, estab_id)
            plano = estab.get("plano", "intermediario") if estab else "intermediario"
            limite = obter_limite_profissionais(plano)
            total_ativos = _obter_total_profissionais_ativos(conn, estab_id)
            if ativo and total_ativos >= limite:
                cfg = PLANOS_CONFIG.get(plano, PLANOS_CONFIG["intermediario"])
                erro = (
                    f"Limite atingido: O seu plano atual ({cfg['nome']}) permite no máximo "
                    f"{limite} profissional(is) ativo(s). Faça o upgrade do seu plano para cadastrar mais profissionais."
                )

        if not erro:
            profissional_id, erro = models.criar_profissional(nome, ativo, servico_ids, estabelecimento_id=estab_id)
            if profissional_id:
                return redirect(url_for("admin_profissionais"))

    return render_template(
        "admin_profissional_form.html",
        erro=erro,
        profissional=None,
        servicos=servicos,
        titulo="Novo profissional",
        **_carregar_config_template(estab_id),
    )


@app.route("/admin/profissionais/<int:profissional_id>/editar", methods=["GET", "POST"])
@login_requerido
def admin_profissional_editar(profissional_id):
    estab_id = session.get("estabelecimento_id") or 1
    profissional = models.obter_profissional(profissional_id)
    if not profissional:
        return redirect(url_for("admin_profissionais"))

    servicos = models.listar_servicos_admin(estabelecimento_id=estab_id)
    lista_profissionais = models.listar_profissionais_admin(estabelecimento_id=estab_id)
    profissional_com_servicos = next(
        (item for item in lista_profissionais if item["id"] == profissional_id),
        None,
    )
    servico_ids_atuais = profissional_com_servicos["servico_ids"] if profissional_com_servicos else []

    disponibilidade = models.obter_disponibilidade_profissional(profissional_id)
    erro = None
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        ativo = request.form.get("ativo") == "on"
        servico_ids = request.form.getlist("servicos", type=int)

        itens_disp = []
        for d in models.DIAS_DA_SEMANA:
            dia_num = d["numero"]
            dia_ativo = request.form.get(f"disp_ativo_{dia_num}") == "on"
            entrada = request.form.get(f"disp_entrada_{dia_num}", "").strip()
            saida = request.form.get(f"disp_saida_{dia_num}", "").strip()
            itens_disp.append({
                "dia_semana": dia_num,
                "nome_dia": d["nome"],
                "ativo": dia_ativo,
                "horario_entrada": entrada,
                "horario_saida": saida,
            })

        disponibilidade = itens_disp

        ok_disp, erro_disp = models.validar_disponibilidade_profissional(itens_disp)
        if not ok_disp:
            erro = erro_disp
        elif ativo and not profissional["ativo"]:
            with db_session() as conn:
                estab = obter_estabelecimento_por_id(conn, estab_id)
                plano = estab.get("plano", "intermediario") if estab else "intermediario"
                limite = obter_limite_profissionais(plano)
                total_ativos = _obter_total_profissionais_ativos(conn, estab_id)
                if total_ativos >= limite:
                    cfg = PLANOS_CONFIG.get(plano, PLANOS_CONFIG["intermediario"])
                    erro = (
                        f"Limite atingido: O seu plano atual ({cfg['nome']}) permite no máximo "
                        f"{limite} profissional(is) ativo(s). Faça o upgrade do seu plano para ativar este profissional."
                    )
        if not erro:
            ok, erro = models.atualizar_profissional(profissional_id, nome, ativo, servico_ids)
            if ok:
                models.salvar_disponibilidade_profissional(profissional_id, itens_disp)
                return redirect(url_for("admin_profissionais"))

    return render_template(
        "admin_profissional_form.html",
        erro=erro,
        profissional={**profissional, "servico_ids": servico_ids_atuais},
        servicos=servicos,
        disponibilidade=disponibilidade,
        titulo="Editar profissional",
        **_carregar_config_template(estab_id),
    )


@app.route("/admin/profissionais/<int:profissional_id>/toggle", methods=["POST"])
@login_requerido
def admin_profissional_toggle(profissional_id):
    profissional = models.obter_profissional(profissional_id)
    if profissional:
        novo_status = not profissional["ativo"]
        if novo_status:
            with db_session() as conn:
                estab_id = session.get("estabelecimento_id") or 1
                estab = obter_estabelecimento_por_id(conn, estab_id)
                plano = estab.get("plano", "intermediario") if estab else "intermediario"
                limite = obter_limite_profissionais(plano)
                total_ativos = _obter_total_profissionais_ativos(conn, estab_id)
                if total_ativos >= limite:
                    return redirect(url_for("admin_profissionais", erro_limite="1"))
        models.alterar_status_profissional(profissional_id, novo_status)
    return redirect(url_for("admin_profissionais"))


@app.route("/admin/profissionais/<int:profissional_id>/excluir", methods=["POST"])
@login_requerido
def admin_profissional_excluir(profissional_id):
    estab_id = session.get("estabelecimento_id") or 1
    ok, erro = models.excluir_profissional(profissional_id, estabelecimento_id=estab_id)
    if not ok:
        session["flash_erro"] = erro
    else:
        session["flash_sucesso"] = "Profissional excluído com sucesso."
    return redirect(url_for("admin_profissionais"))


@app.route("/admin/clientes")
@login_requerido
def admin_clientes():
    estab_id = session.get("estabelecimento_id") or 1
    busca = request.args.get("busca", "").strip()
    clientes = models.listar_clientes(termo_busca=busca, estabelecimento_id=estab_id)
    sucesso = request.args.get("sucesso")
    erro = request.args.get("erro")
    return render_template(
        "admin_clientes.html",
        clientes=clientes,
        busca=busca,
        total_clientes=len(clientes),
        sucesso=sucesso,
        erro=erro,
        **_carregar_config_template(estab_id),
    )


@app.route("/admin/clientes/novo", methods=["GET", "POST"])
@login_requerido
def admin_cliente_novo():
    estab_id = session.get("estabelecimento_id") or 1
    erro = None
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()
        email = request.form.get("email", "").strip()
        observacoes = request.form.get("observacoes", "").strip()

        cliente_id, erro = models.criar_cliente(nome, telefone, email, observacoes, estabelecimento_id=estab_id)
        if not erro and cliente_id:
            return redirect(url_for("admin_cliente_detalhes", cliente_id=cliente_id, sucesso="Cliente cadastrado com sucesso."))

    return render_template(
        "admin_cliente_form.html",
        titulo="Novo Cliente",
        cliente=None,
        erro=erro,
        **_carregar_config_template(estab_id),
    )


@app.route("/admin/clientes/<int:cliente_id>")
@login_requerido
def admin_cliente_detalhes(cliente_id):
    estab_id = session.get("estabelecimento_id") or 1
    cliente = models.obter_cliente(cliente_id)
    if not cliente:
        return redirect(url_for("admin_clientes", erro="Cliente não encontrado."))

    historico = models.obter_historico_cliente(cliente_id)
    sucesso = request.args.get("sucesso")
    erro = request.args.get("erro")

    return render_template(
        "admin_cliente_detalhe.html",
        cliente=cliente,
        historico=historico,
        sucesso=sucesso,
        erro=erro,
        **_carregar_config_template(estab_id),
    )


@app.route("/admin/clientes/<int:cliente_id>/editar", methods=["GET", "POST"])
@login_requerido
def admin_cliente_editar(cliente_id):
    estab_id = session.get("estabelecimento_id") or 1
    cliente = models.obter_cliente(cliente_id)
    if not cliente:
        return redirect(url_for("admin_clientes", erro="Cliente não encontrado."))

    erro = None
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        telefone = request.form.get("telefone", "").strip()
        email = request.form.get("email", "").strip()
        observacoes = request.form.get("observacoes", "").strip()

        ok, erro = models.atualizar_cliente(cliente_id, nome, telefone, email, observacoes, estabelecimento_id=estab_id)
        if ok:
            return redirect(url_for("admin_cliente_detalhes", cliente_id=cliente_id, sucesso="Dados do cliente atualizados com sucesso."))

    return render_template(
        "admin_cliente_form.html",
        titulo=f"Editar {cliente['nome']}",
        cliente=cliente,
        erro=erro,
        **_carregar_config_template(estab_id),
    )


@app.route("/admin/configuracoes", methods=["GET", "POST"])
@login_requerido
def admin_configuracoes():
    estab_id = session.get("estabelecimento_id") or 1
    erro = None
    sucesso = None

    with db_session() as conn:
        valores = obter_configuracoes_estabelecimento(conn, estab_id)

    if request.method == "POST":
        dias_list = request.form.getlist("dias_funcionamento")
        if len(dias_list) == 1 and "," in dias_list[0]:
            dias_str = dias_list[0].strip()
        elif dias_list:
            dias_str = ",".join(d.strip() for d in dias_list)
        else:
            dias_str = request.form.get("dias_funcionamento", "").strip()

        try:
            sinal_val = float(request.form.get("pagamento_sinal_valor", "30").replace(",", "."))
        except (ValueError, TypeError):
            sinal_val = 30.00

        dados = {
            "dias_antecedencia_agendamento": request.form.get("dias_antecedencia_agendamento", "14").strip(),
            "horario_abertura": request.form.get("horario_abertura", "09:00").strip(),
            "horario_fechamento": request.form.get("horario_fechamento", "19:00").strip(),
            "intervalo_slot_minutos": request.form.get("intervalo_slot_minutos", "30").strip(),
            "dias_funcionamento": dias_str,
            "pagamento_online_ativo": bool(request.form.get("pagamento_online_ativo")),
            "pagamento_tipo": request.form.get("pagamento_tipo", "sinal").strip(),
            "pagamento_sinal_valor": sinal_val,
            "chave_pix_estabelecimento": request.form.get("chave_pix_estabelecimento", "").strip(),
            "tipo_chave_pix": request.form.get("tipo_chave_pix", "cpf_cnpj").strip(),
        }

        erro = _validar_configuracoes_operacionais(dados)
        if not erro:
            with db_session() as conn:
                atualizar_configuracoes_estabelecimento(conn, estab_id, dados)
            models._limpar_cache_config()
            sucesso = "Configurações da agenda e pagamentos atualizadas com sucesso."
            valores.update(dados)
        else:
            valores.update(dados)

    return render_template(
        "admin_configuracoes.html",
        erro=erro,
        sucesso=sucesso,
        configuracoes=valores,
        **_carregar_config_template(estab_id),
    )


@app.route("/admin/estabelecimento", methods=["GET", "POST"])
@login_requerido
def admin_estabelecimento():
    erro = None
    sucesso = None
    usuario = session.get("admin_usuario")

    if request.args.get("boas_vindas") == "1":
        sucesso = "Bem-vindo ao Agillex Agenda! Seu período de 14 dias de teste gratuito está ativo. Confira e complete os dados do seu negócio abaixo para começar a receber agendamentos."

    with db_session() as conn:
        configuracoes = obter_todas_configuracoes(conn)
        admin_row = conn.execute(
            "SELECT id, usuario, email, nome_responsavel, estabelecimento_id FROM admin WHERE usuario = %s",
            (usuario,),
        ).fetchone()
        estab_row = None
        if admin_row and admin_row.get("estabelecimento_id"):
            estab_row = obter_estabelecimento_por_id(conn, admin_row["estabelecimento_id"])

    if estab_row and admin_row.get("estabelecimento_id") and admin_row["estabelecimento_id"] != 1:
        nome_estabelecimento_padrao = estab_row["nome"] or configuracoes.get("nome_estabelecimento", "")
        nome_responsavel_salvo = estab_row["nome_responsavel"] or (admin_row["nome_responsavel"] or "").strip()
        cpf_cnpj_padrao = estab_row["cnpj_cpf"] or configuracoes.get("cpf_cnpj", "")
        telefone_padrao = estab_row["telefone"] or configuracoes.get("telefone", "")
        whatsapp_padrao = estab_row["telefone"] or configuracoes.get("whatsapp", "")
        email_padrao = estab_row["email"] or admin_row["email"] or configuracoes.get("email_comercial", "")
    else:
        nome_responsavel_salvo = (
            (admin_row["nome_responsavel"] or "").strip()
            if admin_row and admin_row.get("nome_responsavel")
            else (estab_row["nome_responsavel"] if estab_row else "")
        )

        nome_estabelecimento_padrao = (
            configuracoes.get("nome_estabelecimento")
            or (estab_row["nome"] if estab_row else "")
        )

        cpf_cnpj_padrao = (
            configuracoes.get("cpf_cnpj")
            or (estab_row["cnpj_cpf"] if estab_row else "")
        )

        telefone_padrao = (
            configuracoes.get("telefone")
            or configuracoes.get("telefone_estabelecimento")
            or (estab_row["telefone"] if estab_row else "")
        )

        whatsapp_padrao = (
            configuracoes.get("whatsapp")
            or (estab_row["telefone"] if estab_row else "")
        )

        email_padrao = (
            configuracoes.get("email_comercial")
            or (estab_row["email"] if estab_row else "")
            or (admin_row["email"] if admin_row else "")
        )

    dados = {
        "logotipo": configuracoes.get("logotipo", ""),
        "nome_estabelecimento": nome_estabelecimento_padrao,
        "nome_responsavel": nome_responsavel_salvo,
        "nome_fantasia": configuracoes.get("nome_fantasia", nome_estabelecimento_padrao),
        "razao_social": configuracoes.get("razao_social", ""),
        "cpf_cnpj": cpf_cnpj_padrao,
        "cep": configuracoes.get("cep", ""),
        "logradouro": configuracoes.get("logradouro", ""),
        "numero": configuracoes.get("numero", ""),
        "complemento": configuracoes.get("complemento", ""),
        "bairro": configuracoes.get("bairro", ""),
        "cidade": configuracoes.get("cidade", ""),
        "estado": configuracoes.get("estado", ""),
        "telefone": telefone_padrao,
        "whatsapp": whatsapp_padrao,
        "email_comercial": email_padrao,
    }

    if request.method == "POST":
        nome_estabelecimento = request.form.get("nome_estabelecimento", "").strip()
        nome_responsavel = request.form.get("nome_responsavel", "").strip()
        nome_fantasia = request.form.get("nome_fantasia", "").strip()
        razao_social = request.form.get("razao_social", "").strip()
        cpf_cnpj = request.form.get("cpf_cnpj", "").strip()

        cep = request.form.get("cep", "").strip()
        logradouro = request.form.get("logradouro", "").strip()
        numero = request.form.get("numero", "").strip()
        complemento = request.form.get("complemento", "").strip()
        bairro = request.form.get("bairro", "").strip()
        cidade = request.form.get("cidade", "").strip()
        estado = request.form.get("estado", "").strip()

        telefone = request.form.get("telefone", "").strip()
        whatsapp = request.form.get("whatsapp", "").strip()
        email_comercial = request.form.get("email_comercial", "").strip()

        remover_logo_acao = request.form.get("remover_logo") == "1" or request.form.get("acao") == "remover_logo"
        logo_a_salvar = configuracoes.get("logotipo", "")

        if remover_logo_acao:
            if logo_a_salvar:
                _remover_arquivo_logo(logo_a_salvar)
            logo_a_salvar = ""
        else:
            arquivo_logo = request.files.get("logotipo")
            if arquivo_logo and arquivo_logo.filename:
                novo_logo, erro_logo = _validar_e_salvar_logotipo(arquivo_logo, logo_a_salvar)
                if erro_logo:
                    erro = erro_logo
                else:
                    logo_a_salvar = novo_logo

        if not erro:
            if not nome_estabelecimento:
                erro = "O nome do estabelecimento é obrigatório."
            elif not nome_responsavel:
                erro = "O nome do responsável é obrigatório."
            elif email_comercial and not _validar_email(email_comercial):
                erro = "Informe um e-mail comercial com formato válido."

        if not erro:
            novos_dados = {
                "nome_estabelecimento": nome_estabelecimento,
                "logotipo": logo_a_salvar,
                "nome_fantasia": nome_fantasia,
                "razao_social": razao_social,
                "cpf_cnpj": cpf_cnpj,
                "cep": cep,
                "logradouro": logradouro,
                "numero": numero,
                "complemento": complemento,
                "bairro": bairro,
                "cidade": cidade,
                "estado": estado,
                "telefone": telefone,
                "telefone_estabelecimento": telefone,
                "whatsapp": whatsapp,
                "email_comercial": email_comercial,
            }

            partes_end = []
            if logradouro:
                partes_end.append(f"{logradouro}, {numero}" if numero else logradouro)
            if complemento:
                partes_end.append(complemento)
            if bairro:
                partes_end.append(bairro)
            if cidade or estado:
                partes_end.append(
                    f"{cidade} - {estado}"
                    if (cidade and estado)
                    else (cidade or estado)
                )
            if cep:
                partes_end.append(f"CEP {cep}")
            if partes_end:
                novos_dados["endereco_estabelecimento"] = " - ".join(partes_end)

            with db_session() as conn:
                atualizar_configuracoes(conn, novos_dados)
                if admin_row:
                    conn.execute(
                        "UPDATE admin SET nome_responsavel = %s WHERE id = %s",
                        (nome_responsavel, admin_row["id"]),
                    )
                    if admin_row.get("estabelecimento_id"):
                        conn.execute(
                            """
                            UPDATE estabelecimento
                            SET nome = %s, nome_responsavel = %s, cnpj_cpf = %s, telefone = %s, email = %s
                            WHERE id = %s
                            """,
                            (
                                nome_estabelecimento,
                                nome_responsavel,
                                cpf_cnpj,
                                telefone,
                                email_comercial or admin_row["email"] or "",
                                admin_row["estabelecimento_id"],
                            ),
                        )

            models._limpar_cache_config()
            if remover_logo_acao:
                sucesso = "Logotipo removido com sucesso."
            else:
                sucesso = "Dados do estabelecimento salvos com sucesso."
            dados = {**novos_dados, "nome_responsavel": nome_responsavel}
        else:
            dados = {
                "logotipo": logo_a_salvar,
                "nome_estabelecimento": nome_estabelecimento,
                "nome_responsavel": nome_responsavel,
                "nome_fantasia": nome_fantasia,
                "razao_social": razao_social,
                "cpf_cnpj": cpf_cnpj,
                "cep": cep,
                "logradouro": logradouro,
                "numero": numero,
                "complemento": complemento,
                "bairro": bairro,
                "cidade": cidade,
                "estado": estado,
                "telefone": telefone,
                "whatsapp": whatsapp,
                "email_comercial": email_comercial,
            }

    return render_template(
        "admin_estabelecimento.html",
        erro=erro,
        sucesso=sucesso,
        dados=dados,
        **_carregar_config_template(),
    )


@app.route("/admin/configuracao-inicial", methods=["GET", "POST"])
@login_requerido
def admin_configuracao_inicial():
    usuario = session.get("admin_usuario")
    erro = None
    config = _carregar_config_template()

    with db_session() as conn:
        primeiro_acesso = admin_precisa_alterar_senha(conn, usuario)
        if not primeiro_acesso:
            return redirect(url_for("admin_dashboard"))

        admin_row = conn.execute(
            "SELECT usuario, email, nome_responsavel FROM admin WHERE usuario = %s", (usuario,)
        ).fetchone()
        email_salvo = (admin_row["email"] or "").strip() if admin_row and "email" in admin_row and admin_row["email"] else ""
        nome_resp_salvo = (admin_row["nome_responsavel"] or "").strip() if admin_row and "nome_responsavel" in admin_row and admin_row["nome_responsavel"] else ""
        nome_est_salvo = (obter_configuracao(conn, "nome_estabelecimento") or "").strip()

    nome_estabelecimento = nome_est_salvo
    nome_responsavel = nome_resp_salvo
    email = email_salvo
    novo_login = "" if usuario == "admin" else (usuario or "")

    if request.method == "POST":
        nome_estabelecimento = request.form.get("nome_estabelecimento", "").strip()
        nome_responsavel = request.form.get("nome_responsavel", "").strip()
        email = request.form.get("email", "").strip()
        novo_login = request.form.get("novo_login", "").strip()
        nova_senha = request.form.get("nova_senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")

        if not nome_estabelecimento:
            erro = "O nome do estabelecimento é obrigatório."
        elif not nome_responsavel:
            erro = "O nome do responsável é obrigatório."
        elif not email:
            erro = "O e-mail do responsável é obrigatório."
        elif not _validar_email(email):
            erro = "Informe um e-mail com formato válido."
        elif not novo_login:
            erro = "O novo login é obrigatório."
        elif novo_login.lower() == "admin":
            erro = "Defina um novo login diferente do usuário provisório 'admin'."
        elif not nova_senha:
            erro = "A nova senha é obrigatória."
        elif len(nova_senha) < 8:
            erro = "A nova senha deve ter pelo menos 8 caracteres."
        elif nova_senha != confirmar_senha:
            erro = "As novas senhas não conferem."
        else:
            with db_session() as conn:
                ok, msg = db_admin_concluir_primeiro_acesso(
                    conn,
                    usuario_atual=usuario,
                    novo_login=novo_login,
                    nova_senha=nova_senha,
                    email=email,
                    nome_responsavel=nome_responsavel,
                    nome_estabelecimento=nome_estabelecimento,
                )
            if ok:
                session["admin_usuario"] = novo_login
                models._limpar_cache_config()
                return redirect(url_for("admin_dashboard"))
            else:
                erro = msg or "Não foi possível concluir a configuração inicial."

    return render_template(
        "admin_configuracao_inicial.html",
        erro=erro,
        nome_estabelecimento=nome_estabelecimento,
        nome_responsavel=nome_responsavel,
        email=email,
        novo_login=novo_login,
        nome_publico=config.get("nome_publico", "AllLogic Scheduler"),
    )


@app.route("/admin/alterar-senha", methods=["GET", "POST"])
@login_requerido
def admin_alterar_senha():
    usuario = session.get("admin_usuario")
    erro = None
    sucesso = None
    config = _carregar_config_template()

    with db_session() as conn:
        if admin_precisa_alterar_senha(conn, usuario):
            return redirect(url_for("admin_configuracao_inicial"))

    if request.method == "POST":
        senha_atual = request.form.get("senha_atual", "")
        nova_senha = request.form.get("nova_senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")

        if not senha_atual:
            erro = "A senha atual é obrigatória."
        elif not nova_senha:
            erro = "A nova senha é obrigatória."
        elif len(nova_senha) < 8:
            erro = "A nova senha deve ter pelo menos 8 caracteres."
        elif nova_senha != confirmar_senha:
            erro = "As novas senhas não conferem."
        elif nova_senha == senha_atual:
            erro = "A nova senha deve ser diferente da senha atual."
        else:
            with db_session() as conn:
                ok, msg = db_admin_alterar_senha(conn, usuario, senha_atual, nova_senha)
            if ok:
                sucesso = "Senha alterada com sucesso."
            else:
                erro = msg or "Não foi possível alterar a senha."

    return render_template(
        "admin_alterar_senha.html",
        erro=erro,
        sucesso=sucesso,
        **config,
    )


@app.route("/admin/esqueci-senha", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def admin_esqueci_senha():
    erro = None
    sucesso = None
    email = ""
    config = _carregar_config_template()

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email:
            erro = "Informe o e-mail de recuperação."
        elif not _validar_email(email):
            erro = "Informe um e-mail com formato válido."
        else:
            with db_session() as conn:
                admin_row = obter_admin_por_email(conn, email)
                if admin_row:
                    raw_token = secrets.token_urlsafe(32)
                    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
                    expira_em = datetime.now(timezone.utc) + timedelta(minutes=30)
                    criar_token_recuperacao(conn, admin_row["id"], token_hash, expira_em)
                    link = url_for("admin_redefinir_senha", token=raw_token, _external=True)
                    nome_resp = admin_row.get("nome_responsavel") or admin_row.get("usuario")
                    enviar_email_recuperacao(
                        destinatario=admin_row["email"],
                        link_recuperacao=link,
                        nome_responsavel=nome_resp,
                    )
            sucesso = "Se o e-mail estiver associado a uma conta, enviaremos instruções para redefinição da senha."
            email = ""

    return render_template(
        "admin_esqueci_senha.html",
        erro=erro,
        sucesso=sucesso,
        email=email,
        **config,
    )


@app.route("/admin/redefinir-senha/<token>", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def admin_redefinir_senha(token):
    erro = None
    token_invalido = False
    config = _carregar_config_template()

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    with db_session() as conn:
        valido, msg_erro, _ = validar_token_recuperacao(conn, token_hash)

    if not valido:
        return render_template(
            "admin_redefinir_senha.html",
            token_invalido=True,
            erro=msg_erro,
            token=token,
            **config,
        )

    if request.method == "POST":
        nova_senha = request.form.get("nova_senha", "")
        confirmar_senha = request.form.get("confirmar_senha", "")

        if not nova_senha:
            erro = "A nova senha é obrigatória."
        elif len(nova_senha) < 8:
            erro = "A nova senha deve ter pelo menos 8 caracteres."
        elif nova_senha != confirmar_senha:
            erro = "As novas senhas não conferem."
        else:
            with db_session() as conn:
                ok, msg_db = redefinir_senha_com_token(conn, token_hash, nova_senha)
            if ok:
                return redirect(url_for("admin_login", redefinida=1))
            else:
                token_invalido = True
                erro = msg_db or "Não foi possível redefinir a senha."

    return render_template(
        "admin_redefinir_senha.html",
        token_invalido=token_invalido,
        erro=erro,
        token=token,
        **config,
    )


@app.route("/admin/agendamento/<int:agendamento_id>/cancelar", methods=["POST"])
@login_requerido
def admin_cancelar_agendamento(agendamento_id):
    aba = request.args.get("aba") or request.form.get("aba") or "hoje"
    profissional_id = request.args.get("profissional_id") or request.form.get("profissional_id")
    ok, erro = models.cancelar_agendamento(agendamento_id, usuario=session.get("admin_usuario"))
    params = {"aba": aba}
    if profissional_id:
        params["profissional_id"] = profissional_id
    for param in ("cliente", "telefone", "data_inicio", "data_fim"):
        val = request.args.get(param) or request.form.get(param)
        if val:
            params[param] = val
    st = request.args.get("filtro_status") or request.form.get("filtro_status") or request.args.get("status")
    if st:
        params["status"] = st

    if ok:
        params["sucesso"] = "Agendamento cancelado com sucesso."
    elif erro:
        params["erro"] = erro
    return redirect(url_for("admin_dashboard", **params))


@app.route("/admin/agendamento/<int:agendamento_id>/excluir", methods=["POST"])
@login_requerido
def admin_excluir_agendamento(agendamento_id):
    estab_id = session.get("estabelecimento_id") or 1
    aba = request.args.get("aba") or request.form.get("aba") or "hoje"
    profissional_id = request.args.get("profissional_id") or request.form.get("profissional_id")
    ok, erro = models.excluir_agendamento(agendamento_id, estabelecimento_id=estab_id)
    params = {"aba": aba}
    if profissional_id:
        params["profissional_id"] = profissional_id
    for param in ("cliente", "telefone", "data_inicio", "data_fim"):
        val = request.args.get(param) or request.form.get(param)
        if val:
            params[param] = val
    st = request.args.get("filtro_status") or request.form.get("filtro_status") or request.args.get("status")
    if st:
        params["status"] = st

    if ok:
        params["sucesso"] = "Agendamento cancelado excluído com sucesso."
    elif erro:
        params["erro"] = erro
    return redirect(url_for("admin_dashboard", **params))


@app.route("/admin/agendamento/<int:agendamento_id>/status", methods=["POST"])
@login_requerido
def admin_atualizar_status_agendamento(agendamento_id):
    novo_status = (request.form.get("status") or "").strip()
    aba = request.args.get("aba") or request.form.get("aba") or "hoje"
    profissional_id = request.args.get("profissional_id") or request.form.get("profissional_id")
    ok, erro = models.atualizar_status_agendamento(
        agendamento_id, novo_status, usuario=session.get("admin_usuario")
    )
    params = {"aba": aba}
    if profissional_id:
        params["profissional_id"] = profissional_id
    for param in ("cliente", "telefone", "data_inicio", "data_fim"):
        val = request.args.get(param) or request.form.get(param)
        if val:
            params[param] = val
    st = request.args.get("filtro_status") or request.form.get("filtro_status")
    if st:
        params["status"] = st

    if ok:
        msg = (
            "Atendimento marcado como realizado com sucesso."
            if novo_status == "realizado"
            else "Atendimento marcado como não compareceu."
        )
        params["sucesso"] = msg
    elif erro:
        params["erro"] = erro
    return redirect(url_for("admin_dashboard", **params))


@app.route("/admin/agendamento/<int:agendamento_id>/reagendar", methods=["GET", "POST"])
@login_requerido
def admin_reagendar_agendamento(agendamento_id):
    aba = request.args.get("aba") or request.form.get("aba") or "hoje"
    profissional_id_filtro = request.args.get("profissional_id") or request.form.get("profissional_id")
    cliente_filtro = request.args.get("cliente") or request.form.get("cliente")
    telefone_filtro = request.args.get("telefone") or request.form.get("telefone")
    status_filtro = request.args.get("filtro_status") or request.form.get("filtro_status") or request.args.get("status")
    data_inicio_filtro = request.args.get("data_inicio") or request.form.get("data_inicio")
    data_fim_filtro = request.args.get("data_fim") or request.form.get("data_fim")
    data_filtro = request.args.get("data") or request.form.get("data")

    filtros_retorno = {}
    if cliente_filtro:
        filtros_retorno["cliente"] = cliente_filtro
    if telefone_filtro:
        filtros_retorno["telefone"] = telefone_filtro
    if status_filtro:
        filtros_retorno["status"] = status_filtro
    if data_inicio_filtro:
        filtros_retorno["data_inicio"] = data_inicio_filtro
    if data_fim_filtro:
        filtros_retorno["data_fim"] = data_fim_filtro
    if data_filtro:
        filtros_retorno["data"] = data_filtro

    agendamento = models.obter_agendamento_completo(agendamento_id)
    if not agendamento:
        params_err = {"aba": aba, "erro": "Agendamento não encontrado.", **filtros_retorno}
        if profissional_id_filtro:
            params_err["profissional_id"] = profissional_id_filtro
        return redirect(url_for("admin_dashboard", **params_err))

    if agendamento["status"] != "agendado":
        params_err = {
            "aba": aba,
            "erro": f"Apenas agendamentos ativos podem ser reagendados (status atual: {agendamento['status']}).",
            **filtros_retorno,
        }
        if profissional_id_filtro:
            params_err["profissional_id"] = profissional_id_filtro
        return redirect(url_for("admin_dashboard", **params_err))

    erro = None
    hoje = datetime.now().date()
    max_dias = models.dias_antecedencia_agendamento() or 14
    data_limite = hoje + timedelta(days=max_dias)
    servico_ids = [s["id"] for s in agendamento["servicos"]]
    data_selecionada = (request.form.get("nova_data") or agendamento["data"]).strip()

    if request.method == "POST":
        nova_data = (request.form.get("nova_data") or "").strip()
        novo_horario = (request.form.get("novo_horario") or "").strip()

        if not nova_data:
            erro = "Selecione uma data para o reagendamento."
        elif not novo_horario:
            erro = "Selecione um horário para o reagendamento."
        else:
            ok, erro_reagendar = models.reagendar_agendamento(
                agendamento_id,
                nova_data,
                novo_horario,
                usuario=session.get("admin_usuario"),
            )
            if ok:
                params = {"aba": aba, "sucesso": "Reagendamento realizado com sucesso.", **filtros_retorno}
                if profissional_id_filtro:
                    params["profissional_id"] = profissional_id_filtro
                url_retorno = url_for("admin_dashboard", **params)
                agendamento_atualizado = models.obter_agendamento_completo(agendamento_id) or agendamento
                return render_template(
                    "admin_reagendar_sucesso.html",
                    agendamento=agendamento_atualizado,
                    nova_data=nova_data,
                    novo_horario=novo_horario,
                    url_retorno=url_retorno,
                    **_carregar_config_template(),
                )
            else:
                erro = erro_reagendar
                data_selecionada = nova_data

    historico = models.obter_historico_reagendamentos(agendamento_id)
    horarios_disponiveis = models.horarios_disponiveis(
        agendamento["profissional_id"],
        data_selecionada,
        servico_ids,
        ignorar_agendamento_id=agendamento_id,
    )

    return render_template(
        "admin_reagendar.html",
        agendamento=agendamento,
        historico=historico,
        hoje=hoje.isoformat(),
        data_limite=data_limite.isoformat(),
        data_selecionada=data_selecionada,
        horarios_disponiveis=horarios_disponiveis,
        erro=erro,
        aba=aba,
        profissional_id_filtro=profissional_id_filtro,
        filtros_retorno=filtros_retorno,
        **_carregar_config_template(),
    )


@app.route("/admin/pesquisa")
@login_requerido
def admin_pesquisa():
    args = dict(request.args)
    args["aba"] = "pesquisa"
    return redirect(url_for("admin_dashboard", **args))


@app.route("/admin")
@login_requerido
def admin_dashboard():
    aba = request.args.get("aba", "hoje")
    data_raw = (request.args.get("data") or "").strip()
    hoje = datetime.now().date()
    if data_raw:
        try:
            hoje = datetime.strptime(data_raw, "%Y-%m-%d").date()
        except ValueError:
            hoje = datetime.now().date()

    profissional_id_raw = request.args.get("profissional_id")
    profissional_id = None
    if profissional_id_raw:
        try:
            profissional_id = int(profissional_id_raw)
        except ValueError:
            profissional_id = None

    cliente_filtro = (request.args.get("cliente") or "").strip()
    telefone_filtro = (request.args.get("telefone") or "").strip()
    status_filtro = (request.args.get("status") or request.args.get("filtro_status") or "").strip()
    data_inicio_raw = (request.args.get("data_inicio") or "").strip()
    data_fim_raw = (request.args.get("data_fim") or "").strip()

    data_inicio_filtro = models._normalizar_data_iso(data_inicio_raw) if data_inicio_raw else ""
    data_fim_filtro = models._normalizar_data_iso(data_fim_raw) if data_fim_raw else ""

    tem_param_pesquisa = bool(
        cliente_filtro
        or telefone_filtro
        or status_filtro
        or data_inicio_filtro
        or data_fim_filtro
    )
    if aba == "pesquisa" or (tem_param_pesquisa and aba not in ("hoje", "semana", "mes")):
        aba = "pesquisa"

    receita_prevista = 0.0
    receita_periodo = 0.0
    agrupados = {}
    inicio_semana = None
    fim_semana = None
    semana_anterior = None
    proxima_semana = None

    estab_id = session.get("estabelecimento_id") or 1

    if aba == "pesquisa":
        agendamentos = models.pesquisar_agendamentos(
            cliente=cliente_filtro or None,
            telefone=telefone_filtro or None,
            profissional_id=profissional_id,
            status=status_filtro or None,
            data_inicio=data_inicio_filtro or None,
            data_fim=data_fim_filtro or None,
            estabelecimento_id=estab_id,
        )
    elif aba == "mes":
        inicio_mes = hoje.replace(day=1)
        if hoje.month == 12:
            inicio_proximo_mes = hoje.replace(year=hoje.year + 1, month=1, day=1)
        else:
            inicio_proximo_mes = hoje.replace(month=hoje.month + 1, day=1)
        fim_mes = inicio_proximo_mes - timedelta(days=1)
        agendamentos = models.listar_agendamentos_por_periodo(
            inicio_mes.isoformat(), fim_mes.isoformat(), profissional_id=profissional_id, estabelecimento_id=estab_id
        )
    elif aba == "semana":
        dias_desde_domingo = (hoje.weekday() + 1) % 7
        inicio_semana = hoje - timedelta(days=dias_desde_domingo)
        fim_semana = inicio_semana + timedelta(days=6)
        semana_anterior = (inicio_semana - timedelta(days=7)).isoformat()
        proxima_semana = (inicio_semana + timedelta(days=7)).isoformat()
        agendamentos = models.listar_agendamentos_por_periodo(
            inicio_semana.isoformat(), fim_semana.isoformat(), profissional_id=profissional_id, estabelecimento_id=estab_id
        )
    else:
        aba = "hoje"
        agendamentos = models.listar_agendamentos_por_periodo(
            hoje.isoformat(), hoje.isoformat(), profissional_id=profissional_id, estabelecimento_id=estab_id
        )

    total_agendamentos = len(agendamentos)
    if aba != "pesquisa":
        receita_prevista = sum(
            a["servico_preco"] for a in agendamentos
            if a["status"] == "agendado"
        )
        receita_periodo = sum(
            a["servico_preco"] for a in agendamentos
            if a["status"] in ("agendado", "realizado")
        )
        if aba == "semana":
            for i in range(7):
                dia_data = inicio_semana + timedelta(days=i)
                agrupados[dia_data.isoformat()] = []
            for ag in agendamentos:
                agrupados.setdefault(ag["data"], []).append(ag)
        elif aba == "mes":
            for ag in agendamentos:
                agrupados.setdefault(ag["data"], []).append(ag)

    profissionais_filtro = models.listar_profissionais(apenas_ativos=True, estabelecimento_id=estab_id)
    sucesso = request.args.get("sucesso")
    erro = request.args.get("erro")

    return render_template(
        "admin_dashboard.html",
        aba=aba,
        agendamentos=agendamentos,
        agrupados=agrupados,
        total_agendamentos=total_agendamentos,
        receita_prevista=receita_prevista,
        receita_periodo=receita_periodo,
        hoje=hoje.isoformat(),
        inicio_semana=inicio_semana,
        fim_semana=fim_semana,
        semana_anterior=semana_anterior,
        proxima_semana=proxima_semana,
        profissionais_filtro=profissionais_filtro,
        profissional_selecionado=profissional_id,
        filtro_cliente=cliente_filtro,
        filtro_telefone=telefone_filtro,
        filtro_status=status_filtro,
        filtro_data_inicio=data_inicio_filtro,
        filtro_data_fim=data_fim_filtro,
        sucesso=sucesso,
        erro=erro,
        **_carregar_config_template(estab_id),
    )



# Exempt API endpoints from CSRF (they use JSON, not forms)
csrf.exempt(api_services)
csrf.exempt(api_professionals)
csrf.exempt(api_availability)
csrf.exempt(api_appointments)
csrf.exempt(api_agendamento_pix_status)
csrf.exempt(webhook_asaas_agendamento)


if __name__ == "__main__":
    # Servidor de desenvolvimento. Em produção, o Gunicorn importa a variável `app`
    # diretamente (veja o arquivo de serviço systemd) e este bloco não é executado.
    app.run(debug=False, host="0.0.0.0", port=5000)

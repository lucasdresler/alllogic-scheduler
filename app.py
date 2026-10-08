import hashlib
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
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
    admin_precisa_alterar_senha,
    admin_alterar_senha as db_admin_alterar_senha,
    admin_concluir_primeiro_acesso as db_admin_concluir_primeiro_acesso,
    obter_admin_por_email,
    criar_token_recuperacao,
    validar_token_recuperacao,
    redefinir_senha_com_token,
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


def _carregar_config_template():
    """Carrega configurações do banco para uso nos templates."""
    with db_session() as conn:
        config = obter_todas_configuracoes(conn)

    logotipo = config.get("logotipo", "")
    if logotipo:
        caminho_disco = os.path.join(app.root_path, "static", logotipo)
        if not os.path.isfile(caminho_disco):
            logotipo = ""

    telefone = config.get("telefone_estabelecimento", "")
    telefone_limpo = re.sub(r"[^\d+]", "", telefone) if telefone else ""

    return {
        "nome_estabelecimento": config.get("nome_estabelecimento", "AllLogic Scheduler"),
        "telefone_estabelecimento": telefone,
        "telefone_limpo": telefone_limpo,
        "endereco_estabelecimento": config.get("endereco_estabelecimento", ""),
        "nome_publico": config.get("nome_publico", "AllLogic Scheduler"),
        "logotipo": logotipo,
        "dias_antecedencia": models.dias_antecedencia_agendamento(),
        "dias_funcionamento": models.dias_funcionamento(),
    }


@app.context_processor
def inject_config_template():
    return _carregar_config_template()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def _validar_email(email):
    if not email or len(email) > 254:
        return False
    return bool(EMAIL_REGEX.match(email))


def login_requerido(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        if not session.get("admin_logado"):
            return redirect(url_for("admin_login"))
        if request.endpoint not in ("admin_configuracao_inicial", "admin_logout"):
            usuario = session.get("admin_usuario")
            with db_session() as conn:
                if admin_precisa_alterar_senha(conn, usuario):
                    return redirect(url_for("admin_configuracao_inicial"))
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

@app.route("/")
def index():
    servicos = models.listar_servicos()
    profissionais = models.listar_profissionais()
    config = _carregar_config_template()
    return render_template(
        "index.html",
        servicos=servicos,
        profissionais=profissionais,
        **config,
    )


@app.route("/agendamento/sucesso/<int:agendamento_id>")
def agendamento_sucesso(agendamento_id):
    agendamento = models.obter_agendamento_completo(agendamento_id)
    if not agendamento:
        return redirect(url_for("index"))
    return render_template(
        "sucesso.html",
        agendamento=agendamento,
        **_carregar_config_template(),
    )


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

@app.route("/api/services")
def api_services():
    return jsonify(models.listar_servicos(apenas_ativos=True))


@app.route("/api/professionals")
def api_professionals():
    servico_ids = request.args.getlist("servico_id", type=int)
    if not servico_ids:
        return jsonify(models.listar_profissionais(apenas_ativos=True))

    servico_ids = list(dict.fromkeys(servico_ids))
    if any(
        not (servico := models.obter_servico(servico_id)) or not servico["ativo"]
        for servico_id in servico_ids
    ):
        return jsonify({"erro": "Serviço inválido."}), 400
    return jsonify(models.listar_profissionais_para_servicos(servico_ids))


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

        if not erros and not models.data_permitida(data_str):
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
    )

    if erro:
        return jsonify({"erro": erro}), 409

    return jsonify({"agendamento_id": agendamento_id}), 201


@app.route("/admin/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def admin_login():
    erro = None
    sucesso = None
    if request.args.get("redefinida") == "1":
        sucesso = "Senha redefinida com sucesso. Faça login com a sua nova senha."
    config = _carregar_config_template()
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")
        if models.verificar_admin(usuario, senha):
            session["admin_logado"] = True
            session["admin_usuario"] = usuario
            with db_session() as conn:
                if admin_precisa_alterar_senha(conn, usuario):
                    return redirect(url_for("admin_configuracao_inicial"))
            return redirect(url_for("admin_dashboard"))
        erro = "Usuário ou senha inválidos."
    return render_template("admin_login.html", erro=erro, sucesso=sucesso, **config)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin/servicos")
@login_requerido
def admin_servicos():
    servicos = models.listar_servicos_admin()
    return render_template(
        "admin_servicos.html",
        servicos=servicos,
        **_carregar_config_template(),
    )


@app.route("/admin/servicos/novo", methods=["GET", "POST"])
@login_requerido
def admin_servico_novo():
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
        )
        if servico_id:
            return redirect(url_for("admin_servicos"))

    return render_template(
        "admin_servico_form.html",
        erro=erro,
        servico=None,
        titulo="Novo serviço",
        **_carregar_config_template(),
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


@app.route("/admin/profissionais")
@login_requerido
def admin_profissionais():
    profissionais = models.listar_profissionais_admin()
    servicos = models.listar_servicos_admin()
    return render_template(
        "admin_profissionais.html",
        profissionais=profissionais,
        servicos=servicos,
        **_carregar_config_template(),
    )


@app.route("/admin/profissionais/novo", methods=["GET", "POST"])
@login_requerido
def admin_profissional_novo():
    erro = None
    servicos = models.listar_servicos_admin()
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        ativo = request.form.get("ativo") == "on"
        servico_ids = request.form.getlist("servicos", type=int)

        profissional_id, erro = models.criar_profissional(nome, ativo, servico_ids)
        if profissional_id:
            return redirect(url_for("admin_profissionais"))

    return render_template(
        "admin_profissional_form.html",
        erro=erro,
        profissional=None,
        servicos=servicos,
        titulo="Novo profissional",
        **_carregar_config_template(),
    )


@app.route("/admin/profissionais/<int:profissional_id>/editar", methods=["GET", "POST"])
@login_requerido
def admin_profissional_editar(profissional_id):
    profissional = models.obter_profissional(profissional_id)
    if not profissional:
        return redirect(url_for("admin_profissionais"))

    servicos = models.listar_servicos_admin()
    lista_profissionais = models.listar_profissionais_admin()
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
        else:
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
        **_carregar_config_template(),
    )


@app.route("/admin/profissionais/<int:profissional_id>/toggle", methods=["POST"])
@login_requerido
def admin_profissional_toggle(profissional_id):
    profissional = models.obter_profissional(profissional_id)
    if profissional:
        models.alterar_status_profissional(profissional_id, not profissional["ativo"])
    return redirect(url_for("admin_profissionais"))


@app.route("/admin/configuracoes", methods=["GET", "POST"])
@login_requerido
def admin_configuracoes():
    erro = None
    sucesso = None

    with db_session() as conn:
        valores = obter_todas_configuracoes(conn)

    if request.method == "POST":
        dias_list = request.form.getlist("dias_funcionamento")
        if len(dias_list) == 1 and "," in dias_list[0]:
            dias_str = dias_list[0].strip()
        elif dias_list:
            dias_str = ",".join(d.strip() for d in dias_list)
        else:
            dias_str = request.form.get("dias_funcionamento", "").strip()

        dados = {
            "dias_antecedencia_agendamento": request.form.get("dias_antecedencia_agendamento", "14").strip(),
            "horario_abertura": request.form.get("horario_abertura", "09:00").strip(),
            "horario_fechamento": request.form.get("horario_fechamento", "19:00").strip(),
            "intervalo_slot_minutos": request.form.get("intervalo_slot_minutos", "30").strip(),
            "dias_funcionamento": dias_str,
        }

        erro = _validar_configuracoes_operacionais(dados)
        if not erro:
            with db_session() as conn:
                atualizar_configuracoes(conn, dados)
            models._limpar_cache_config()
            sucesso = "Configurações da agenda atualizadas com sucesso."
            valores.update(dados)
        else:
            valores.update(dados)

    return render_template(
        "admin_configuracoes.html",
        erro=erro,
        sucesso=sucesso,
        configuracoes=valores,
        **_carregar_config_template(),
    )


@app.route("/admin/estabelecimento", methods=["GET", "POST"])
@login_requerido
def admin_estabelecimento():
    erro = None
    sucesso = None
    usuario = session.get("admin_usuario")

    with db_session() as conn:
        configuracoes = obter_todas_configuracoes(conn)
        admin_row = conn.execute(
            "SELECT id, usuario, email, nome_responsavel FROM admin WHERE usuario = %s",
            (usuario,),
        ).fetchone()

    nome_responsavel_salvo = (
        (admin_row["nome_responsavel"] or "").strip()
        if admin_row and "nome_responsavel" in admin_row and admin_row["nome_responsavel"]
        else ""
    )

    telefone_padrao = configuracoes.get(
        "telefone", configuracoes.get("telefone_estabelecimento", "")
    )

    dados = {
        "logotipo": configuracoes.get("logotipo", ""),
        "nome_estabelecimento": configuracoes.get("nome_estabelecimento", ""),
        "nome_responsavel": nome_responsavel_salvo,
        "nome_fantasia": configuracoes.get("nome_fantasia", ""),
        "razao_social": configuracoes.get("razao_social", ""),
        "cpf_cnpj": configuracoes.get("cpf_cnpj", ""),
        "cep": configuracoes.get("cep", ""),
        "logradouro": configuracoes.get("logradouro", ""),
        "numero": configuracoes.get("numero", ""),
        "complemento": configuracoes.get("complemento", ""),
        "bairro": configuracoes.get("bairro", ""),
        "cidade": configuracoes.get("cidade", ""),
        "estado": configuracoes.get("estado", ""),
        "telefone": telefone_padrao,
        "whatsapp": configuracoes.get("whatsapp", ""),
        "email_comercial": configuracoes.get("email_comercial", ""),
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
                params = {"aba": aba, "sucesso": "Agendamento reagendado com sucesso.", **filtros_retorno}
                if profissional_id_filtro:
                    params["profissional_id"] = profissional_id_filtro
                return redirect(url_for("admin_dashboard", **params))
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

    if aba == "pesquisa":
        agendamentos = models.pesquisar_agendamentos(
            cliente=cliente_filtro or None,
            telefone=telefone_filtro or None,
            profissional_id=profissional_id,
            status=status_filtro or None,
            data_inicio=data_inicio_filtro or None,
            data_fim=data_fim_filtro or None,
        )
    elif aba == "mes":
        inicio_mes = hoje.replace(day=1)
        if hoje.month == 12:
            inicio_proximo_mes = hoje.replace(year=hoje.year + 1, month=1, day=1)
        else:
            inicio_proximo_mes = hoje.replace(month=hoje.month + 1, day=1)
        fim_mes = inicio_proximo_mes - timedelta(days=1)
        agendamentos = models.listar_agendamentos_por_periodo(
            inicio_mes.isoformat(), fim_mes.isoformat(), profissional_id=profissional_id
        )
    elif aba == "semana":
        dias_desde_domingo = (hoje.weekday() + 1) % 7
        inicio_semana = hoje - timedelta(days=dias_desde_domingo)
        fim_semana = inicio_semana + timedelta(days=6)
        semana_anterior = (inicio_semana - timedelta(days=7)).isoformat()
        proxima_semana = (inicio_semana + timedelta(days=7)).isoformat()
        agendamentos = models.listar_agendamentos_por_periodo(
            inicio_semana.isoformat(), fim_semana.isoformat(), profissional_id=profissional_id
        )
    else:
        aba = "hoje"
        agendamentos = models.listar_agendamentos_por_periodo(
            hoje.isoformat(), hoje.isoformat(), profissional_id=profissional_id
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

    profissionais_filtro = models.listar_profissionais(apenas_ativos=True)
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
        **_carregar_config_template(),
    )



# Exempt API endpoints from CSRF (they use JSON, not forms)
csrf.exempt(api_services)
csrf.exempt(api_professionals)
csrf.exempt(api_availability)
csrf.exempt(api_appointments)


if __name__ == "__main__":
    # Servidor de desenvolvimento. Em produção, o Gunicorn importa a variável `app`
    # diretamente (veja o arquivo de serviço systemd) e este bloco não é executado.
    app.run(debug=False, host="0.0.0.0", port=5000)

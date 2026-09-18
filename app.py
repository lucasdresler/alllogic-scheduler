from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

import models
from config import DIAS_ANTECEDENCIA_AGENDAMENTO, SECRET_KEY
from database import init_db

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY

init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def login_requerido(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        if not session.get("admin_logado"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorada


# ---------------------------------------------------------------------------
# Páginas públicas
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    servicos = models.listar_servicos()
    profissionais = models.listar_profissionais()
    return render_template(
        "index.html",
        servicos=servicos,
        profissionais=profissionais,
        dias_antecedencia=DIAS_ANTECEDENCIA_AGENDAMENTO,
    )


@app.route("/agendamento/sucesso/<int:agendamento_id>")
def agendamento_sucesso(agendamento_id):
    agendamento = models.obter_agendamento_completo(agendamento_id)
    if not agendamento:
        return redirect(url_for("index"))
    return render_template("sucesso.html", agendamento=agendamento)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

@app.route("/api/services")
def api_services():
    return jsonify(models.listar_servicos())


@app.route("/api/professionals")
def api_professionals():
    return jsonify(models.listar_profissionais())


@app.route("/api/availability")
def api_availability():
    profissional_id = request.args.get("profissional_id", type=int)
    data_str = request.args.get("data", type=str)

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

    if any(not models.obter_servico(servico_id) for servico_id in servico_ids):
        return jsonify({"erro": "Serviço inválido."}), 400

    horarios = models.horarios_disponiveis(
        profissional_id,
        data_str,
        servico_ids,
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
    if not servico_ids:
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
            if not isinstance(servico_id, int) or not models.obter_servico(servico_id):
                erros.append("Serviço inválido.")
                break

        if not models.obter_profissional(profissional_id):
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
def admin_login():
    erro = None
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")
        if models.verificar_admin(usuario, senha):
            session["admin_logado"] = True
            session["admin_usuario"] = usuario
            return redirect(url_for("admin_dashboard"))
        erro = "Usuário ou senha inválidos."
    return render_template("admin_login.html", erro=erro)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin/agendamento/<int:agendamento_id>/cancelar", methods=["POST"])
@login_requerido
def admin_cancelar_agendamento(agendamento_id):
    models.cancelar_agendamento(agendamento_id)
    return redirect(url_for("admin_dashboard"))



@app.route("/admin")
@login_requerido
def admin_dashboard():
    aba = request.args.get("aba", "hoje")
    hoje = datetime.now().date()

    if aba == "mes":
        inicio_mes = hoje.replace(day=1)
        if hoje.month == 12:
            inicio_proximo_mes = hoje.replace(year=hoje.year + 1, month=1, day=1)
        else:
            inicio_proximo_mes = hoje.replace(month=hoje.month + 1, day=1)
        fim_mes = inicio_proximo_mes - timedelta(days=1)
        agendamentos = models.listar_agendamentos_por_periodo(inicio_mes.isoformat(), fim_mes.isoformat())
    elif aba == "semana":
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        fim_semana = inicio_semana + timedelta(days=6)
        agendamentos = models.listar_agendamentos_por_periodo(
            inicio_semana.isoformat(), fim_semana.isoformat()
        )
    else:
        aba = "hoje"
        agendamentos = models.listar_agendamentos_por_periodo(hoje.isoformat(), hoje.isoformat())

    total_agendamentos = len(agendamentos)
    receita_prevista = sum(
        a["servico_preco"] for a in agendamentos
        if a["status"] == "agendado"
    )
    receita_periodo = sum(
        a["servico_preco"] for a in agendamentos
        if a["status"] in ("agendado", "realizado")
    )

    agrupados = {}
    if aba in ("semana", "mes"):
        for ag in agendamentos:
            agrupados.setdefault(ag["data"], []).append(ag)

    return render_template(
        "admin_dashboard.html",
        aba=aba,
        agendamentos=agendamentos,
        agrupados=agrupados,
        total_agendamentos=total_agendamentos,
        receita_prevista=receita_prevista,
        receita_periodo=receita_periodo,
        hoje=hoje.isoformat(),
    )


if __name__ == "__main__":
    # Servidor de desenvolvimento. Em produção, o Gunicorn importa a variável `app`
    # diretamente (veja o arquivo de serviço systemd) e este bloco não é executado.
    app.run(debug=False, host="0.0.0.0", port=5000)

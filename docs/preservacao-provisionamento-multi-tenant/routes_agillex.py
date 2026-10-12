"""
Rotas de Cadastro (/agillex) e Expiração de Trial (/admin/trial-expirado)
Preservadas para evolução futura conforme Decisão 1 e Decisão 4 do projeto.

Contém a implementação completa e testada do formulário de auto-cadastro web,
validações no servidor, hashing, rate limiting e tratamento de expiração.
"""

import re
from flask import render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash

# Regex de validação de e-mail padronizado
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def validar_email(email):
    if not email or len(email) > 254:
        return False
    return bool(EMAIL_REGEX.match(email))


def registrar_rotas_agillex(app, limiter, db_session, database_ext, carregar_config_template):
    """
    Registra as rotas de auto-cadastro e expiração no app Flask quando o provisionamento for ativado.
    """

    @app.route("/agillex", methods=["GET", "POST"])
    @limiter.limit("5 per minute", methods=["POST"])
    def agillex():
        erro = None
        valores = {}
        config = carregar_config_template()

        if request.method == "POST":
            nome_estabelecimento = request.form.get("nome_estabelecimento", "").strip()
            nome_responsavel = request.form.get("nome_responsavel", "").strip()
            email = request.form.get("email", "").strip().lower()
            telefone = request.form.get("telefone", "").strip()
            usuario = request.form.get("usuario", "").strip().lower()
            senha = request.form.get("senha", "")
            confirmar_senha = request.form.get("confirmar_senha", "")
            termos = request.form.get("termos") == "1"

            valores = {
                "nome_estabelecimento": nome_estabelecimento,
                "nome_responsavel": nome_responsavel,
                "email": email,
                "telefone": telefone,
                "usuario": usuario,
                "termos": termos,
            }

            if not (nome_estabelecimento and nome_responsavel and email and telefone and usuario and senha and confirmar_senha):
                erro = "Por favor, preencha todos os campos obrigatórios."
            elif not termos:
                erro = "Você precisa concordar com os termos de uso para ativar o período de teste."
            elif not validar_email(email):
                erro = "Por favor, forneça um endereço de e-mail comercial válido."
            elif len("".join(c for c in telefone if c.isdigit())) < 10:
                erro = "O telefone informado deve conter DDD e pelo menos 10 dígitos numéricos."
            elif not re.match(r"^[a-zA-Z0-9_.-]{3,30}$", usuario):
                erro = "O nome de usuário deve conter de 3 a 30 caracteres alfanuméricos, ponto, traço ou sublinhado."
            elif len(senha) < 8:
                erro = "A senha deve ter no mínimo 8 caracteres."
            elif senha != confirmar_senha:
                erro = "A confirmação de senha não confere com a senha informada."
            else:
                with db_session() as conn:
                    admin_existente = conn.execute(
                        "SELECT id FROM admin WHERE LOWER(usuario) = LOWER(%s)",
                        (usuario,),
                    ).fetchone()
                    if admin_existente:
                        erro = "O nome de usuário informado já está em uso. Por favor, escolha outro."
                    else:
                        email_admin = conn.execute(
                            "SELECT id FROM admin WHERE LOWER(email) = LOWER(%s)",
                            (email,),
                        ).fetchone()
                        estab_email = database_ext.obter_estabelecimento_por_email(conn, email)
                        if email_admin or estab_email:
                            erro = "Este endereço de e-mail já está cadastrado. Se já possui uma conta, acesse o painel."
                        else:
                            try:
                                senha_hash = generate_password_hash(senha)
                                novo_estab = database_ext.criar_estabelecimento_com_admin(
                                    conn,
                                    nome_estabelecimento=nome_estabelecimento,
                                    nome_responsavel=nome_responsavel,
                                    email=email,
                                    telefone=telefone,
                                    usuario=usuario,
                                    senha_hash=senha_hash,
                                )
                                session["admin_logado"] = True
                                session["admin_usuario"] = usuario
                                session["estabelecimento_id"] = novo_estab["estabelecimento_id"]

                                return redirect(url_for("admin_dashboard"))
                            except Exception:
                                erro = "Ocorreu uma falha ao criar o cadastro. Por favor, tente novamente ou contate nosso suporte."

        return render_template(
            "agillex.html",
            erro=erro,
            valores=valores,
            **config,
        )

    @app.route("/admin/trial-expirado")
    def admin_trial_expirado():
        if not session.get("admin_logado"):
            return redirect(url_for("admin_login"))
        estab_id = session.get("estabelecimento_id")
        with db_session() as conn:
            info_trial = database_ext.verificar_status_trial(conn, estab_id)
        return render_template(
            "admin_trial_expirado.html",
            info_trial=info_trial,
            **carregar_config_template(),
        )

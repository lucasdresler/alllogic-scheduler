from datetime import datetime, timedelta
from functools import lru_cache
import re
import uuid

from database import db_session, obter_todas_configuracoes, obter_configuracoes_estabelecimento


def _carregar_configuracoes():
    with db_session() as conn:
        return obter_todas_configuracoes(conn)


@lru_cache(maxsize=1)
def _get_config(versao):
    return _carregar_configuracoes()


def _limpar_cache_config():
    _get_config.cache_clear()


def _obter_configuracoes_cacheadas():
    with db_session() as conn:
        row = conn.execute(
            "SELECT valor FROM configuracao WHERE chave = %s",
            ("__config_generation__",),
        ).fetchone()
    versao = row["valor"] if row else "0"
    return _get_config(versao)


def _obter_config(chave, padrao=None):
    config = _obter_configuracoes_cacheadas()
    valor = config.get(chave)
    if valor is None:
        return padrao
    return valor


def _obter_config_int(chave, padrao=None):
    valor = _obter_config(chave)
    if valor is None:
        return padrao
    try:
        return int(valor)
    except (ValueError, TypeError):
        return padrao


def _obter_config_lista_int(chave, padrao=None):
    valor = _obter_config(chave)
    if not valor:
        return padrao
    try:
        return [int(x.strip()) for x in valor.split(",") if x.strip()]
    except (ValueError, TypeError):
        return padrao


def listar_servicos_admin(estabelecimento_id=None):
    with db_session() as conn:
        if estabelecimento_id is not None:
            if estabelecimento_id == 1:
                rows = conn.execute(
                    "SELECT * FROM servico WHERE estabelecimento_id = 1 OR estabelecimento_id IS NULL ORDER BY ativo DESC, nome ASC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM servico WHERE estabelecimento_id = %s ORDER BY ativo DESC, nome ASC",
                    (estabelecimento_id,)
                ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM servico ORDER BY ativo DESC, nome ASC"
            ).fetchall()
        return [dict(row) for row in rows]


def criar_servico(nome, preco, duracao_minutos, ativo=True, descricao="", estabelecimento_id=None):
    nome = (nome or "").strip()
    descricao = (descricao or "").strip()
    if not nome:
        return None, "Nome do serviço é obrigatório."

    try:
        preco_valor = float(preco)
    except (TypeError, ValueError):
        return None, "Preço inválido."

    if preco_valor <= 0:
        return None, "Preço deve ser maior que zero."

    try:
        duracao = int(duracao_minutos)
    except (TypeError, ValueError):
        return None, "Duração inválida."

    if duracao <= 0:
        return None, "Duração deve ser maior que zero."

    estab_id = estabelecimento_id or 1
    with db_session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO servico (nome, descricao, preco, duracao_minutos, ativo, estabelecimento_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (nome, descricao, preco_valor, duracao, bool(ativo), estab_id),
        )
        servico_id = cursor.fetchone()["id"]
        return servico_id, None


def atualizar_servico(servico_id, nome, preco, duracao_minutos, ativo, descricao=""):
    nome = (nome or "").strip()
    descricao = (descricao or "").strip()
    if not nome:
        return False, "Nome do serviço é obrigatório."

    try:
        preco_valor = float(preco)
    except (TypeError, ValueError):
        return False, "Preço inválido."

    if preco_valor <= 0:
        return False, "Preço deve ser maior que zero."

    try:
        duracao = int(duracao_minutos)
    except (TypeError, ValueError):
        return False, "Duração inválida."

    if duracao <= 0:
        return False, "Duração deve ser maior que zero."

    with db_session() as conn:
        row = conn.execute(
            "SELECT id FROM servico WHERE id = %s",
            (servico_id,),
        ).fetchone()
        if not row:
            return False, "Serviço não encontrado."

        conn.execute(
            """
            UPDATE servico
            SET nome = %s, descricao = %s, preco = %s, duracao_minutos = %s, ativo = %s
            WHERE id = %s
            """,
            (nome, descricao, preco_valor, duracao, bool(ativo), servico_id),
        )
        return True, None


def alterar_status_servico(servico_id, ativo):
    with db_session() as conn:
        row = conn.execute(
            "SELECT id FROM servico WHERE id = %s",
            (servico_id,),
        ).fetchone()
        if not row:
            return False, "Serviço não encontrado."

        conn.execute(
            "UPDATE servico SET ativo = %s WHERE id = %s",
            (bool(ativo), servico_id),
        )
        return True, None


def excluir_servico(servico_id, estabelecimento_id=None):
    with db_session() as conn:
        cond_estab = ""
        params = [servico_id]
        if estabelecimento_id is not None:
            if estabelecimento_id == 1:
                cond_estab = " AND (estabelecimento_id = 1 OR estabelecimento_id IS NULL)"
            else:
                cond_estab = " AND estabelecimento_id = %s"
                params.append(estabelecimento_id)

        row = conn.execute(
            f"SELECT id, nome FROM servico WHERE id = %s{cond_estab}", tuple(params)
        ).fetchone()
        if not row:
            return False, "Serviço não encontrado."

        agendamentos_ativos = conn.execute(
            """
            SELECT COUNT(DISTINCT a.id) AS c
            FROM agendamento a
            LEFT JOIN agendamento_servico ags ON ags.agendamento_id = a.id
            WHERE (a.servico_id = %s OR ags.servico_id = %s)
              AND a.status != 'cancelado'
            """,
            (servico_id, servico_id),
        ).fetchone()["c"]
        if agendamentos_ativos > 0:
            return False, f"Não é possível excluir o serviço '{row['nome']}' porque existem {agendamentos_ativos} agendamento(s) ativo(s) vinculado(s) a ele. Você pode desativá-lo para que não apareça na agenda."

        # Remove agendamentos cancelados vinculados a este serviço para evitar violação de integridade referencial
        conn.execute("DELETE FROM agendamento WHERE servico_id = %s AND status = 'cancelado'", (servico_id,))
        conn.execute("DELETE FROM profissional_servico WHERE servico_id = %s", (servico_id,))
        conn.execute("DELETE FROM agendamento_servico WHERE servico_id = %s", (servico_id,))
        conn.execute("DELETE FROM servico WHERE id = %s", (servico_id,))
        return True, None


def listar_profissionais_admin(estabelecimento_id=None):
    with db_session() as conn:
        if estabelecimento_id is not None:
            if estabelecimento_id == 1:
                rows = conn.execute(
                    "SELECT * FROM profissional WHERE estabelecimento_id = 1 OR estabelecimento_id IS NULL ORDER BY ativo DESC, nome ASC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM profissional WHERE estabelecimento_id = %s ORDER BY ativo DESC, nome ASC",
                    (estabelecimento_id,)
                ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM profissional ORDER BY ativo DESC, nome ASC"
            ).fetchall()

        profissionais = []
        for row in rows:
            servicos = conn.execute(
                """
                SELECT s.id, s.nome, s.ativo
                FROM servico s
                JOIN profissional_servico ps ON ps.servico_id = s.id
                WHERE ps.profissional_id = %s
                ORDER BY s.nome ASC
                """,
                (row["id"],),
            ).fetchall()

            item = dict(row)
            item["servicos"] = [dict(servico) for servico in servicos]
            item["servico_ids"] = [servico["id"] for servico in servicos]
            profissionais.append(item)

        return profissionais


def criar_profissional(nome, ativo=True, servico_ids=None, estabelecimento_id=None):
    nome = (nome or "").strip()
    if not nome:
        return None, "Nome do profissional é obrigatório."

    servico_ids = list(dict.fromkeys(servico_ids or []))
    if bool(ativo) and not servico_ids:
        return None, "Selecione pelo menos um serviço para o profissional ativo."

    estab_id = estabelecimento_id or 1
    with db_session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO profissional (nome, ativo, estabelecimento_id)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (nome, bool(ativo), estab_id),
        )
        profissional_id = cursor.fetchone()["id"]

    if servico_ids:
        ok, erro = atualizar_profissional_servicos(profissional_id, servico_ids)
        if not ok:
            return None, erro

    return profissional_id, None


def atualizar_profissional(profissional_id, nome, ativo, servico_ids=None):
    nome = (nome or "").strip()
    if not nome:
        return False, "Nome do profissional é obrigatório."

    servico_ids = list(dict.fromkeys(servico_ids or []))
    if bool(ativo) and not servico_ids:
        return False, "Selecione pelo menos um serviço para o profissional ativo."

    with db_session() as conn:
        row = conn.execute(
            "SELECT id FROM profissional WHERE id = %s",
            (profissional_id,),
        ).fetchone()
        if not row:
            return False, "Profissional não encontrado."

        conn.execute(
            "UPDATE profissional SET nome = %s, ativo = %s WHERE id = %s",
            (nome, bool(ativo), profissional_id),
        )

    if servico_ids:
        ok, erro = atualizar_profissional_servicos(profissional_id, servico_ids)
        if not ok:
            return False, erro
    else:
        ok, erro = atualizar_profissional_servicos(profissional_id, [])
        if not ok:
            return False, erro

    return True, None


def alterar_status_profissional(profissional_id, ativo):
    with db_session() as conn:
        row = conn.execute(
            "SELECT id FROM profissional WHERE id = %s",
            (profissional_id,),
        ).fetchone()
        if not row:
            return False, "Profissional não encontrado."

        conn.execute(
            "UPDATE profissional SET ativo = %s WHERE id = %s",
            (bool(ativo), profissional_id),
        )
        return True, None


def excluir_profissional(profissional_id, estabelecimento_id=None):
    with db_session() as conn:
        cond_estab = ""
        params = [profissional_id]
        if estabelecimento_id is not None:
            if estabelecimento_id == 1:
                cond_estab = " AND (estabelecimento_id = 1 OR estabelecimento_id IS NULL)"
            else:
                cond_estab = " AND estabelecimento_id = %s"
                params.append(estabelecimento_id)

        row = conn.execute(
            f"SELECT id, nome FROM profissional WHERE id = %s{cond_estab}", tuple(params)
        ).fetchone()
        if not row:
            return False, "Profissional não encontrado."

        agendamentos_ativos = conn.execute(
            "SELECT COUNT(*) AS c FROM agendamento WHERE profissional_id = %s AND status != 'cancelado'",
            (profissional_id,),
        ).fetchone()["c"]
        if agendamentos_ativos > 0:
            return False, f"Não é possível excluir o profissional '{row['nome']}' porque existem {agendamentos_ativos} agendamento(s) ativo(s) vinculado(s) a ele. Você pode desativá-lo para que não apareça na agenda."

        # Remove agendamentos cancelados vinculados a este profissional para evitar violação de integridade referencial
        conn.execute("DELETE FROM agendamento WHERE profissional_id = %s AND status = 'cancelado'", (profissional_id,))
        conn.execute("DELETE FROM profissional_disponibilidade WHERE profissional_id = %s", (profissional_id,))
        conn.execute("DELETE FROM profissional_servico WHERE profissional_id = %s", (profissional_id,))
        conn.execute("DELETE FROM profissional WHERE id = %s", (profissional_id,))
        return True, None


def atualizar_profissional_servicos(profissional_id, servico_ids):
    servico_ids = list(dict.fromkeys(servico_ids or []))

    with db_session() as conn:
        row = conn.execute(
            "SELECT id FROM profissional WHERE id = %s",
            (profissional_id,),
        ).fetchone()
        if not row:
            return False, "Profissional não encontrado."

        if servico_ids:
            existentes = conn.execute(
                "SELECT id FROM servico WHERE id = ANY(%s)",
                (servico_ids,),
            ).fetchall()
            ids_existentes = {item["id"] for item in existentes}
            faltantes = [servico_id for servico_id in servico_ids if servico_id not in ids_existentes]
            if faltantes:
                return False, "Há serviços inválidos na associação."

        conn.execute(
            "DELETE FROM profissional_servico WHERE profissional_id = %s",
            (profissional_id,),
        )

        if servico_ids:
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO profissional_servico (profissional_id, servico_id) VALUES (%s, %s)",
                    [(profissional_id, servico_id) for servico_id in servico_ids],
                )

    return True, None


DIAS_DA_SEMANA = [
    {"numero": 0, "nome": "Domingo"},
    {"numero": 1, "nome": "Segunda-feira"},
    {"numero": 2, "nome": "Terça-feira"},
    {"numero": 3, "nome": "Quarta-feira"},
    {"numero": 4, "nome": "Quinta-feira"},
    {"numero": 5, "nome": "Sexta-feira"},
    {"numero": 6, "nome": "Sábado"},
]


def obter_disponibilidade_profissional(profissional_id):
    """
    Retorna uma lista ordenada com a disponibilidade dos 7 dias da semana (Segunda a Domingo).
    Se o profissional não possuir registros individuais, retorna os padrões baseados no estabelecimento.
    """
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT dia_semana, horario_entrada, horario_saida, ativo
            FROM profissional_disponibilidade
            WHERE profissional_id = %s
            """,
            (profissional_id,),
        ).fetchall()

    cadastrados = {r["dia_semana"]: dict(r) for r in rows}
    tem_customizado = len(cadastrados) > 0

    abertura_padrao = horario_abertura()
    fechamento_padrao = horario_fechamento()
    dias_estab = dias_funcionamento()

    resultado = []
    for info in DIAS_DA_SEMANA:
        dia_num = info["numero"]
        if tem_customizado and dia_num in cadastrados:
            c = cadastrados[dia_num]
            resultado.append({
                "dia_semana": dia_num,
                "nome_dia": info["nome"],
                "ativo": bool(c["ativo"]),
                "horario_entrada": c["horario_entrada"] or "",
                "horario_saida": c["horario_saida"] or "",
            })
        else:
            resultado.append({
                "dia_semana": dia_num,
                "nome_dia": info["nome"],
                "ativo": (dia_num in dias_estab) if not tem_customizado else False,
                "horario_entrada": abertura_padrao,
                "horario_saida": fechamento_padrao,
            })

    return resultado


def validar_disponibilidade_profissional(itens_disponibilidade):
    """
    Valida a lista de disponibilidade semanal de um profissional.
    Retorna (True, None) se válido ou (False, mensagem_erro) se inválido.
    """
    nomes_por_numero = {d["numero"]: d["nome"] for d in DIAS_DA_SEMANA}

    for item in itens_disponibilidade:
        dia_num = item.get("dia_semana")
        if dia_num not in nomes_por_numero:
            return False, "Dia da semana inválido."

        nome_dia = nomes_por_numero[dia_num]
        ativo = bool(item.get("ativo"))
        entrada = (item.get("horario_entrada") or "").strip()
        saida = (item.get("horario_saida") or "").strip()

        if ativo:
            if not entrada or not saida:
                return False, f"{nome_dia}: horários de entrada e saída são obrigatórios quando o dia estiver ativo."

            try:
                hora_ent = datetime.strptime(entrada, "%H:%M")
                hora_sai = datetime.strptime(saida, "%H:%M")
            except (ValueError, TypeError):
                return False, f"{nome_dia}: formato de horário inválido. Utilize o formato HH:MM."

            if hora_sai <= hora_ent:
                return False, f"{nome_dia}: o horário de saída deve ser posterior ao horário de entrada."

    return True, None


def salvar_disponibilidade_profissional(profissional_id, itens_disponibilidade):
    """
    Salva a disponibilidade semanal do profissional no banco.
    """
    ok, erro = validar_disponibilidade_profissional(itens_disponibilidade)
    if not ok:
        return False, erro

    with db_session() as conn:
        row = conn.execute(
            "SELECT id FROM profissional WHERE id = %s",
            (profissional_id,),
        ).fetchone()
        if not row:
            return False, "Profissional não encontrado."

        with conn.cursor() as cur:
            for item in itens_disponibilidade:
                dia_num = item["dia_semana"]
                ativo = bool(item.get("ativo"))
                entrada = (item.get("horario_entrada") or "").strip() if ativo else ""
                saida = (item.get("horario_saida") or "").strip() if ativo else ""

                cur.execute(
                    """
                    INSERT INTO profissional_disponibilidade (
                        profissional_id, dia_semana, horario_entrada, horario_saida, ativo
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (profissional_id, dia_semana) DO UPDATE SET
                        horario_entrada = EXCLUDED.horario_entrada,
                        horario_saida = EXCLUDED.horario_saida,
                        ativo = EXCLUDED.ativo
                    """,
                    (profissional_id, dia_num, entrada, saida, ativo),
                )

    return True, None


# Propriedades dinâmicas que leem do cache a cada acesso
def horario_abertura():
    return _obter_config("horario_abertura", "09:00")


def horario_fechamento():
    return _obter_config("horario_fechamento", "19:00")


def intervalo_slot_minutos():
    return _obter_config_int("intervalo_slot_minutos", 30)


def dias_funcionamento():
    return _obter_config_lista_int("dias_funcionamento", [0, 1, 2, 3, 4, 5])


def dias_antecedencia_agendamento():
    return _obter_config_int("dias_antecedencia_agendamento", 14)


def nome_estabelecimento():
    return _obter_config("nome_estabelecimento", "AllLogic Scheduler")


def telefone_estabelecimento():
    return _obter_config("telefone_estabelecimento", "")


def endereco_estabelecimento():
    return _obter_config("endereco_estabelecimento", "")


def nome_publico():
    return _obter_config("nome_publico", "AllLogic Scheduler")


# Aliases para compatibilidade com código existente que importa as constantes
HORARIO_ABERTURA = horario_abertura()
HORARIO_FECHAMENTO = horario_fechamento()
INTERVALO_SLOT_MINUTOS = intervalo_slot_minutos()
DIAS_FUNCIONAMENTO = dias_funcionamento()
DIAS_ANTECEDENCIA_AGENDAMENTO = dias_antecedencia_agendamento()
NOME_ESTABELECIMENTO = nome_estabelecimento()
TELEFONE_ESTABELECIMENTO = telefone_estabelecimento()
ENDERECO_ESTABELECIMENTO = endereco_estabelecimento()
NOME_PUBLICO = nome_publico()


def listar_servicos(apenas_ativos=True, estabelecimento_id=None):
    with db_session() as conn:
        conds = []
        params = []
        if apenas_ativos:
            conds.append("ativo = TRUE")
        if estabelecimento_id is not None:
            if estabelecimento_id == 1:
                conds.append("(estabelecimento_id = 1 OR estabelecimento_id IS NULL)")
            else:
                conds.append("estabelecimento_id = %s")
                params.append(estabelecimento_id)
        where = f"WHERE {' AND '.join(conds)}" if conds else ""
        rows = conn.execute(f"SELECT * FROM servico {where} ORDER BY id", tuple(params)).fetchall()
        return [dict(r) for r in rows]


def obter_servico(servico_id):
    with db_session() as conn:
        row = conn.execute("SELECT * FROM servico WHERE id = %s", (servico_id,)).fetchone()
        return dict(row) if row else None


def listar_profissionais(apenas_ativos=True, estabelecimento_id=None):
    with db_session() as conn:
        conds = []
        params = []
        if apenas_ativos:
            conds.append("ativo = TRUE")
        if estabelecimento_id is not None:
            if estabelecimento_id == 1:
                conds.append("(estabelecimento_id = 1 OR estabelecimento_id IS NULL)")
            else:
                conds.append("estabelecimento_id = %s")
                params.append(estabelecimento_id)
        where = f"WHERE {' AND '.join(conds)}" if conds else ""
        rows = conn.execute(f"SELECT * FROM profissional {where} ORDER BY nome", tuple(params)).fetchall()
        return [dict(r) for r in rows]


def listar_profissionais_para_servicos(servico_ids, estabelecimento_id=None):
    servico_ids = list(dict.fromkeys(servico_ids or []))
    if not servico_ids:
        return listar_profissionais(apenas_ativos=True, estabelecimento_id=estabelecimento_id)

    with db_session() as conn:
        cond_estab = ""
        if estabelecimento_id is not None:
            if estabelecimento_id == 1:
                cond_estab = "AND (p.estabelecimento_id = 1 OR p.estabelecimento_id IS NULL)"
                params = [servico_ids, len(servico_ids)]
            else:
                cond_estab = "AND p.estabelecimento_id = %s"
                params = [estabelecimento_id, servico_ids, len(servico_ids)]
        else:
            params = [servico_ids, len(servico_ids)]

        rows = conn.execute(
            f"""
            SELECT p.id, p.nome, p.ativo
            FROM profissional AS p
            JOIN profissional_servico AS ps ON ps.profissional_id = p.id
            JOIN servico AS s ON s.id = ps.servico_id
            WHERE p.ativo = TRUE
              AND s.ativo = TRUE
              {cond_estab}
              AND s.id = ANY(%s)
            GROUP BY p.id, p.nome, p.ativo
            HAVING COUNT(DISTINCT s.id) = %s
            ORDER BY p.nome ASC
            """,
            tuple(params),
        ).fetchall()
        return [dict(row) for row in rows]


def obter_profissional(profissional_id):
    with db_session() as conn:
        row = conn.execute("SELECT * FROM profissional WHERE id = %s", (profissional_id,)).fetchone()
        return dict(row) if row else None


def _gerar_slots_intervalo(inicio_dt, fim_dt, intervalo):
    try:
        slots = []
        if intervalo <= 0 or inicio_dt >= fim_dt:
            return slots
        atual = inicio_dt
        while atual < fim_dt:
            slots.append(atual.strftime("%H:%M"))
            atual += timedelta(minutes=intervalo)
        return slots
    except (TypeError, ValueError):
        return []


def _gerar_slots_do_dia(estabelecimento_id=None):
    try:
        with db_session() as conn:
            cfg = obter_configuracoes_estabelecimento(conn, estabelecimento_id or 1)
        inicio = datetime.strptime(cfg.get("horario_abertura", "09:00"), "%H:%M")
        fim = datetime.strptime(cfg.get("horario_fechamento", "19:00"), "%H:%M")
        intervalo = int(cfg.get("intervalo_slot_minutos", 30))
        return _gerar_slots_intervalo(inicio, fim, intervalo)
    except (TypeError, ValueError):
        return []


def data_permitida(data_str, estabelecimento_id=None):
    """Valida se a data está dentro do funcionamento do estabelecimento (dia permitido, futuro e limite de antecedência)."""
    try:
        data = datetime.strptime(data_str, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return False
    hoje = datetime.now().date()
    if data < hoje:
        return False

    with db_session() as conn:
        cfg = obter_configuracoes_estabelecimento(conn, estabelecimento_id or 1)

    dias_func_raw = cfg.get("dias_funcionamento", "1,2,3,4,5,6")
    if isinstance(dias_func_raw, str):
        dias_permitidos = [int(x.strip()) for x in dias_func_raw.split(",") if x.strip()]
    elif isinstance(dias_func_raw, (list, tuple)):
        dias_permitidos = [int(x) for x in dias_func_raw]
    else:
        dias_permitidos = [0, 1, 2, 3, 4, 5]

    if (data.weekday() + 1) % 7 not in dias_permitidos:
        return False

    max_dias = cfg.get("dias_antecedencia_agendamento", 14)
    if max_dias is not None:
        try:
            if (data - hoje).days > int(max_dias):
                return False
        except (ValueError, TypeError):
            pass
    return True


def _horarios_disponiveis_conn(conn, profissional_id, data_str, servico_ids, ignorar_agendamento_id=None):
    profissional = conn.execute(
        "SELECT ativo, estabelecimento_id FROM profissional WHERE id = %s",
        (profissional_id,),
    ).fetchone()
    if not profissional or not profissional["ativo"]:
        return []

    p_estab_id = profissional.get("estabelecimento_id") or 1
    cfg_estab = obter_configuracoes_estabelecimento(conn, p_estab_id)

    servicos = conn.execute(
        """
        SELECT id, duracao_minutos
        FROM servico
        WHERE id = ANY(%s) AND ativo = TRUE
        """,
        (servico_ids,),
    ).fetchall()
    if len(servicos) != len(servico_ids):
        return []

    vinculos = conn.execute(
        """
        SELECT servico_id
        FROM profissional_servico
        WHERE profissional_id = %s AND servico_id = ANY(%s)
        """,
        (profissional_id, servico_ids),
    ).fetchall()
    if {row["servico_id"] for row in vinculos} != set(servico_ids):
        return []

    duracao_total = sum(servico["duracao_minutos"] for servico in servicos)
    data = datetime.strptime(data_str, "%Y-%m-%d").date()
    dia_semana = (data.weekday() + 1) % 7

    # Consulta disponibilidade individual do profissional
    disp_rows = conn.execute(
        """
        SELECT dia_semana, horario_entrada, horario_saida, ativo
        FROM profissional_disponibilidade
        WHERE profissional_id = %s
        """,
        (profissional_id,),
    ).fetchall()

    abertura_estab_str = cfg_estab.get("horario_abertura", "09:00")
    fechamento_estab_str = cfg_estab.get("horario_fechamento", "19:00")
    intervalo_minutos = int(cfg_estab.get("intervalo_slot_minutos", 30))

    if disp_rows:
        disp_dia = next((r for r in disp_rows if r["dia_semana"] == dia_semana), None)
        if not disp_dia or not disp_dia["ativo"] or not disp_dia["horario_entrada"] or not disp_dia["horario_saida"]:
            return []

        try:
            prof_entrada = datetime.strptime(disp_dia["horario_entrada"], "%H:%M")
            prof_saida = datetime.strptime(disp_dia["horario_saida"], "%H:%M")
            estab_abertura = datetime.strptime(abertura_estab_str, "%H:%M")
            estab_fechamento = datetime.strptime(fechamento_estab_str, "%H:%M")
        except (ValueError, TypeError):
            return []

        inicio_jornada = max(prof_entrada, estab_abertura)
        fim_jornada = min(prof_saida, estab_fechamento)
        if inicio_jornada >= fim_jornada:
            return []
    else:
        # Fallback para profissionais sem jornada individual cadastrada
        inicio_jornada = datetime.strptime(abertura_estab_str, "%H:%M")
        fim_jornada = datetime.strptime(fechamento_estab_str, "%H:%M")

    limite_saida = datetime.combine(data, fim_jornada.time())

    query_ocupados = """
        SELECT a.hora,
               COALESCE(SUM(COALESCE(ags.duracao_minutos, s.duracao_minutos)), 0)
                   AS duracao_minutos
        FROM agendamento AS a
        JOIN agendamento_servico AS ags ON ags.agendamento_id = a.id
        JOIN servico AS s ON s.id = ags.servico_id
        WHERE a.profissional_id = %s
          AND a.data = %s
          AND a.status = 'agendado'
    """
    params_ocupados = [profissional_id, data_str]
    if ignorar_agendamento_id is not None:
        query_ocupados += " AND a.id != %s"
        params_ocupados.append(ignorar_agendamento_id)
    query_ocupados += " GROUP BY a.id, a.hora"

    ocupados = conn.execute(query_ocupados, tuple(params_ocupados)).fetchall()

    agora = datetime.now()
    disponiveis = []
    slots_dia = _gerar_slots_intervalo(inicio_jornada, fim_jornada, intervalo_minutos)
    for slot in slots_dia:
        inicio = datetime.combine(data, datetime.strptime(slot, "%H:%M").time())
        fim = inicio + timedelta(minutes=duracao_total)
        if fim > limite_saida or (data == agora.date() and inicio <= agora):
            continue

        conflito = False
        for agendamento in ocupados:
            inicio_ocupado = datetime.combine(
                data,
                datetime.strptime(agendamento["hora"], "%H:%M").time(),
            )
            fim_ocupado = inicio_ocupado + timedelta(
                minutes=agendamento["duracao_minutos"]
            )
            if inicio < fim_ocupado and inicio_ocupado < fim:
                conflito = True
                break

        if not conflito:
            disponiveis.append(slot)

    return disponiveis


def horarios_disponiveis(profissional_id, data_str, servico_ids, ignorar_agendamento_id=None):
    """Retorna horários livres considerando os serviços e estados atuais."""
    with db_session() as conn:
        row_p = conn.execute("SELECT estabelecimento_id FROM profissional WHERE id = %s", (profissional_id,)).fetchone()
        estab_id = row_p.get("estabelecimento_id") if row_p else 1

    if not data_permitida(data_str, estabelecimento_id=estab_id):
        return []
    if isinstance(servico_ids, int):
        servico_ids = [servico_ids]
    servico_ids = list(dict.fromkeys(servico_ids or []))
    if not servico_ids or any(type(item) is not int or item <= 0 for item in servico_ids):
        return []

    with db_session() as conn:
        return _horarios_disponiveis_conn(
            conn,
            profissional_id,
            data_str,
            servico_ids,
            ignorar_agendamento_id=ignorar_agendamento_id,
        )


def criar_agendamento(cliente_nome, cliente_telefone, servico_ids, profissional_id, data_str, hora_str, estabelecimento_id=None):
    """Cria o agendamento e seus serviços, revalidando a disponibilidade com lock de concorrência."""
    if isinstance(servico_ids, int):
        servico_ids = [servico_ids]
    servico_ids = list(dict.fromkeys(servico_ids or []))
    if not servico_ids or any(type(item) is not int or item <= 0 for item in servico_ids):
        return None, "Selecione pelo menos um serviço."
    if type(profissional_id) is not int or profissional_id <= 0:
        return None, "Profissional inválido."

    with db_session() as conn:
        row_prof = conn.execute(
            "SELECT nome, estabelecimento_id FROM profissional WHERE id = %s AND ativo = TRUE",
            (profissional_id,),
        ).fetchone()
        if not row_prof:
            return None, "Profissional inválido."

        estab_id = estabelecimento_id or row_prof.get("estabelecimento_id") or 1
        if not data_permitida(data_str, estabelecimento_id=estab_id):
            return None, "Data indisponível para agendamento."

        lock_key = (profissional_id * 1000000) + int(data_str.replace("-", ""))
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (lock_key,))
        if not data_permitida(data_str, estabelecimento_id=estab_id):
            return None, "Data indisponível para agendamento."

        disponiveis = _horarios_disponiveis_conn(
            conn,
            profissional_id,
            data_str,
            servico_ids,
        )
        if hora_str not in disponiveis:
            return None, "Horário não disponível. Escolha outro horário."

        servicos = conn.execute(
            """
            SELECT id, nome, preco, duracao_minutos
            FROM servico
            WHERE id = ANY(%s) AND ativo = TRUE
            ORDER BY id
            """,
            (servico_ids,),
        ).fetchall()
        if len(servicos) != len(servico_ids):
            return None, "Serviço inválido."

        primeiro_servico_id = servico_ids[0]
        cliente_id = _obter_ou_criar_cliente_conn(conn, cliente_nome, cliente_telefone, estabelecimento_id=estab_id)
        token_acesso = uuid.uuid4().hex

        cursor = conn.execute(
            """
            INSERT INTO agendamento (
                cliente_id,
                cliente_nome,
                cliente_telefone,
                servico_id,
                profissional_id,
                data,
                hora,
                profissional_nome_snapshot,
                token_acesso,
                estabelecimento_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                cliente_id,
                cliente_nome,
                cliente_telefone,
                primeiro_servico_id,
                profissional_id,
                data_str,
                hora_str,
                row_prof["nome"],
                token_acesso,
                estab_id,
            ),
        )
        agendamento_id = cursor.fetchone()["id"]

        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO agendamento_servico (
                    agendamento_id,
                    servico_id,
                    nome_servico,
                    preco_unitario,
                    duracao_minutos
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (agendamento_id, servico_id) DO NOTHING
                """,
                [
                    (
                        agendamento_id,
                        servico["id"],
                        servico["nome"],
                        servico["preco"],
                        servico["duracao_minutos"],
                    )
                    for servico in servicos
                ],
            )

    return agendamento_id, None


def obter_agendamento_completo(agendamento_id):
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT a.*,
                   COALESCE(a.profissional_nome_snapshot, p.nome) AS profissional_nome,
                   COALESCE(
                       json_agg(
                           json_build_object(
                               'id', COALESCE(ags.servico_id, s.id),
                               'nome', COALESCE(ags.nome_servico, s.nome),
                               'preco', COALESCE(ags.preco_unitario, s.preco),
                               'duracao_minutos', COALESCE(ags.duracao_minutos, s.duracao_minutos)
                           )
                           ORDER BY COALESCE(ags.servico_id, s.id)
                       ) FILTER (WHERE ags.servico_id IS NOT NULL OR s.id IS NOT NULL),
                       '[]'::json
                   ) AS servicos
            FROM agendamento a
            LEFT JOIN profissional p ON p.id = a.profissional_id
            LEFT JOIN agendamento_servico ags ON ags.agendamento_id = a.id
            LEFT JOIN servico s ON s.id = ags.servico_id
            WHERE a.id = %s
            GROUP BY a.id, p.nome
            """,
            (agendamento_id,),
        ).fetchone()

        if not row:
            return None

        resultado = dict(row)
        resultado["servico_nome"] = ", ".join(
            servico["nome"] for servico in resultado["servicos"]
        )
        resultado["servico_preco"] = sum(
            servico["preco"] for servico in resultado["servicos"]
        )
        resultado["servico_duracao_minutos"] = sum(
            servico["duracao_minutos"] for servico in resultado["servicos"]
        )

        return resultado


def listar_agendamentos_por_periodo(data_inicio_str, data_fim_str, profissional_id=None, estabelecimento_id=None):
    with db_session() as conn:
        query = """
            SELECT a.*,
                   COALESCE(a.profissional_nome_snapshot, p.nome) AS profissional_nome,
                   COALESCE(
                       json_agg(
                           json_build_object(
                               'id', COALESCE(ags.servico_id, s.id),
                               'nome', COALESCE(ags.nome_servico, s.nome),
                               'preco', COALESCE(ags.preco_unitario, s.preco),
                               'duracao_minutos', COALESCE(ags.duracao_minutos, s.duracao_minutos)
                           )
                           ORDER BY COALESCE(ags.servico_id, s.id)
                       ) FILTER (WHERE ags.servico_id IS NOT NULL OR s.id IS NOT NULL),
                       '[]'::json
                   ) AS servicos
            FROM agendamento a
            LEFT JOIN profissional p ON p.id = a.profissional_id
            LEFT JOIN agendamento_servico ags ON ags.agendamento_id = a.id
            LEFT JOIN servico s ON s.id = ags.servico_id
            WHERE a.data BETWEEN %s AND %s
        """
        params = [data_inicio_str, data_fim_str]
        if profissional_id is not None:
            query += " AND a.profissional_id = %s"
            params.append(profissional_id)

        if estabelecimento_id is not None:
            if estabelecimento_id == 1:
                query += " AND (a.estabelecimento_id = 1 OR a.estabelecimento_id IS NULL)"
            else:
                query += " AND a.estabelecimento_id = %s"
                params.append(estabelecimento_id)

        query += """
            GROUP BY a.id, p.nome
            ORDER BY a.data ASC, a.hora ASC
        """
        rows = conn.execute(query, tuple(params)).fetchall()

        agora = datetime.now()
        resultados = []

        for row in rows:
            resultado = dict(row)
            resultado["servico_nome"] = ", ".join(
                servico["nome"] for servico in resultado["servicos"]
            )
            resultado["servico_preco"] = sum(
                servico["preco"] for servico in resultado["servicos"]
            )
            resultado["servico_duracao_minutos"] = sum(
                servico["duracao_minutos"] for servico in resultado["servicos"]
            )
            try:
                dt_ag = datetime.strptime(f"{resultado['data']} {resultado['hora']}", "%Y-%m-%d %H:%M")
                resultado["ja_passou"] = dt_ag <= agora
            except Exception:
                resultado["ja_passou"] = False

            resultados.append(resultado)

        return resultados


def _normalizar_data_iso(data_str):
    """Converte datas em formatos variados (ex.: DD/MM/AAAA) para o padrão ISO (YYYY-MM-DD)."""
    if not data_str:
        return None
    data_str = data_str.strip()
    if not data_str:
        return None
    if "/" in data_str:
        partes = data_str.split("/")
        if len(partes) == 3:
            try:
                d, m, y = int(partes[0]), int(partes[1]), int(partes[2])
                return f"{y:04d}-{m:02d}-{d:02d}"
            except ValueError:
                pass
    return data_str


def pesquisar_agendamentos(
    cliente=None,
    telefone=None,
    profissional_id=None,
    status=None,
    data_inicio=None,
    data_fim=None,
    estabelecimento_id=None,
):
    """
    Pesquisa agendamentos com filtros combináveis:
    - cliente: busca textual (ILIKE) pelo nome do cliente;
    - telefone: busca por dígitos ou formatação;
    - profissional_id: ID do profissional (ou None para todos);
    - status: status específico (ou None/vazio para todos);
    - data_inicio: limite inferior de data (YYYY-MM-DD);
    - data_fim: limite superior de data (YYYY-MM-DD);
    - estabelecimento_id: filtro por tenant.
    """
    with db_session() as conn:
        query = """
            SELECT a.*,
                   COALESCE(a.profissional_nome_snapshot, p.nome) AS profissional_nome,
                   COALESCE(
                       json_agg(
                           json_build_object(
                               'id', COALESCE(ags.servico_id, s.id),
                               'nome', COALESCE(ags.nome_servico, s.nome),
                               'preco', COALESCE(ags.preco_unitario, s.preco),
                               'duracao_minutos', COALESCE(ags.duracao_minutos, s.duracao_minutos)
                           )
                           ORDER BY COALESCE(ags.servico_id, s.id)
                       ) FILTER (WHERE ags.servico_id IS NOT NULL OR s.id IS NOT NULL),
                       '[]'::json
                   ) AS servicos
            FROM agendamento a
            LEFT JOIN profissional p ON p.id = a.profissional_id
            LEFT JOIN agendamento_servico ags ON ags.agendamento_id = a.id
            LEFT JOIN servico s ON s.id = ags.servico_id
            WHERE 1=1
        """
        params = []

        if estabelecimento_id is not None:
            if estabelecimento_id == 1:
                query += " AND (a.estabelecimento_id = 1 OR a.estabelecimento_id IS NULL)"
            else:
                query += " AND a.estabelecimento_id = %s"
                params.append(estabelecimento_id)

        if cliente and cliente.strip():
            query += " AND a.cliente_nome ILIKE %s"
            params.append(f"%{cliente.strip()}%")

        if telefone and telefone.strip():
            tel_limpo = telefone.strip()
            digitos = "".join(c for c in tel_limpo if c.isdigit())
            if digitos:
                query += " AND (a.cliente_telefone ILIKE %s OR REGEXP_REPLACE(a.cliente_telefone, '\\D', '', 'g') LIKE %s)"
                params.append(f"%{tel_limpo}%")
                params.append(f"%{digitos}%")
            else:
                query += " AND a.cliente_telefone ILIKE %s"
                params.append(f"%{tel_limpo}%")

        if profissional_id is not None:
            query += " AND a.profissional_id = %s"
            params.append(profissional_id)

        if status and status.strip() and status.strip().lower() != "todos":
            query += " AND a.status = %s"
            params.append(status.strip())

        data_inicio_iso = _normalizar_data_iso(data_inicio) if data_inicio else None
        data_fim_iso = _normalizar_data_iso(data_fim) if data_fim else None

        if data_inicio_iso:
            query += " AND a.data >= %s"
            params.append(data_inicio_iso)

        if data_fim_iso:
            query += " AND a.data <= %s"
            params.append(data_fim_iso)

        query += """
            GROUP BY a.id, p.nome
            ORDER BY a.data ASC, a.hora ASC, a.id ASC
        """
        rows = conn.execute(query, tuple(params)).fetchall()

        agora = datetime.now()
        resultados = []

        for row in rows:
            resultado = dict(row)
            resultado["servico_nome"] = ", ".join(
                servico["nome"] for servico in resultado["servicos"]
            )
            resultado["servico_preco"] = sum(
                servico["preco"] for servico in resultado["servicos"]
            )
            resultado["servico_duracao_minutos"] = sum(
                servico["duracao_minutos"] for servico in resultado["servicos"]
            )
            try:
                dt_ag = datetime.strptime(f"{resultado['data']} {resultado['hora']}", "%Y-%m-%d %H:%M")
                resultado["ja_passou"] = dt_ag <= agora
            except Exception:
                resultado["ja_passou"] = False

            resultados.append(resultado)

        return resultados


def cancelar_agendamento(agendamento_id, usuario=None):
    """Cancela um agendamento preservando seu registro histórico e impedindo cancelamento duplicado."""
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT id, status
            FROM agendamento
            WHERE id = %s
            FOR UPDATE
            """,
            (agendamento_id,),
        ).fetchone()

        if not row:
            return False, "Agendamento não encontrado."

        if row["status"] == "cancelado":
            return False, "Este agendamento já está cancelado."

        if row["status"] in ("realizado", "nao_compareceu"):
            return False, f"Não é possível cancelar um agendamento com status '{row['status']}'."

        conn.execute(
            """
            UPDATE agendamento
            SET status = 'cancelado'
            WHERE id = %s
            """,
            (agendamento_id,),
        )
        conn.execute(
            """
            INSERT INTO agendamento_status_historico (
                agendamento_id, status_anterior, status_novo, usuario
            )
            VALUES (%s, %s, 'cancelado', %s)
            """,
            (agendamento_id, row["status"], usuario),
        )
        return True, None


def excluir_agendamento(agendamento_id, estabelecimento_id=None):
    """Exclui permanentemente um agendamento com status 'cancelado'."""
    with db_session() as conn:
        cond_estab = ""
        params = [agendamento_id]
        if estabelecimento_id is not None:
            if estabelecimento_id == 1:
                cond_estab = " AND (estabelecimento_id = 1 OR estabelecimento_id IS NULL)"
            else:
                cond_estab = " AND estabelecimento_id = %s"
                params.append(estabelecimento_id)

        row = conn.execute(
            f"SELECT id, status, cliente_nome FROM agendamento WHERE id = %s{cond_estab}",
            tuple(params),
        ).fetchone()

        if not row:
            return False, "Agendamento não encontrado."

        if row["status"] != "cancelado":
            return False, "Apenas agendamentos cancelados podem ser excluídos permanentemente."

        conn.execute("DELETE FROM agendamento WHERE id = %s", (agendamento_id,))
        return True, None


def atualizar_status_agendamento(agendamento_id, novo_status, usuario=None):
    """
    Atualiza o status de um agendamento para 'realizado' ou 'nao_compareceu'.
    Não permite alterar atendimentos futuros e preserva o histórico.
    """
    if novo_status not in ("realizado", "nao_compareceu"):
        return False, "Status inválido."

    with db_session() as conn:
        row = conn.execute(
            """
            SELECT id, data, hora, status
            FROM agendamento
            WHERE id = %s
            FOR UPDATE
            """,
            (agendamento_id,),
        ).fetchone()

        if not row:
            return False, "Agendamento não encontrado."

        if row["status"] != "agendado":
            return False, f"Apenas agendamentos ativos podem ter status alterado (status atual: {row['status']})."

        agora = datetime.now()
        try:
            dt_agendamento = datetime.strptime(f"{row['data']} {row['hora']}", "%Y-%m-%d %H:%M")
        except Exception:
            return False, "Data ou horário do agendamento inválidos."

        if dt_agendamento > agora:
            return False, "Não é permitido marcar como realizado ou não compareceu atendimentos futuros."

        conn.execute(
            """
            UPDATE agendamento
            SET status = %s
            WHERE id = %s
            """,
            (novo_status, agendamento_id),
        )
        conn.execute(
            """
            INSERT INTO agendamento_status_historico (
                agendamento_id, status_anterior, status_novo, usuario
            )
            VALUES (%s, %s, %s, %s)
            """,
            (agendamento_id, row["status"], novo_status, usuario),
        )
        return True, None


def reagendar_agendamento(agendamento_id, nova_data, novo_horario, usuario=None):
    """
    Altera data e horário de um agendamento preservando cliente, serviços, snapshots e histórico.
    Valida disponibilidade completa no mesmo motor do agendamento público, ignorando o próprio agendamento.
    A operação é estritamente transacional.
    """
    with db_session() as conn:
        ag = conn.execute(
            """
            SELECT id, profissional_id, data, hora, status
            FROM agendamento
            WHERE id = %s
            FOR UPDATE
            """,
            (agendamento_id,),
        ).fetchone()

        if not ag:
            return False, "Agendamento não encontrado."

        if ag["status"] != "agendado":
            return False, f"Apenas agendamentos ativos podem ser reagendados (status atual: {ag['status']})."

        if nova_data == ag["data"] and novo_horario == ag["hora"]:
            return False, "A nova data e horário devem ser diferentes dos atuais."

        # Buscar serviços vinculados
        servicos_rows = conn.execute(
            """
            SELECT servico_id
            FROM agendamento_servico
            WHERE agendamento_id = %s
            ORDER BY servico_id
            """,
            (agendamento_id,),
        ).fetchall()

        if not servicos_rows:
            return False, "Agendamento não possui serviços cadastrados."

        servico_ids = [r["servico_id"] for r in servicos_rows]

        # Validar formato da data
        try:
            datetime.strptime(nova_data, "%Y-%m-%d")
        except (ValueError, TypeError):
            return False, "Data inválida. Use o formato YYYY-MM-DD."

        # Validar profissional ativo
        prof = conn.execute(
            "SELECT id, ativo, estabelecimento_id FROM profissional WHERE id = %s",
            (ag["profissional_id"],),
        ).fetchone()
        if not prof or not prof["ativo"]:
            return False, "Profissional inativo ou não encontrado."

        p_estab_id = prof.get("estabelecimento_id") or 1
        if not data_permitida(nova_data, estabelecimento_id=p_estab_id):
            return False, "Data selecionada indisponível para agendamento."

        # Validar serviços ativos
        servicos_ativos = conn.execute(
            "SELECT id FROM servico WHERE id = ANY(%s) AND ativo = TRUE",
            (servico_ids,),
        ).fetchall()
        if len(servicos_ativos) != len(servico_ids):
            return False, "Um ou mais serviços deste agendamento estão inativos."

        # Validar compatibilidade
        vinculos = conn.execute(
            """
            SELECT servico_id FROM profissional_servico
            WHERE profissional_id = %s AND servico_id = ANY(%s)
            """,
            (ag["profissional_id"], servico_ids),
        ).fetchall()
        if {r["servico_id"] for r in vinculos} != set(servico_ids):
            return False, "Profissional incompatível com os serviços do agendamento."

        # Advisory lock na data e profissional para prevenir concorrência
        lock_key = (ag["profissional_id"] * 1000000) + int(nova_data.replace("-", ""))
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (lock_key,))

        # Buscar horários disponíveis ignorando o próprio agendamento
        disponiveis = _horarios_disponiveis_conn(
            conn,
            ag["profissional_id"],
            nova_data,
            servico_ids,
            ignorar_agendamento_id=agendamento_id,
        )

        if novo_horario not in disponiveis:
            return False, "Horário indisponível para o profissional na data selecionada."

        # Registrar no histórico de reagendamentos
        conn.execute(
            """
            INSERT INTO agendamento_reagendamento (
                agendamento_id, data_anterior, hora_anterior, data_nova, hora_nova
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (agendamento_id, ag["data"], ag["hora"], nova_data, novo_horario),
        )

        # Atualizar agendamento mantendo status 'agendado'
        conn.execute(
            """
            UPDATE agendamento
            SET data = %s, hora = %s
            WHERE id = %s
            """,
            (nova_data, novo_horario, agendamento_id),
        )

        return True, None


def obter_historico_reagendamentos(agendamento_id):
    """Retorna os registros de reagendamento de um agendamento."""
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT id, agendamento_id, data_anterior, hora_anterior, data_nova, hora_nova, motivo, criado_em
            FROM agendamento_reagendamento
            WHERE agendamento_id = %s
            ORDER BY criado_em ASC
            """,
            (agendamento_id,),
        ).fetchall()
        return [dict(r) for r in rows]



def verificar_admin(usuario, senha, estabelecimento_id=None):
    from werkzeug.security import check_password_hash

    if not usuario or not senha:
        return False

    with db_session() as conn:
        if estabelecimento_id:
            rows = conn.execute(
                """
                SELECT * FROM admin
                WHERE (LOWER(usuario) = LOWER(%s) OR (email IS NOT NULL AND LOWER(email) = LOWER(%s)))
                  AND estabelecimento_id = %s
                """,
                (usuario.strip(), usuario.strip(), estabelecimento_id),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM admin
                WHERE LOWER(usuario) = LOWER(%s)
                   OR (email IS NOT NULL AND LOWER(email) = LOWER(%s))
                ORDER BY id ASC
                """,
                (usuario.strip(), usuario.strip()),
            ).fetchall()

        for row in rows:
            if check_password_hash(row["senha_hash"], senha):
                return dict(row)
        return False


# ==============================================================================
# MÓDULO DE CLIENTES
# ==============================================================================

def _obter_ou_criar_cliente_conn(conn, nome, telefone, email=None, estabelecimento_id=None):
    """Localiza ou cria cliente na mesma transação."""
    nome = (nome or "").strip()
    telefone = (telefone or "").strip()
    email = (email or "").strip() or None
    if not nome or not telefone:
        return None

    estab_id = estabelecimento_id or 1
    if estab_id == 1:
        row = conn.execute(
            "SELECT id, nome, email FROM cliente WHERE TRIM(telefone) = %s AND (estabelecimento_id = 1 OR estabelecimento_id IS NULL)",
            (telefone,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id, nome, email FROM cliente WHERE TRIM(telefone) = %s AND estabelecimento_id = %s",
            (telefone, estab_id),
        ).fetchone()

    if row:
        if email and not row["email"]:
            conn.execute(
                "UPDATE cliente SET email = %s WHERE id = %s",
                (email, row["id"]),
            )
        return row["id"]

    cursor = conn.execute(
        """
        INSERT INTO cliente (nome, telefone, email, estabelecimento_id)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (nome, telefone, email, estab_id),
    )
    return cursor.fetchone()["id"]


def obter_ou_criar_cliente(nome, telefone, email=None, estabelecimento_id=None):
    """Retorna ID do cliente existente ou cria novo."""
    with db_session() as conn:
        return _obter_ou_criar_cliente_conn(conn, nome, telefone, email, estabelecimento_id=estabelecimento_id)


def listar_clientes(termo_busca=None, estabelecimento_id=None):
    """
    Retorna lista de clientes com métricas agregadas:
    - total de agendamentos
    - agendamentos realizados, cancelados e faltas
    - data do último agendamento
    """
    estab_id = estabelecimento_id or 1
    with db_session() as conn:
        query = """
            SELECT
                c.id,
                c.nome,
                c.telefone,
                c.email,
                c.observacoes,
                c.criado_em,
                COUNT(a.id) AS total_agendamentos,
                COUNT(a.id) FILTER (WHERE a.status = 'realizado') AS total_realizados,
                COUNT(a.id) FILTER (WHERE a.status = 'cancelado') AS total_cancelados,
                COUNT(a.id) FILTER (WHERE a.status = 'nao_compareceu') AS total_faltas,
                COUNT(a.id) FILTER (WHERE a.status = 'agendado') AS total_pendentes,
                MAX(a.data) AS ultimo_agendamento_data
            FROM cliente c
            LEFT JOIN agendamento a ON a.cliente_id = c.id
        """
        params = []
        where_clauses = []
        if estab_id == 1:
            where_clauses.append("(c.estabelecimento_id = 1 OR c.estabelecimento_id IS NULL)")
        else:
            where_clauses.append("c.estabelecimento_id = %s")
            params.append(estab_id)

        if termo_busca and termo_busca.strip():
            termo = termo_busca.strip()
            digitos = re.sub(r"\D", "", termo)
            if digitos:
                where_clauses.append("""
                    (c.nome ILIKE %s
                     OR c.telefone ILIKE %s
                     OR REGEXP_REPLACE(c.telefone, '\\D', '', 'g') LIKE %s)
                """)
                params.extend([f"%{termo}%", f"%{termo}%", f"%{digitos}%"])
            else:
                where_clauses.append("(c.nome ILIKE %s OR c.telefone ILIKE %s)")
                params.extend([f"%{termo}%", f"%{termo}%"])

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += """
            GROUP BY c.id, c.nome, c.telefone, c.email, c.observacoes, c.criado_em
            ORDER BY COALESCE(MAX(a.data), '1970-01-01') DESC, c.nome ASC
        """
        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(r) for r in rows]


def obter_cliente(cliente_id):
    """Retorna dados de um cliente pelo ID com estatísticas de atendimento."""
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT c.*,
                   COUNT(a.id) AS total_agendamentos,
                   COUNT(a.id) FILTER (WHERE a.status = 'realizado') AS total_realizados,
                   COUNT(a.id) FILTER (WHERE a.status = 'cancelado') AS total_cancelados,
                   COUNT(a.id) FILTER (WHERE a.status = 'nao_compareceu') AS total_faltas,
                   COUNT(a.id) FILTER (WHERE a.status = 'agendado') AS total_pendentes,
                   COALESCE(SUM(s.total_preco) FILTER (WHERE a.status IN ('agendado', 'realizado')), 0) AS valor_total_atendimentos
            FROM cliente c
            LEFT JOIN agendamento a ON a.cliente_id = c.id
            LEFT JOIN (
                SELECT agendamento_id, SUM(COALESCE(preco_unitario, 0)) AS total_preco
                FROM agendamento_servico
                GROUP BY agendamento_id
            ) s ON s.agendamento_id = a.id
            WHERE c.id = %s
            GROUP BY c.id
            """,
            (cliente_id,),
        ).fetchone()
        return dict(row) if row else None


def obter_historico_cliente(cliente_id):
    """Retorna o histórico cronológico de agendamentos de um cliente."""
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT
                a.id,
                a.data,
                a.hora,
                a.status,
                a.criado_em,
                COALESCE(a.profissional_nome_snapshot, p.nome) AS profissional_nome,
                COALESCE(string_agg(COALESCE(ags.nome_servico, s.nome), ', ' ORDER BY ags.servico_id), '') AS servico_nome,
                COALESCE(SUM(COALESCE(ags.preco_unitario, s.preco)), 0) AS servico_preco,
                COALESCE(SUM(COALESCE(ags.duracao_minutos, s.duracao_minutos)), 0) AS servico_duracao
            FROM agendamento a
            LEFT JOIN profissional p ON p.id = a.profissional_id
            LEFT JOIN agendamento_servico ags ON ags.agendamento_id = a.id
            LEFT JOIN servico s ON s.id = ags.servico_id
            WHERE a.cliente_id = %s
            GROUP BY a.id, a.data, a.hora, a.status, a.criado_em, a.profissional_nome_snapshot, p.nome
            ORDER BY a.data DESC, a.hora DESC
            """,
            (cliente_id,),
        ).fetchall()

        agora = datetime.now()
        resultados = []
        for r in rows:
            item = dict(r)
            try:
                dt_ag = datetime.strptime(f"{item['data']} {item['hora']}", "%Y-%m-%d %H:%M")
                item["ja_passou"] = dt_ag <= agora
            except Exception:
                item["ja_passou"] = False
            resultados.append(item)
        return resultados


def criar_cliente(nome, telefone, email=None, observacoes="", estabelecimento_id=None):
    """Cria um novo cliente no sistema com validações."""
    nome = (nome or "").strip()
    telefone = (telefone or "").strip()
    email = (email or "").strip() or None
    observacoes = (observacoes or "").strip()
    estab_id = estabelecimento_id or 1
    if not nome:
        return None, "Nome do cliente é obrigatório."
    if not telefone:
        return None, "Telefone do cliente é obrigatório."

    with db_session() as conn:
        if estab_id == 1:
            existente = conn.execute(
                "SELECT id FROM cliente WHERE TRIM(telefone) = %s AND (estabelecimento_id = 1 OR estabelecimento_id IS NULL)",
                (telefone,),
            ).fetchone()
        else:
            existente = conn.execute(
                "SELECT id FROM cliente WHERE TRIM(telefone) = %s AND estabelecimento_id = %s",
                (telefone, estab_id),
            ).fetchone()
        if existente:
            return None, "Já existe um cliente cadastrado com este telefone."

        cursor = conn.execute(
            """
            INSERT INTO cliente (nome, telefone, email, observacoes, estabelecimento_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (nome, telefone, email, observacoes, estab_id),
        )
        return cursor.fetchone()["id"], None


def atualizar_cliente(cliente_id, nome, telefone, email=None, observacoes="", estabelecimento_id=None):
    """Atualiza dados cadastrais e observações de um cliente."""
    nome = (nome or "").strip()
    telefone = (telefone or "").strip()
    email = (email or "").strip() or None
    observacoes = (observacoes or "").strip()
    if not nome:
        return False, "Nome do cliente é obrigatório."
    if not telefone:
        return False, "Telefone do cliente é obrigatório."

    with db_session() as conn:
        row_c = conn.execute("SELECT estabelecimento_id FROM cliente WHERE id = %s", (cliente_id,)).fetchone()
        estab_id = estabelecimento_id or (row_c.get("estabelecimento_id") if row_c else 1) or 1

        if estab_id == 1:
            duplicado = conn.execute(
                "SELECT id FROM cliente WHERE TRIM(telefone) = %s AND id != %s AND (estabelecimento_id = 1 OR estabelecimento_id IS NULL)",
                (telefone, cliente_id),
            ).fetchone()
        else:
            duplicado = conn.execute(
                "SELECT id FROM cliente WHERE TRIM(telefone) = %s AND id != %s AND estabelecimento_id = %s",
                (telefone, cliente_id, estab_id),
            ).fetchone()
        if duplicado:
            return False, "Outro cliente já utiliza este telefone."

        conn.execute(
            """
            UPDATE cliente
            SET nome = %s, telefone = %s, email = %s, observacoes = %s
            WHERE id = %s
            """,
            (nome, telefone, email, observacoes, cliente_id),
        )
        # Atualiza também o snapshot nos agendamentos futuros não concluídos para manter coerência
        conn.execute(
            """
            UPDATE agendamento
            SET cliente_nome = %s, cliente_telefone = %s
            WHERE cliente_id = %s AND status = 'agendado'
            """,
            (nome, telefone, cliente_id),
        )
        return True, None


# ==============================================================================
# ACESSO PÚBLICO À RESERVA (TOKEN DO CLIENTE)
# ==============================================================================

def obter_agendamento_por_token(token):
    """Retorna os dados completos do agendamento a partir do token de acesso público."""
    if not token or not str(token).strip():
        return None
    token = str(token).strip()

    with db_session() as conn:
        row = conn.execute(
            "SELECT id FROM agendamento WHERE token_acesso = %s",
            (token,),
        ).fetchone()
        if not row:
            return None
        return obter_agendamento_completo(row["id"])


def cancelar_agendamento_por_cliente(token):
    """
    Cancela o agendamento através do token público de acesso do cliente.
    Apenas agendamentos com status 'agendado' podem ser cancelados.
    """
    if not token or not str(token).strip():
        return False, "Token de acesso inválido."
    token = str(token).strip()

    ag = obter_agendamento_por_token(token)
    if not ag:
        return False, "Agendamento não encontrado."

    if ag["status"] != "agendado":
        if ag["status"] == "cancelado":
            return False, "Este agendamento já foi cancelado anteriormente."
        return False, "Este agendamento não pode mais ser cancelado."

    return cancelar_agendamento(ag["id"], usuario="cliente")


def confirmar_presenca_por_cliente(token):
    """
    Confirma a presença do cliente no agendamento através do token público com 1 clique.
    """
    if not token or not str(token).strip():
        return False, "Token de acesso inválido."
    token = str(token).strip()

    with db_session() as conn:
        row = conn.execute(
            "SELECT id, status, confirmado_pelo_cliente FROM agendamento WHERE token_acesso = %s",
            (token,),
        ).fetchone()
        if not row:
            return False, "Agendamento não encontrado."
        if row["status"] != "agendado":
            return False, f"Não é possível confirmar presença para agendamento com status '{row['status']}'."
        if row["confirmado_pelo_cliente"]:
            return True, "Sua presença já foi confirmada anteriormente."

        conn.execute(
            """
            UPDATE agendamento
            SET confirmado_pelo_cliente = TRUE,
                confirmado_em = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (row["id"],),
        )
        return True, "Presença confirmada com sucesso!"


def buscar_agendamentos_para_lembretes(estabelecimento_id=None):
    """
    Localiza agendamentos futuros elegíveis para lembrete de 24h ou 2h via WhatsApp.
    Retorna dicionário com listas de ids para cada tipo de lembrete.
    """
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        tz_br = ZoneInfo("America/Sao_Paulo")
    except Exception:
        tz_br = None

    agora = datetime.now(tz_br) if tz_br else datetime.now()

    with db_session() as conn:
        filtro_estab = "AND estabelecimento_id = %s" if estabelecimento_id else ""
        params = [agora.strftime("%Y-%m-%d")]
        if estabelecimento_id:
            params.append(estabelecimento_id)

        rows = conn.execute(
            f"""
            SELECT id, data, hora, lembrete_24h_enviado_em, lembrete_2h_enviado_em, cliente_telefone, estabelecimento_id
            FROM agendamento
            WHERE status = 'agendado'
              AND data >= %s
              AND cliente_telefone IS NOT NULL
              AND cliente_telefone <> ''
              AND (lembrete_24h_enviado_em IS NULL OR lembrete_2h_enviado_em IS NULL)
              {filtro_estab}
            ORDER BY data ASC, hora ASC
            """,
            params,
        ).fetchall()

    elegiveis_24h = []
    elegiveis_2h = []

    for r in rows:
        data_str = r["data"]
        hora_str = r["hora"]
        try:
            dt_agenda = datetime.strptime(f"{data_str} {hora_str}", "%Y-%m-%d %H:%M")
            if tz_br:
                dt_agenda = dt_agenda.replace(tzinfo=tz_br)
            delta_horas = (dt_agenda - agora).total_seconds() / 3600.0

            # Lembrete 24h: entre 20h e 28h de antecedência
            if 20.0 <= delta_horas <= 28.0 and not r["lembrete_24h_enviado_em"]:
                elegiveis_24h.append(r["id"])

            # Lembrete 2h: entre 0.5h (30min) e 3.0h de antecedência
            if 0.5 <= delta_horas <= 3.0 and not r["lembrete_2h_enviado_em"]:
                elegiveis_2h.append(r["id"])
        except Exception:
            continue

    return {
        "lembretes_24h": elegiveis_24h,
        "lembretes_2h": elegiveis_2h,
    }


def marcar_lembrete_enviado(agendamento_id, tipo="24h"):
    """Registra timestamp do disparo de lembrete 24h ou 2h."""
    col = "lembrete_24h_enviado_em" if tipo == "24h" else "lembrete_2h_enviado_em"
    with db_session() as conn:
        conn.execute(
            f"UPDATE agendamento SET {col} = CURRENT_TIMESTAMP WHERE id = %s",
            (agendamento_id,),
        )


# ==============================================================================
# AGILLEX PAY — GESTÃO DE PAGAMENTOS E TRANSAÇÕES
# ==============================================================================

def atualizar_pagamento_agendamento(
    agendamento_id,
    status,
    asaas_payment_id=None,
    pix_copia_cola=None,
    pix_qr_code=None,
    valor=None,
    taxa=1.99,
    valor_liquido=None,
):
    """Atualiza o status e dados de liquidação financeira de um agendamento."""
    with db_session() as conn:
        updates = ["pagamento_status = %s"]
        params = [status]
        if asaas_payment_id:
            updates.append("asaas_payment_id = %s")
            params.append(asaas_payment_id)
        if pix_copia_cola:
            updates.append("pix_copia_cola = %s")
            params.append(pix_copia_cola)
        if pix_qr_code:
            updates.append("pix_qr_code = %s")
            params.append(pix_qr_code)
        if valor is not None:
            updates.append("pagamento_valor = %s")
            params.append(valor)
        if taxa is not None:
            updates.append("pagamento_taxa_alllogic = %s")
            params.append(taxa)
        if valor_liquido is not None:
            updates.append("pagamento_valor_liquido = %s")
            params.append(valor_liquido)
        if status == "pago":
            updates.append("pago_em = CURRENT_TIMESTAMP")

        params.append(agendamento_id)
        conn.execute(
            f"UPDATE agendamento SET {', '.join(updates)} WHERE id = %s",
            params,
        )


def obter_agendamento_por_asaas_id(asaas_payment_id):
    """Busca um agendamento pelo identificador da cobrança no Asaas."""
    if not asaas_payment_id:
        return None
    with db_session() as conn:
        row = conn.execute(
            "SELECT * FROM agendamento WHERE asaas_payment_id = %s",
            (asaas_payment_id.strip(),),
        ).fetchone()
        return dict(row) if row else None


# ==============================================================================
# CONTROLE DE PACOTES DE SERVIÇOS
# ==============================================================================

def listar_pacotes(estabelecimento_id=1, apenas_ativos=False):
    """Lista todos os pacotes cadastrados para o estabelecimento."""
    with db_session() as conn:
        filtro_ativo = "AND p.ativo = TRUE" if apenas_ativos else ""
        query = f"""
            SELECT p.*, s.nome AS servico_nome, s.preco AS servico_preco_unitario
            FROM pacote p
            LEFT JOIN servico s ON s.id = p.servico_id
            WHERE (p.estabelecimento_id = %s OR p.estabelecimento_id IS NULL)
            {filtro_ativo}
            ORDER BY p.ativo DESC, p.nome ASC
        """
        rows = conn.execute(query, (estabelecimento_id,)).fetchall()
        return [dict(r) for r in rows]


def criar_pacote(estabelecimento_id, nome, descricao, servico_id, quantidade_sessoes, preco, validade_dias=60, ativo=True):
    """Cria um novo pacote de serviços."""
    with db_session() as conn:
        row = conn.execute(
            """
            INSERT INTO pacote (
                estabelecimento_id, nome, descricao, servico_id, quantidade_sessoes, preco, validade_dias, ativo
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (estabelecimento_id, nome.strip(), descricao.strip(), servico_id, int(quantidade_sessoes), float(preco), int(validade_dias), bool(ativo)),
        ).fetchone()
        return row["id"]


def obter_pacote(pacote_id):
    """Retorna dados de um pacote específico."""
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT p.*, s.nome AS servico_nome
            FROM pacote p
            LEFT JOIN servico s ON s.id = p.servico_id
            WHERE p.id = %s
            """,
            (pacote_id,),
        ).fetchone()
        return dict(row) if row else None


def editar_pacote(pacote_id, nome, descricao, servico_id, quantidade_sessoes, preco, validade_dias, ativo=True):
    """Atualiza os dados de um pacote de serviços."""
    with db_session() as conn:
        conn.execute(
            """
            UPDATE pacote
            SET nome = %s,
                descricao = %s,
                servico_id = %s,
                quantidade_sessoes = %s,
                preco = %s,
                validade_dias = %s,
                ativo = %s
            WHERE id = %s
            """,
            (nome.strip(), descricao.strip(), servico_id, int(quantidade_sessoes), float(preco), int(validade_dias), bool(ativo), pacote_id),
        )
        return True


def alternar_status_pacote(pacote_id, estabelecimento_id=None):
    """Ativa ou desativa um pacote."""
    with db_session() as conn:
        filtros = ["id = %s"]
        params = [pacote_id]
        if estabelecimento_id:
            filtros.append("(estabelecimento_id = %s OR estabelecimento_id IS NULL)")
            params.append(estabelecimento_id)
        where_clause = " AND ".join(filtros)
        row = conn.execute(f"SELECT ativo FROM pacote WHERE {where_clause}", params).fetchone()
        if not row:
            return False
        novo_status = not row["ativo"]
        conn.execute("UPDATE pacote SET ativo = %s WHERE id = %s", (novo_status, pacote_id))
        return novo_status


def vender_pacote_para_cliente(estabelecimento_id, cliente_id, pacote_id, valor_pago=None, pago=True, observacoes=""):
    """Registra a aquisição de um pacote por um cliente."""
    from datetime import date, timedelta
    pacote = obter_pacote(pacote_id)
    if not pacote:
        return False, "Pacote não encontrado."

    validade_dias = pacote.get("validade_dias") or 60
    data_exp = date.today() + timedelta(days=validade_dias)
    preco = float(valor_pago if valor_pago is not None else pacote["preco"])

    with db_session() as conn:
        row = conn.execute(
            """
            INSERT INTO cliente_pacote (
                estabelecimento_id, cliente_id, pacote_id, quantidade_total, quantidade_utilizada,
                status, valor_pago, pago, data_expiracao, observacoes
            ) VALUES (%s, %s, %s, %s, 0, 'ativo', %s, %s, %s, %s)
            RETURNING id
            """,
            (estabelecimento_id, cliente_id, pacote_id, pacote["quantidade_sessoes"], preco, bool(pago), data_exp, observacoes.strip()),
        ).fetchone()
        return True, row["id"]


def listar_pacotes_do_cliente(cliente_id, estabelecimento_id=None):
    """Lista todos os pacotes adquiridos por um cliente com saldo e validade."""
    with db_session() as conn:
        filtros = ["cp.cliente_id = %s"]
        params = [cliente_id]
        if estabelecimento_id:
            filtros.append("(cp.estabelecimento_id = %s OR cp.estabelecimento_id IS NULL)")
            params.append(estabelecimento_id)
        where_clause = " AND ".join(filtros)
        rows = conn.execute(
            f"""
            SELECT cp.*, p.nome AS pacote_nome, s.nome AS servico_nome,
                   (cp.quantidade_total - cp.quantidade_utilizada) AS sessoes_restantes
            FROM cliente_pacote cp
            JOIN pacote p ON p.id = cp.pacote_id
            LEFT JOIN servico s ON s.id = p.servico_id
            WHERE {where_clause}
            ORDER BY cp.status ASC, cp.data_compra DESC
            """,
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def listar_todos_pacotes_clientes(estabelecimento_id=1, status=None):
    """Lista todos os pacotes de clientes para a visão geral administrativa."""
    with db_session() as conn:
        filtro_status = "AND cp.status = %s" if status else ""
        params = [estabelecimento_id]
        if status:
            params.append(status)

        query = f"""
            SELECT cp.*, c.nome AS cliente_nome, c.telefone AS cliente_telefone,
                   p.nome AS pacote_nome, s.nome AS servico_nome,
                   (cp.quantidade_total - cp.quantidade_utilizada) AS sessoes_restantes
            FROM cliente_pacote cp
            JOIN cliente c ON c.id = cp.cliente_id
            JOIN pacote p ON p.id = cp.pacote_id
            LEFT JOIN servico s ON s.id = p.servico_id
            WHERE (cp.estabelecimento_id = %s OR cp.estabelecimento_id IS NULL)
            {filtro_status}
            ORDER BY cp.data_compra DESC
        """
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def abater_sessao_pacote_cliente(cliente_pacote_id, agendamento_id=None, observacao=""):
    """Consome 1 sessão do saldo de um pacote ativo do cliente."""
    with db_session() as conn:
        row = conn.execute(
            "SELECT id, quantidade_total, quantidade_utilizada, status FROM cliente_pacote WHERE id = %s",
            (cliente_pacote_id,),
        ).fetchone()
        if not row:
            return False, "Pacote do cliente não encontrado."

        if row["status"] != "ativo":
            return False, f"Pacote não está ativo (status: {row['status']})."

        nova_utilizada = row["quantidade_utilizada"] + 1
        if nova_utilizada > row["quantidade_total"]:
            return False, "Todas as sessões deste pacote já foram utilizadas."

        novo_status = "esgotado" if nova_utilizada >= row["quantidade_total"] else "ativo"

        conn.execute(
            "UPDATE cliente_pacote SET quantidade_utilizada = %s, status = %s WHERE id = %s",
            (nova_utilizada, novo_status, cliente_pacote_id),
        )

        obs = observacao.strip() or f"Sessão {nova_utilizada} de {row['quantidade_total']} utilizada"
        conn.execute(
            """
            INSERT INTO cliente_pacote_uso (cliente_pacote_id, agendamento_id, observacao)
            VALUES (%s, %s, %s)
            """,
            (cliente_pacote_id, agendamento_id, obs),
        )

        restantes = row["quantidade_total"] - nova_utilizada
        return True, f"Sessão abatida com sucesso! Restam {restantes} sessões."


# ==============================================================================
# CONTROLE DE FIADOS (CONTAS A RECEBER)
# ==============================================================================

def criar_lancamento_fiado(estabelecimento_id, cliente_id, valor, descricao, data_vencimento=None, agendamento_id=None):
    """Cria um débito pendente para um cliente."""
    from datetime import date
    with db_session() as conn:
        row = conn.execute(
            """
            INSERT INTO fiado_lancamento (
                estabelecimento_id, cliente_id, agendamento_id, descricao, valor, valor_pago,
                status, data_lancamento, data_vencimento
            ) VALUES (%s, %s, %s, %s, %s, 0.00, 'pendente', CURRENT_DATE, %s)
            RETURNING id
            """,
            (estabelecimento_id, cliente_id, agendamento_id, descricao.strip(), float(valor), data_vencimento or None),
        ).fetchone()
        return row["id"]


def listar_fiados(estabelecimento_id=1, status=None, cliente_id=None):
    """Lista todos os lançamentos de fiado com detalhes do cliente."""
    with db_session() as conn:
        filtros = ["(f.estabelecimento_id = %s OR f.estabelecimento_id IS NULL)"]
        params = [estabelecimento_id]

        if status:
            filtros.append("f.status = %s")
            params.append(status)
        if cliente_id:
            filtros.append("f.cliente_id = %s")
            params.append(cliente_id)

        where_clause = " AND ".join(filtros)
        query = f"""
            SELECT f.*, c.nome AS cliente_nome, c.telefone AS cliente_telefone,
                   (f.valor - f.valor_pago) AS saldo_devedor
            FROM fiado_lancamento f
            JOIN cliente c ON c.id = f.cliente_id
            WHERE {where_clause}
            ORDER BY f.status ASC, f.data_lancamento DESC
        """
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def obter_fiado(fiado_id):
    """Retorna detalhes de um lançamento de fiado."""
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT f.*, c.nome AS cliente_nome, c.telefone AS cliente_telefone,
                   (f.valor - f.valor_pago) AS saldo_devedor
            FROM fiado_lancamento f
            JOIN cliente c ON c.id = f.cliente_id
            WHERE f.id = %s
            """,
            (fiado_id,),
        ).fetchone()
        if not row:
            return None
        fiado = dict(row)

        pagamentos = conn.execute(
            "SELECT * FROM fiado_pagamento WHERE fiado_id = %s ORDER BY data_pagamento DESC",
            (fiado_id,),
        ).fetchall()
        fiado["pagamentos"] = [dict(p) for p in pagamentos]
        return fiado


def registrar_pagamento_fiado(fiado_id, valor_pago, forma_pagamento="pix", observacao=""):
    """Registra pagamento total ou parcial de um fiado pendente."""
    with db_session() as conn:
        row = conn.execute(
            "SELECT id, valor, valor_pago, status FROM fiado_lancamento WHERE id = %s",
            (fiado_id,),
        ).fetchone()
        if not row:
            return False, "Lançamento de fiado não encontrado."

        val_pagamento = float(valor_pago)
        if val_pagamento <= 0:
            return False, "Valor de pagamento deve ser maior que zero."

        novo_valor_pago = float(row["valor_pago"]) + val_pagamento
        total_devido = float(row["valor"])

        novo_status = "liquidado" if novo_valor_pago >= (total_devido - 0.01) else "pago_parcial"

        conn.execute(
            "UPDATE fiado_lancamento SET valor_pago = %s, status = %s WHERE id = %s",
            (novo_valor_pago, novo_status, fiado_id),
        )

        conn.execute(
            """
            INSERT INTO fiado_pagamento (fiado_id, valor_pago, forma_pagamento, observacao)
            VALUES (%s, %s, %s, %s)
            """,
            (fiado_id, val_pagamento, forma_pagamento.strip().lower(), observacao.strip()),
        )

        restante = max(0.0, total_devido - novo_valor_pago)
        msg = "Fiado totalmente quitado!" if novo_status == "liquidado" else f"Pagamento registrado! Saldo restante: R$ {restante:.2f}".replace(".", ",")
        return True, msg


def obter_resumo_fiados(estabelecimento_id=1):
    """Retorna totais consolidados de fiados para cards do dashboard."""
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT 
                COALESCE(SUM(valor - valor_pago) FILTER (WHERE status <> 'liquidado'), 0.0) AS total_a_receber,
                COALESCE(SUM(valor_pago), 0.0) AS total_recebido,
                COUNT(DISTINCT cliente_id) FILTER (WHERE status <> 'liquidado') AS clientes_com_pendencia,
                COUNT(*) FILTER (WHERE status <> 'liquidado') AS total_lancamentos_pendentes
            FROM fiado_lancamento
            WHERE (estabelecimento_id = %s OR estabelecimento_id IS NULL)
            """,
            (estabelecimento_id,),
        ).fetchone()
        return dict(row) if row else {
            "total_a_receber": 0.0,
            "total_recebido": 0.0,
            "clientes_com_pendencia": 0,
            "total_lancamentos_pendentes": 0,
        }


def obter_saldo_devedor_cliente(cliente_id, estabelecimento_id=None):
    """Retorna o valor total devedor atual de um cliente específico."""
    with db_session() as conn:
        filtros = ["cliente_id = %s", "status <> 'liquidado'"]
        params = [cliente_id]
        if estabelecimento_id:
            filtros.append("(estabelecimento_id = %s OR estabelecimento_id IS NULL)")
            params.append(estabelecimento_id)
        where_clause = " AND ".join(filtros)
        row = conn.execute(
            f"""
            SELECT COALESCE(SUM(valor - valor_pago), 0.0) AS saldo_devedor
            FROM fiado_lancamento
            WHERE {where_clause}
            """,
            params,
        ).fetchone()
        return float(row["saldo_devedor"]) if row else 0.0


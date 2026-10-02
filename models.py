from datetime import datetime, timedelta
from functools import lru_cache

from database import db_session, obter_todas_configuracoes


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


def listar_servicos_admin():
    with db_session() as conn:
        rows = conn.execute(
            "SELECT * FROM servico ORDER BY ativo DESC, nome ASC"
        ).fetchall()
        return [dict(row) for row in rows]


def criar_servico(nome, preco, duracao_minutos, ativo=True, descricao=""):
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

    with db_session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO servico (nome, descricao, preco, duracao_minutos, ativo)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (nome, descricao, preco_valor, duracao, bool(ativo)),
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


def listar_profissionais_admin():
    with db_session() as conn:
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


def criar_profissional(nome, ativo=True, servico_ids=None):
    nome = (nome or "").strip()
    if not nome:
        return None, "Nome do profissional é obrigatório."

    servico_ids = list(dict.fromkeys(servico_ids or []))
    if bool(ativo) and not servico_ids:
        return None, "Selecione pelo menos um serviço para o profissional ativo."

    with db_session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO profissional (nome, ativo)
            VALUES (%s, %s)
            RETURNING id
            """,
            (nome, bool(ativo)),
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


def listar_servicos(apenas_ativos=True):
    with db_session() as conn:
        if apenas_ativos:
            rows = conn.execute("SELECT * FROM servico WHERE ativo = TRUE ORDER BY id").fetchall()
        else:
            rows = conn.execute("SELECT * FROM servico ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def obter_servico(servico_id):
    with db_session() as conn:
        row = conn.execute("SELECT * FROM servico WHERE id = %s", (servico_id,)).fetchone()
        return dict(row) if row else None


def listar_profissionais(apenas_ativos=True):
    with db_session() as conn:
        if apenas_ativos:
            rows = conn.execute("SELECT * FROM profissional WHERE ativo = TRUE ORDER BY nome").fetchall()
        else:
            rows = conn.execute("SELECT * FROM profissional ORDER BY nome").fetchall()
        return [dict(r) for r in rows]


def listar_profissionais_para_servicos(servico_ids):
    servico_ids = list(dict.fromkeys(servico_ids or []))
    if not servico_ids:
        return listar_profissionais(apenas_ativos=True)

    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.nome, p.ativo
            FROM profissional AS p
            JOIN profissional_servico AS ps ON ps.profissional_id = p.id
            JOIN servico AS s ON s.id = ps.servico_id
            WHERE p.ativo = TRUE
              AND s.ativo = TRUE
              AND s.id = ANY(%s)
            GROUP BY p.id, p.nome, p.ativo
            HAVING COUNT(DISTINCT s.id) = %s
            ORDER BY p.nome ASC
            """,
            (servico_ids, len(servico_ids)),
        ).fetchall()
        return [dict(row) for row in rows]


def obter_profissional(profissional_id):
    with db_session() as conn:
        row = conn.execute("SELECT * FROM profissional WHERE id = %s", (profissional_id,)).fetchone()
        return dict(row) if row else None


def _gerar_slots_do_dia():
    try:
        slots = []
        inicio = datetime.strptime(horario_abertura(), "%H:%M")
        fim = datetime.strptime(horario_fechamento(), "%H:%M")
        intervalo = intervalo_slot_minutos()
        if intervalo <= 0 or inicio >= fim:
            return slots
        atual = inicio
        while atual < fim:
            slots.append(atual.strftime("%H:%M"))
            atual += timedelta(minutes=intervalo)
        return slots
    except (TypeError, ValueError):
        return []


def data_permitida(data_str):
    """Valida se a data está dentro do funcionamento (dia da semana permitido, não é passado e respeita antecedência máxima)."""
    try:
        data = datetime.strptime(data_str, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return False
    hoje = datetime.now().date()
    if data < hoje:
        return False
    if (data.weekday() + 1) % 7 not in dias_funcionamento():
        return False
    # Valida antecedência máxima configurada no banco
    max_dias = dias_antecedencia_agendamento()
    if max_dias is not None and (data - hoje).days > max_dias:
        return False
    return True


def _horarios_disponiveis_conn(conn, profissional_id, data_str, servico_ids):
    profissional = conn.execute(
        "SELECT ativo FROM profissional WHERE id = %s",
        (profissional_id,),
    ).fetchone()
    if not profissional or not profissional["ativo"]:
        return []

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
    fechamento = datetime.strptime(horario_fechamento(), "%H:%M")
    data = datetime.strptime(data_str, "%Y-%m-%d").date()
    fechamento = datetime.combine(data, fechamento.time())
    ocupados = conn.execute(
        """
        SELECT a.hora,
               COALESCE(SUM(COALESCE(ags.duracao_minutos, s.duracao_minutos)), 0)
                   AS duracao_minutos
        FROM agendamento AS a
        JOIN agendamento_servico AS ags ON ags.agendamento_id = a.id
        JOIN servico AS s ON s.id = ags.servico_id
        WHERE a.profissional_id = %s
          AND a.data = %s
          AND a.status = 'agendado'
        GROUP BY a.id, a.hora
        """,
        (profissional_id, data_str),
    ).fetchall()

    agora = datetime.now()
    disponiveis = []
    for slot in _gerar_slots_do_dia():
        inicio = datetime.combine(data, datetime.strptime(slot, "%H:%M").time())
        fim = inicio + timedelta(minutes=duracao_total)
        if fim > fechamento or (data == agora.date() and inicio <= agora):
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


def horarios_disponiveis(profissional_id, data_str, servico_ids):
    """Retorna horários livres considerando os serviços e estados atuais."""
    if not data_permitida(data_str):
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
        )


def criar_agendamento(cliente_nome, cliente_telefone, servico_ids, profissional_id, data_str, hora_str):
    """Cria o agendamento e seus serviços, revalidando a disponibilidade com lock de concorrência."""
    if isinstance(servico_ids, int):
        servico_ids = [servico_ids]
    servico_ids = list(dict.fromkeys(servico_ids or []))
    if not servico_ids or any(type(item) is not int or item <= 0 for item in servico_ids):
        return None, "Selecione pelo menos um serviço."
    if type(profissional_id) is not int or profissional_id <= 0:
        return None, "Profissional inválido."
    if not data_permitida(data_str):
        return None, "Data indisponível para agendamento."

    with db_session() as conn:
        lock_key = (profissional_id * 1000000) + int(data_str.replace("-", ""))
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (lock_key,))
        if not data_permitida(data_str):
            return None, "Data indisponível para agendamento."

        disponiveis = _horarios_disponiveis_conn(
            conn,
            profissional_id,
            data_str,
            servico_ids,
        )
        if hora_str not in disponiveis:
            return None, "Horário não disponível. Escolha outro horário."

        profissional = conn.execute(
            "SELECT nome FROM profissional WHERE id = %s AND ativo = TRUE",
            (profissional_id,),
        ).fetchone()
        servicos = conn.execute(
            """
            SELECT id, nome, preco, duracao_minutos
            FROM servico
            WHERE id = ANY(%s) AND ativo = TRUE
            ORDER BY id
            """,
            (servico_ids,),
        ).fetchall()
        if not profissional or len(servicos) != len(servico_ids):
            return None, "Serviço inválido."

        primeiro_servico_id = servico_ids[0]

        cursor = conn.execute(
            """
            INSERT INTO agendamento (
                cliente_nome,
                cliente_telefone,
                servico_id,
                profissional_id,
                data,
                hora,
                profissional_nome_snapshot
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                cliente_nome,
                cliente_telefone,
                primeiro_servico_id,
                profissional_id,
                data_str,
                hora_str,
                profissional["nome"],
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
                               'id', s.id,
                               'nome', COALESCE(ags.nome_servico, s.nome),
                               'preco', COALESCE(ags.preco_unitario, s.preco),
                               'duracao_minutos', COALESCE(ags.duracao_minutos, s.duracao_minutos)
                           )
                           ORDER BY s.id
                       ) FILTER (WHERE s.id IS NOT NULL),
                       '[]'::json
                   ) AS servicos
            FROM agendamento a
            JOIN profissional p ON p.id = a.profissional_id
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


def listar_agendamentos_por_periodo(data_inicio_str, data_fim_str):
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT a.*,
                   COALESCE(a.profissional_nome_snapshot, p.nome) AS profissional_nome,
                   COALESCE(
                       json_agg(
                           json_build_object(
                               'id', s.id,
                               'nome', COALESCE(ags.nome_servico, s.nome),
                               'preco', COALESCE(ags.preco_unitario, s.preco),
                               'duracao_minutos', COALESCE(ags.duracao_minutos, s.duracao_minutos)
                           )
                           ORDER BY s.id
                       ) FILTER (WHERE s.id IS NOT NULL),
                       '[]'::json
                   ) AS servicos
            FROM agendamento a
            JOIN profissional p ON p.id = a.profissional_id
            LEFT JOIN agendamento_servico ags ON ags.agendamento_id = a.id
            LEFT JOIN servico s ON s.id = ags.servico_id
            WHERE a.data BETWEEN %s AND %s
            GROUP BY a.id, p.nome
            ORDER BY a.data ASC, a.hora ASC
            """,
            (data_inicio_str, data_fim_str),
        ).fetchall()

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
            resultados.append(resultado)

        return resultados


def cancelar_agendamento(agendamento_id):
    """Cancela um agendamento preservando seu registro histórico."""
    with db_session() as conn:
        cursor = conn.execute(
            """
            UPDATE agendamento
            SET status = 'cancelado'
            WHERE id = %s AND status = 'agendado'
            RETURNING id
            """,
            (agendamento_id,),
        )
        row = cursor.fetchone()
        return row is not None



def verificar_admin(usuario, senha):
    from werkzeug.security import check_password_hash

    with db_session() as conn:
        row = conn.execute("SELECT * FROM admin WHERE usuario = %s", (usuario,)).fetchone()
        if not row:
            return False
        return check_password_hash(row["senha_hash"], senha)

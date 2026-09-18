from datetime import datetime, timedelta

from config import (
    HORARIO_ABERTURA,
    HORARIO_FECHAMENTO,
    INTERVALO_SLOT_MINUTOS,
    DIAS_FUNCIONAMENTO,
)
from database import db_session


def listar_servicos():
    with db_session() as conn:
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


def obter_profissional(profissional_id):
    with db_session() as conn:
        row = conn.execute("SELECT * FROM profissional WHERE id = %s", (profissional_id,)).fetchone()
        return dict(row) if row else None


def _gerar_slots_do_dia():
    slots = []
    inicio = datetime.strptime(HORARIO_ABERTURA, "%H:%M")
    fim = datetime.strptime(HORARIO_FECHAMENTO, "%H:%M")
    atual = inicio
    while atual < fim:
        slots.append(atual.strftime("%H:%M"))
        atual += timedelta(minutes=INTERVALO_SLOT_MINUTOS)
    return slots


def data_permitida(data_str):
    """Valida se a data está dentro do funcionamento (dia da semana permitido e não é passado)."""
    data = datetime.strptime(data_str, "%Y-%m-%d").date()
    hoje = datetime.now().date()
    if data < hoje:
        return False
    if data.weekday() not in DIAS_FUNCIONAMENTO:
        return False
    return True


def horarios_disponiveis(profissional_id, data_str, servico_ids):
    """Retorna horários livres considerando a duração total dos serviços selecionados."""
    if not data_permitida(data_str):
        return []

    if isinstance(servico_ids, int):
        servico_ids = [servico_ids]

    servico_ids = list(servico_ids)
    if not servico_ids:
        return []

    with db_session() as conn:
        servicos = conn.execute(
            """
            SELECT id, duracao_minutos
            FROM servico
            WHERE id = ANY(%s)
            """,
            (servico_ids,),
        ).fetchall()

        if len(servicos) != len(set(servico_ids)):
            return []

        duracao_total = sum(servico["duracao_minutos"] for servico in servicos)

        ocupados_rows = conn.execute(
            """
            SELECT a.hora,
                   COALESCE(SUM(s.duracao_minutos), 0) AS duracao_minutos
            FROM agendamento a
            JOIN agendamento_servico ags ON ags.agendamento_id = a.id
            JOIN servico s ON s.id = ags.servico_id
            WHERE a.profissional_id = %s
              AND a.data = %s
              AND a.status = 'agendado'
            GROUP BY a.id, a.hora
            """,
            (profissional_id, data_str),
        ).fetchall()

    todos_slots = _gerar_slots_do_dia()
    slots_necessarios = max(
        1,
        -(-duracao_total // INTERVALO_SLOT_MINUTOS),
    )

    ocupados = set()
    for row in ocupados_rows:
        inicio_idx = todos_slots.index(row["hora"]) if row["hora"] in todos_slots else None
        if inicio_idx is None:
            continue

        qtd = max(
            1,
            -(-row["duracao_minutos"] // INTERVALO_SLOT_MINUTOS),
        )

        for i in range(inicio_idx, inicio_idx + qtd):
            if i < len(todos_slots):
                ocupados.add(todos_slots[i])

    agora = datetime.now()
    data_e_hoje = datetime.strptime(data_str, "%Y-%m-%d").date() == agora.date()

    disponiveis = []

    for i, slot in enumerate(todos_slots):
        se_de_hoje_no_passado = (
            data_e_hoje
            and datetime.strptime(slot, "%H:%M").time() <= agora.time()
        )
        if se_de_hoje_no_passado:
            continue

        faixa = todos_slots[i:i + slots_necessarios]

        if len(faixa) < slots_necessarios:
            continue

        if any(s in ocupados for s in faixa):
            continue

        disponiveis.append(slot)

    return disponiveis


def criar_agendamento(cliente_nome, cliente_telefone, servico_ids, profissional_id, data_str, hora_str):
    """Cria o agendamento e seus serviços, revalidando a disponibilidade."""
    if isinstance(servico_ids, int):
        servico_ids = [servico_ids]

    servico_ids = list(servico_ids)
    if not servico_ids:
        return None, "Selecione pelo menos um serviço."

    disponiveis = horarios_disponiveis(
        profissional_id,
        data_str,
        servico_ids,
    )
    if hora_str not in disponiveis:
        return None, "Horário não disponível. Escolha outro horário."

    with db_session() as conn:
        servicos = conn.execute(
            """
            SELECT id
            FROM servico
            WHERE id = ANY(%s)
            """,
            (servico_ids,),
        ).fetchall()

        if len(servicos) != len(set(servico_ids)):
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
                hora
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                cliente_nome,
                cliente_telefone,
                primeiro_servico_id,
                profissional_id,
                data_str,
                hora_str,
            ),
        )
        agendamento_id = cursor.fetchone()["id"]

        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO agendamento_servico (agendamento_id, servico_id)
                VALUES (%s, %s)
                ON CONFLICT (agendamento_id, servico_id) DO NOTHING
                """,
                [(agendamento_id, servico_id) for servico_id in servico_ids],
            )

    return agendamento_id, None


def obter_agendamento_completo(agendamento_id):
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT a.*,
                   p.nome AS profissional_nome,
                   COALESCE(
                       json_agg(
                           json_build_object(
                               'id', s.id,
                               'nome', s.nome,
                               'preco', s.preco,
                               'duracao_minutos', s.duracao_minutos
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
                   p.nome AS profissional_nome,
                   COALESCE(
                       json_agg(
                           json_build_object(
                               'id', s.id,
                               'nome', s.nome,
                               'preco', s.preco,
                               'duracao_minutos', s.duracao_minutos
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

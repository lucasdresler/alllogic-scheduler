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


def horarios_disponiveis(profissional_id, data_str, servico_id):
    """Retorna lista de horários (HH:MM) livres para o profissional na data, considerando a duração do serviço."""
    if not data_permitida(data_str):
        return []

    servico = obter_servico(servico_id)
    if not servico:
        return []

    duracao = servico["duracao_minutos"]
    slots_necessarios = max(1, -(-duracao // INTERVALO_SLOT_MINUTOS))  # ceil division

    todos_slots = _gerar_slots_do_dia()

    with db_session() as conn:
        ocupados_rows = conn.execute(
            """
            SELECT a.hora, s.duracao_minutos
            FROM agendamento a
            JOIN servico s ON s.id = a.servico_id
            WHERE a.profissional_id = %s AND a.data = %s
            """,
            (profissional_id, data_str),
        ).fetchall()

    ocupados = set()
    for row in ocupados_rows:
        inicio_idx = todos_slots.index(row["hora"]) if row["hora"] in todos_slots else None
        if inicio_idx is None:
            continue
        qtd = max(1, -(-row["duracao_minutos"] // INTERVALO_SLOT_MINUTOS))
        for i in range(inicio_idx, inicio_idx + qtd):
            if i < len(todos_slots):
                ocupados.add(todos_slots[i])

    agora = datetime.now()
    data_e_hoje = datetime.strptime(data_str, "%Y-%m-%d").date() == agora.date()

    disponiveis = []
    for i, slot in enumerate(todos_slots):
        se_de_hoje_no_passado = data_e_hoje and datetime.strptime(slot, "%H:%M").time() <= agora.time()
        if se_de_hoje_no_passado:
            continue

        faixa = todos_slots[i:i + slots_necessarios]
        if len(faixa) < slots_necessarios:
            continue  # não cabe o serviço até o fechamento
        if any(s in ocupados for s in faixa):
            continue

        disponiveis.append(slot)

    return disponiveis


def criar_agendamento(cliente_nome, cliente_telefone, servico_id, profissional_id, data_str, hora_str):
    """Cria o agendamento revalidando disponibilidade (evita corrida/duplicidade)."""
    disponiveis = horarios_disponiveis(profissional_id, data_str, servico_id)
    if hora_str not in disponiveis:
        return None, "Horário não disponível. Escolha outro horário."

    with db_session() as conn:
        cursor = conn.execute(
            """
            INSERT INTO agendamento (cliente_nome, cliente_telefone, servico_id, profissional_id, data, hora)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (cliente_nome, cliente_telefone, servico_id, profissional_id, data_str, hora_str),
        )
        agendamento_id = cursor.fetchone()["id"]

    return agendamento_id, None


def obter_agendamento_completo(agendamento_id):
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT a.*, s.nome AS servico_nome, s.preco AS servico_preco,
                   p.nome AS profissional_nome
            FROM agendamento a
            JOIN servico s ON s.id = a.servico_id
            JOIN profissional p ON p.id = a.profissional_id
            WHERE a.id = %s
            """,
            (agendamento_id,),
        ).fetchone()
        return dict(row) if row else None


def listar_agendamentos_por_periodo(data_inicio_str, data_fim_str):
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT a.*, s.nome AS servico_nome, s.preco AS servico_preco,
                   p.nome AS profissional_nome
            FROM agendamento a
            JOIN servico s ON s.id = a.servico_id
            JOIN profissional p ON p.id = a.profissional_id
            WHERE a.data BETWEEN %s AND %s
            ORDER BY a.data ASC, a.hora ASC
            """,
            (data_inicio_str, data_fim_str),
        ).fetchall()
        return [dict(r) for r in rows]


def verificar_admin(usuario, senha):
    from werkzeug.security import check_password_hash

    with db_session() as conn:
        row = conn.execute("SELECT * FROM admin WHERE usuario = %s", (usuario,)).fetchone()
        if not row:
            return False
        return check_password_hash(row["senha_hash"], senha)

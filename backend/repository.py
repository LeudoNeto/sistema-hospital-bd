from database import get_conexao


class Repository:
    """Consultas SQL (pymysql) do sistema hospitalar."""

    def paciente_existe(self, id_paciente: int) -> bool:
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM PACIENTE WHERE id_pessoa = %s", (id_paciente,)
                )
                return cursor.fetchone() is not None
        finally:
            conexao.close()

    def residente_existe(self, id_residente: int) -> bool:
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM RESIDENTE WHERE id_profissional = %s",
                    (id_residente,),
                )
                return cursor.fetchone() is not None
        finally:
            conexao.close()

    def preceptor_existe(self, id_preceptor: int) -> bool:
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM PRECEPTOR WHERE id_profissional = %s",
                    (id_preceptor,),
                )
                return cursor.fetchone() is not None
        finally:
            conexao.close()

    def inserir_atendimento(
        self,
        data_hora,
        duracao_minutos: int,
        id_paciente: int,
        id_residente: int,
        id_preceptor: int,
    ) -> int:
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO ATENDIMENTO
                        (data_hora, duracao_minutos, id_paciente, id_residente, id_preceptor)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        data_hora,
                        duracao_minutos,
                        id_paciente,
                        id_residente,
                        id_preceptor,
                    ),
                )
                novo_id = cursor.lastrowid
            conexao.commit()
            return novo_id
        finally:
            conexao.close()

    def listar_atendimentos_por_paciente(self, id_paciente: int) -> list:
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id_atendimento, data_hora, duracao_minutos,
                           id_paciente, id_residente, id_preceptor
                    FROM ATENDIMENTO
                    WHERE id_paciente = %s
                    ORDER BY data_hora
                    """,
                    (id_paciente,),
                )
                return cursor.fetchall()
        finally:
            conexao.close()

    def listar_procedimentos_realizados(self, id_atendimento: int) -> list:
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT p.nome, pr.quantidade, pr.tempo_real_minutos
                    FROM PROCEDIMENTO_REALIZADO pr
                    JOIN PROCEDIMENTO p ON p.id_procedimento = pr.id_procedimento
                    WHERE pr.id_atendimento = %s
                    """,
                    (id_atendimento,),
                )
                return cursor.fetchall()
        finally:
            conexao.close()

    def buscar_procedimento_realizado(
        self, id_atendimento: int, id_procedimento: int
    ) -> dict | None:
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT is_faturado
                    FROM PROCEDIMENTO_REALIZADO
                    WHERE id_atendimento = %s AND id_procedimento = %s
                    """,
                    (id_atendimento, id_procedimento),
                )
                return cursor.fetchone()
        finally:
            conexao.close()

    def remover_procedimento_realizado(
        self, id_atendimento: int, id_procedimento: int
    ) -> None:
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM PROCEDIMENTO_REALIZADO
                    WHERE id_atendimento = %s AND id_procedimento = %s
                    """,
                    (id_atendimento, id_procedimento),
                )
            conexao.commit()
        finally:
            conexao.close()

    def atualizar_paciente(self, id_paciente: int, campos: dict) -> None:
        atribuicoes = ", ".join(f"{coluna} = %s" for coluna in campos)
        valores = list(campos.values()) + [id_paciente]
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    f"UPDATE PACIENTE SET {atribuicoes} WHERE id_pessoa = %s",
                    valores,
                )
            conexao.commit()
        finally:
            conexao.close()

    def tempo_medio_por_residente(self) -> list:
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pe.nome,
                           ROUND(AVG(a.duracao_minutos), 2) AS tempo_medio_minutos
                    FROM ATENDIMENTO a
                    JOIN PESSOA pe ON pe.id_pessoa = a.id_residente
                    GROUP BY a.id_residente, pe.nome
                    ORDER BY tempo_medio_minutos DESC
                    """
                )
                return cursor.fetchall()
        finally:
            conexao.close()

    def ranking_residentes(self) -> list:
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pe.nome,
                           COUNT(a.id_atendimento) AS total_atendimentos
                    FROM RESIDENTE r
                    JOIN PESSOA pe ON pe.id_pessoa = r.id_profissional
                    LEFT JOIN ATENDIMENTO a ON a.id_residente = r.id_profissional
                    GROUP BY r.id_profissional, pe.nome
                    ORDER BY total_atendimentos DESC
                    """
                )
                return cursor.fetchall()
        finally:
            conexao.close()

    def preceptores_supervisao(self, mes: int, ano: int) -> list:
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pe.nome,
                           COUNT(*) AS total_atendimentos
                    FROM ATENDIMENTO a
                    JOIN PESSOA pe ON pe.id_pessoa = a.id_preceptor
                    WHERE MONTH(a.data_hora) = %s AND YEAR(a.data_hora) = %s
                    GROUP BY a.id_preceptor, pe.nome
                    HAVING COUNT(*) > 5
                    ORDER BY total_atendimentos DESC
                    """,
                    (mes, ano),
                )
                return cursor.fetchall()
        finally:
            conexao.close()

    def plantoes_por_unidade(self) -> list:
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT u.nome AS unidade,
                           pe.nome AS residente,
                           COUNT(*) AS total_plantoes
                    FROM ESCALA e
                    JOIN UNIDADE u ON u.id_unidade = e.id_unidade
                    JOIN PESSOA pe ON pe.id_pessoa = e.id_residente
                    WHERE e.mes_referencia = MONTH(CURDATE())
                      AND e.ano_referencia = YEAR(CURDATE())
                    GROUP BY u.id_unidade, u.nome, e.id_residente, pe.nome
                    ORDER BY u.nome, total_plantoes DESC
                    """
                )
                return cursor.fetchall()
        finally:
            conexao.close()

    def pacientes_sem_procedimento_alto(self) -> list:
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pe.id_pessoa AS id_paciente, pe.nome
                    FROM PACIENTE pac
                    JOIN PESSOA pe ON pe.id_pessoa = pac.id_pessoa
                    WHERE pac.id_pessoa NOT IN (
                        SELECT a.id_paciente
                        FROM ATENDIMENTO a
                        JOIN PROCEDIMENTO_REALIZADO pr
                            ON pr.id_atendimento = a.id_atendimento
                        JOIN PROCEDIMENTO p
                            ON p.id_procedimento = pr.id_procedimento
                        WHERE p.nivel_risco = 'alto'
                    )
                    ORDER BY pe.nome
                    """
                )
                return cursor.fetchall()
        finally:
            conexao.close()

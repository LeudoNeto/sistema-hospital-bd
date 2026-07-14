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

    def procedimento_existe(self, id_procedimento: int) -> bool:
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM PROCEDIMENTO WHERE id_procedimento = %s",
                    (id_procedimento,),
                )
                return cursor.fetchone() is not None
        finally:
            conexao.close()

    def inserir_atendimento_com_procedimentos(
        self,
        data_hora,
        duracao_minutos: int,
        id_paciente: int,
        id_residente: int,
        id_preceptor: int,
        procedimentos: list,
    ) -> int:
        """Insere o atendimento e seus procedimentos numa única transação.

        Garante a regra "todo atendimento tem ao menos um procedimento":
        se a inserção de qualquer procedimento falhar, o atendimento também
        é desfeito (rollback).
        """
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

                cursor.executemany(
                    """
                    INSERT INTO PROCEDIMENTO_REALIZADO
                        (id_atendimento, id_procedimento, quantidade,
                         tempo_real_minutos, observacao)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            novo_id,
                            p.id_procedimento,
                            p.quantidade,
                            p.tempo_real_minutos,
                            p.observacao,
                        )
                        for p in procedimentos
                    ],
                )
            conexao.commit()
            return novo_id
        except Exception:
            conexao.rollback()
            raise
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

    # ==================================================================
    # Extras para o front-end
    # (consultas de apoio às telas do painel; não fazem parte dos
    #  requisitos originais da Etapa 1)
    # ==================================================================

    def listar_atendimentos_com_nomes(self, id_paciente: int | None = None) -> list:
        """Lista os atendimentos já com os nomes das pessoas envolvidas.

        Sem ``id_paciente`` retorna todos; com ``id_paciente`` filtra por
        paciente. Usada pela tabela e pelo filtro da aba Atendimentos.
        """
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                consulta = """
                    SELECT a.id_atendimento,
                           a.data_hora,
                           a.duracao_minutos,
                           pac.nome  AS paciente,
                           res.nome  AS residente,
                           prec.nome AS preceptor
                    FROM ATENDIMENTO a
                    JOIN PESSOA pac  ON pac.id_pessoa  = a.id_paciente
                    JOIN PESSOA res  ON res.id_pessoa  = a.id_residente
                    JOIN PESSOA prec ON prec.id_pessoa = a.id_preceptor
                """
                parametros = ()
                if id_paciente is not None:
                    consulta += " WHERE a.id_paciente = %s"
                    parametros = (id_paciente,)
                consulta += " ORDER BY a.data_hora"
                cursor.execute(consulta, parametros)
                return cursor.fetchall()
        finally:
            conexao.close()

    def listar_procedimentos_realizados_detalhado(self, id_atendimento: int) -> list:
        """Igual à listagem original, porém com ``id_procedimento`` e
        ``is_faturado`` — o front precisa deles para montar/habilitar o
        botão de exclusão no modal."""
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pr.id_procedimento,
                           p.nome,
                           pr.quantidade,
                           pr.tempo_real_minutos,
                           pr.observacao,
                           pr.is_faturado
                    FROM PROCEDIMENTO_REALIZADO pr
                    JOIN PROCEDIMENTO p ON p.id_procedimento = pr.id_procedimento
                    WHERE pr.id_atendimento = %s
                    ORDER BY p.nome
                    """,
                    (id_atendimento,),
                )
                return cursor.fetchall()
        finally:
            conexao.close()

    def contar_procedimentos_do_atendimento(self, id_atendimento: int) -> int:
        """Usada para impedir a remoção do último procedimento de um
        atendimento (regra: todo atendimento tem ao menos um)."""
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM PROCEDIMENTO_REALIZADO
                    WHERE id_atendimento = %s
                    """,
                    (id_atendimento,),
                )
                return cursor.fetchone()["total"]
        finally:
            conexao.close()

    def listar_pacientes(self) -> list:
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pe.id_pessoa AS id_paciente,
                           pe.nome,
                           pac.num_convenio,
                           pac.grupo_sanguineo,
                           pac.alergias,
                           pac.endereco
                    FROM PACIENTE pac
                    JOIN PESSOA pe ON pe.id_pessoa = pac.id_pessoa
                    """
                )
                return cursor.fetchall()
        finally:
            conexao.close()

    def listar_procedimentos(self) -> list:
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id_procedimento,
                           codigo,
                           nome,
                           tempo_medio_minutos,
                           nivel_risco
                    FROM PROCEDIMENTO
                    ORDER BY codigo
                    """
                )
                return cursor.fetchall()
        finally:
            conexao.close()

    def listar_profissionais(self) -> list:
        """Lista os profissionais com o papel atual (Residente/Preceptor).

        O detalhe traz ``ano_residencia`` para residentes e ``titulacao``
        para preceptores.
        """
        conexao = get_conexao()
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pe.id_pessoa,
                           pe.nome,
                           pr.CRM,
                           pr.especialidade,
                           pr.data_admissao,
                           CASE
                               WHEN res.id_profissional IS NOT NULL THEN 'Residente'
                               WHEN prec.id_profissional IS NOT NULL THEN 'Preceptor'
                               ELSE '—'
                           END AS papel,
                           COALESCE(res.ano_residencia, prec.titulacao) AS detalhe
                    FROM PROFISSIONAL pr
                    JOIN PESSOA pe ON pe.id_pessoa = pr.id_pessoa
                    LEFT JOIN RESIDENTE res  ON res.id_profissional  = pr.id_pessoa
                    LEFT JOIN PRECEPTOR prec ON prec.id_profissional = pr.id_pessoa
                    """
                )
                return cursor.fetchall()
        finally:
            conexao.close()

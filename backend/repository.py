import json
from contextlib import contextmanager

from sqlalchemy import extract, func, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import aliased, contains_eager, joinedload, selectinload

from database import conexao_procedure, sessao, transacao
from erros import EntidadeNaoEncontrada, OperacaoNaoPermitida
from models import (
    Atendimento,
    AuditoriaAtendimento,
    Base,
    Escala,
    Paciente,
    Pessoa,
    Preceptor,
    Procedimento,
    ProcedimentoRealizado,
    Profissional,
    Residente,
    Unidade,
)

# Colunas de PACIENTE que a API permite atualizar (protege o setattr dinâmico).
CAMPOS_EDITAVEIS_PACIENTE = frozenset({"endereco", "num_convenio"})

# Idem para ATENDIMENTO. id_paciente não entra: ver AtendimentoUpdate.
CAMPOS_EDITAVEIS_ATENDIMENTO = frozenset(
    {"data_hora", "duracao_minutos", "id_residente", "id_preceptor", "id_unidade"}
)

# Ordem cronológica dos domínios de ESCALA (os valores são garantidos pelos
# CHECK da tabela; aqui servem só para ordenar a listagem).
DIAS_SEMANA = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")
TURNOS = ("manhã", "tarde", "noite")

# MYSQL_ERRNO usados pelos SIGNAL em database/procedures.sql e
# database/triggers.sql.
ERRO_NAO_ENCONTRADO = 4404  # entidade referenciada não existe
ERRO_REGRA_NEGOCIO = 1644   # default do SIGNAL SQLSTATE '45000'
ERRO_DUPLICADO = 1062       # ER_DUP_ENTRY: violação de UNIQUE


@contextmanager
def _erros_do_banco():
    """Traduz o ``SIGNAL`` das stored procedures e dos triggers nas exceções
    de negócio.

    Assim as mensagens escritas no banco caem no mesmo mapeamento para HTTP
    que o ``controller`` já aplica às regras validadas em Python. Vale tanto
    para as chamadas de procedure quanto para as escritas da ORM que podem
    ser barradas por um trigger.
    """
    try:
        yield
    except DBAPIError as erro:
        argumentos = getattr(erro.orig, "args", ())
        if len(argumentos) < 2:
            raise
        codigo, mensagem = argumentos[0], argumentos[1]
        if codigo == ERRO_NAO_ENCONTRADO:
            raise EntidadeNaoEncontrada(mensagem) from erro
        if codigo == ERRO_REGRA_NEGOCIO:
            raise OperacaoNaoPermitida(mensagem) from erro
        raise


class Repository:
    """Consultas e persistência do sistema hospitalar via SQLAlchemy ORM."""

    def _existe(self, entidade: type[Base], chave) -> bool:
        with sessao() as s:
            return s.get(entidade, chave) is not None

    def paciente_existe(self, id_paciente: int) -> bool:
        return self._existe(Paciente, id_paciente)

    def residente_existe(self, id_residente: int) -> bool:
        return self._existe(Residente, id_residente)

    def preceptor_existe(self, id_preceptor: int) -> bool:
        return self._existe(Preceptor, id_preceptor)

    def procedimento_existe(self, id_procedimento: int) -> bool:
        return self._existe(Procedimento, id_procedimento)

    def unidade_existe(self, id_unidade: int) -> bool:
        return self._existe(Unidade, id_unidade)

    def atendimento_existe(self, id_atendimento: int) -> bool:
        return self._existe(Atendimento, id_atendimento)

    def escala_existe(self, id_escala: int) -> bool:
        return self._existe(Escala, id_escala)


    def inserir_atendimento_com_procedimentos(
        self,
        data_hora,
        duracao_minutos: int,
        id_paciente: int,
        id_residente: int,
        id_preceptor: int,
        procedimentos: list,
        id_unidade: int | None = None,
    ) -> int:
        """Insere o atendimento e seus procedimentos numa única transação.

        Garante a regra "todo atendimento tem ao menos um procedimento": o
        ``transacao()`` faz rollback se qualquer inserção falhar, desfazendo
        também o atendimento.
        """
        with transacao() as s:
            atendimento = Atendimento(
                data_hora=data_hora,
                duracao_minutos=duracao_minutos,
                id_paciente=id_paciente,
                id_residente=id_residente,
                id_preceptor=id_preceptor,
                id_unidade=id_unidade,
                procedimentos_realizados=[
                    ProcedimentoRealizado(
                        id_procedimento=p.id_procedimento,
                        quantidade=p.quantidade,
                        tempo_real_minutos=p.tempo_real_minutos,
                        data_hora_inicio=p.data_hora_inicio,
                        observacao=p.observacao,
                    )
                    for p in procedimentos
                ],
            )
            s.add(atendimento)
            s.flush()
            return atendimento.id_atendimento



    def registrar_atendimento_completo_sp(
        self,
        data_hora,
        duracao_minutos: int,
        id_paciente: int,
        id_residente: int,
        id_preceptor: int,
        procedimentos: list,
        id_unidade: int | None = None,
    ) -> int:
        itens = [
            {
                "id_procedimento": p.id_procedimento,
                "quantidade": p.quantidade,
                "tempo_real_minutos": p.tempo_real_minutos,
                "data_hora_inicio": (
                    p.data_hora_inicio.strftime("%Y-%m-%d %H:%M:%S")
                    if p.data_hora_inicio
                    else None
                ),
                "observacao": p.observacao,
            }
            for p in procedimentos
        ]

        with _erros_do_banco(), conexao_procedure() as conn:
            conn.exec_driver_sql(
                "CALL sp_registrar_atendimento_completo"
                "(%s, %s, %s, %s, %s, %s, %s, @id_atendimento)",
                (
                    data_hora,
                    duracao_minutos,
                    id_paciente,
                    id_residente,
                    id_preceptor,
                    id_unidade,
                    json.dumps(itens, ensure_ascii=False),
                ),
            )
            return conn.exec_driver_sql("SELECT @id_atendimento").scalar()

    def tempo_medio_espera_por_unidade(
        self, mes: int | None = None, ano: int | None = None
    ) -> list:
        with _erros_do_banco(), conexao_procedure() as conn:
            linhas = conn.exec_driver_sql(
                "CALL sp_calcular_tempo_medio_espera(%s, %s)", (mes, ano)
            ).mappings().all()

        return [
            {
                "id_unidade": linha["id_unidade"],
                "unidade": linha["unidade"],
                "tipo": linha["tipo"],
                "atendimentos_medidos": linha["atendimentos_medidos"],
                "tempo_medio_espera_minutos": (
                    float(linha["tempo_medio_espera_minutos"])
                    if linha["tempo_medio_espera_minutos"] is not None
                    else None
                ),
                "menor_espera_minutos": linha["menor_espera_minutos"],
                "maior_espera_minutos": linha["maior_espera_minutos"],
            }
            for linha in linhas
        ]

    def reajustar_escala(
        self,
        id_residente: int,
        dia_origem: str,
        turno_origem: str,
        dia_destino: str,
        turno_destino: str,
        mes: int | None = None,
        ano: int | None = None,
    ) -> int:
        """``sp_reajustar_escala``: move as escalas do residente de um
        dia/turno para outro. Devolve quantas foram movidas.

        Havendo qualquer conflito, a procedure não move nada e sinaliza erro.
        """
        with _erros_do_banco(), conexao_procedure() as conn:
            conn.exec_driver_sql(
                "CALL sp_reajustar_escala(%s, %s, %s, %s, %s, %s, %s, @movidas)",
                (
                    id_residente,
                    dia_origem,
                    turno_origem,
                    dia_destino,
                    turno_destino,
                    mes,
                    ano,
                ),
            )
            return conn.exec_driver_sql("SELECT @movidas").scalar()

    def inserir_escala(self, dados) -> int:
        with _erros_do_banco(), transacao() as s:
            escala = Escala(
                id_unidade=dados.id_unidade,
                dia_semana=dados.dia_semana,
                turno=dados.turno,
                mes_referencia=dados.mes_referencia,
                ano_referencia=dados.ano_referencia,
                id_residente=dados.id_residente,
                id_preceptor=dados.id_preceptor,
            )
            s.add(escala)
            try:
                s.flush()
            except IntegrityError as erro:
                argumentos = getattr(erro.orig, "args", ())
                if argumentos and argumentos[0] == ERRO_DUPLICADO:
                    raise OperacaoNaoPermitida(
                        "O residente já está escalado nesta unidade neste "
                        "dia, turno e mês de referência."
                    ) from erro
                raise
            return escala.id_escala

    def remover_escala(self, id_escala: int) -> None:
        with transacao() as s:
            escala = s.get(Escala, id_escala)
            if escala is not None:
                s.delete(escala)

    def remover_procedimento_realizado(
        self, id_atendimento: int, id_procedimento: int
    ) -> None:
        with transacao() as s:
            registro = s.get(ProcedimentoRealizado, (id_atendimento, id_procedimento))
            if registro is not None:
                s.delete(registro)

    def atualizar_atendimento(self, id_atendimento: int, campos: dict) -> None:
        desconhecidos = set(campos) - CAMPOS_EDITAVEIS_ATENDIMENTO
        if desconhecidos:
            raise ValueError(f"Campos não editáveis: {sorted(desconhecidos)}")

        with transacao() as s:
            atendimento = s.get(Atendimento, id_atendimento)
            if atendimento is None:
                return
            for coluna, valor in campos.items():
                setattr(atendimento, coluna, valor)

    def remover_atendimento(self, id_atendimento: int) -> None:
        with transacao() as s:
            atendimento = s.get(Atendimento, id_atendimento)
            if atendimento is None:
                return

            afetados = [
                pr.id_procedimento for pr in atendimento.procedimentos_realizados
            ]
            s.delete(atendimento)
            s.flush()

            if afetados:
                media = (
                    select(func.round(func.avg(ProcedimentoRealizado.tempo_real_minutos), 2))
                    .where(
                        ProcedimentoRealizado.id_procedimento
                        == Procedimento.id_procedimento
                    )
                    .scalar_subquery()
                )
                s.execute(
                    update(Procedimento)
                    .where(Procedimento.id_procedimento.in_(afetados))
                    .values(media_tempo_procedimento=media)
                )

    def atualizar_paciente(self, id_paciente: int, campos: dict) -> None:
        desconhecidos = set(campos) - CAMPOS_EDITAVEIS_PACIENTE
        if desconhecidos:
            raise ValueError(f"Campos não editáveis: {sorted(desconhecidos)}")

        with transacao() as s:
            paciente = s.get(Paciente, id_paciente)
            if paciente is None:
                return
            for coluna, valor in campos.items():
                setattr(paciente, coluna, valor)


    def listar_atendimentos_por_paciente(self, id_paciente: int) -> list:
        with sessao() as s:
            consulta = (
                select(Atendimento)
                .where(Atendimento.id_paciente == id_paciente)
                .order_by(Atendimento.data_hora)
            )
            return [
                {
                    "id_atendimento": a.id_atendimento,
                    "data_hora": a.data_hora,
                    "duracao_minutos": a.duracao_minutos,
                    "id_paciente": a.id_paciente,
                    "id_residente": a.id_residente,
                    "id_preceptor": a.id_preceptor,
                }
                for a in s.scalars(consulta)
            ]

    def listar_procedimentos_realizados(self, id_atendimento: int) -> list:
        with sessao() as s:
            consulta = (
                select(ProcedimentoRealizado)
                .where(ProcedimentoRealizado.id_atendimento == id_atendimento)
                .options(joinedload(ProcedimentoRealizado.procedimento))
            )
            return [
                {
                    "nome": pr.procedimento.nome,
                    "quantidade": pr.quantidade,
                    "tempo_real_minutos": pr.tempo_real_minutos,
                }
                for pr in s.scalars(consulta).unique()
            ]

    def buscar_procedimento_realizado(
        self, id_atendimento: int, id_procedimento: int
    ) -> dict | None:
        with sessao() as s:
            registro = s.get(ProcedimentoRealizado, (id_atendimento, id_procedimento))
            if registro is None:
                return None
            return {"is_faturado": registro.is_faturado}

    def contar_procedimentos_do_atendimento(self, id_atendimento: int) -> int:
        with sessao() as s:
            consulta = (
                select(func.count())
                .select_from(ProcedimentoRealizado)
                .where(ProcedimentoRealizado.id_atendimento == id_atendimento)
            )
            return s.scalar(consulta) or 0


    def tempo_medio_por_residente(self) -> list:
        with sessao() as s:
            tempo_medio = func.round(func.avg(Atendimento.duracao_minutos), 2).label(
                "tempo_medio_minutos"
            )
            consulta = (
                select(Pessoa.nome, tempo_medio)
                .join(Pessoa, Pessoa.id_pessoa == Atendimento.id_residente)
                .group_by(Atendimento.id_residente, Pessoa.nome)
                .order_by(tempo_medio.desc())
            )
            return [
                {
                    "nome": linha.nome,
                    "tempo_medio_minutos": float(linha.tempo_medio_minutos),
                }
                for linha in s.execute(consulta)
            ]

    def ranking_residentes(self) -> list:
        with sessao() as s:
            total = func.count(Atendimento.id_atendimento).label("total_atendimentos")
            consulta = (
                select(Pessoa.nome, total)
                .select_from(Residente)
                .join(Pessoa, Pessoa.id_pessoa == Residente.id_profissional)
                .outerjoin(
                    Atendimento, Atendimento.id_residente == Residente.id_profissional
                )
                .group_by(Residente.id_profissional, Pessoa.nome)
                .order_by(total.desc())
            )
            return [
                {"nome": linha.nome, "total_atendimentos": linha.total_atendimentos}
                for linha in s.execute(consulta)
            ]

    def preceptores_supervisao(self, mes: int, ano: int) -> list:
        with sessao() as s:
            total = func.count().label("total_atendimentos")
            consulta = (
                select(Pessoa.nome, total)
                .select_from(Atendimento)
                .join(Pessoa, Pessoa.id_pessoa == Atendimento.id_preceptor)
                .where(
                    extract("month", Atendimento.data_hora) == mes,
                    extract("year", Atendimento.data_hora) == ano,
                )
                .group_by(Atendimento.id_preceptor, Pessoa.nome)
                .having(total > 5)
                .order_by(total.desc())
            )
            return [
                {"nome": linha.nome, "total_atendimentos": linha.total_atendimentos}
                for linha in s.execute(consulta)
            ]

    def plantoes_por_unidade(self) -> list:
        with sessao() as s:
            hoje = func.curdate()
            total = func.count().label("total_plantoes")
            consulta = (
                select(
                    Unidade.nome.label("unidade"),
                    Pessoa.nome.label("residente"),
                    total,
                )
                .select_from(Escala)
                .join(Unidade, Unidade.id_unidade == Escala.id_unidade)
                .join(Pessoa, Pessoa.id_pessoa == Escala.id_residente)
                .where(
                    Escala.mes_referencia == extract("month", hoje),
                    Escala.ano_referencia == extract("year", hoje),
                )
                .group_by(
                    Unidade.id_unidade, Unidade.nome, Escala.id_residente, Pessoa.nome
                )
                .order_by(Unidade.nome, total.desc())
            )
            return [
                {
                    "unidade": linha.unidade,
                    "residente": linha.residente,
                    "total_plantoes": linha.total_plantoes,
                }
                for linha in s.execute(consulta)
            ]

    def pacientes_sem_procedimento_alto(self) -> list:
        with sessao() as s:
            fez_procedimento_de_alto_risco = Paciente.atendimentos.any(
                Atendimento.procedimentos_realizados.any(
                    ProcedimentoRealizado.procedimento.has(
                        Procedimento.nivel_risco == "alto"
                    )
                )
            )
            consulta = (
                select(Pessoa.id_pessoa.label("id_paciente"), Pessoa.nome)
                .select_from(Paciente)
                .join(Pessoa, Pessoa.id_pessoa == Paciente.id_pessoa)
                .where(~fez_procedimento_de_alto_risco)
                .order_by(Pessoa.nome)
            )
            return [
                {"id_paciente": linha.id_paciente, "nome": linha.nome}
                for linha in s.execute(consulta)
            ]

    def tempos_observados_procedimentos(self) -> list:
        with sessao() as s:
            realizacoes = func.count(ProcedimentoRealizado.id_atendimento).label(
                "realizacoes"
            )
            consulta = (
                select(
                    Procedimento.codigo,
                    Procedimento.nome,
                    Procedimento.tempo_medio_minutos,
                    Procedimento.media_tempo_procedimento,
                    realizacoes,
                )
                .outerjoin(
                    ProcedimentoRealizado,
                    ProcedimentoRealizado.id_procedimento
                    == Procedimento.id_procedimento,
                )
                .group_by(
                    Procedimento.id_procedimento,
                    Procedimento.codigo,
                    Procedimento.nome,
                    Procedimento.tempo_medio_minutos,
                    Procedimento.media_tempo_procedimento,
                )
                .order_by(Procedimento.codigo)
            )

            linhas = []
            for linha in s.execute(consulta):
                observado = (
                    float(linha.media_tempo_procedimento)
                    if linha.media_tempo_procedimento is not None
                    else None
                )
                previsto = linha.tempo_medio_minutos
                desvio = round(observado - previsto, 2) if observado is not None else None
                linhas.append(
                    {
                        "codigo": linha.codigo,
                        "nome": linha.nome,
                        "tempo_estimado_minutos": previsto,
                        "media_observada_minutos": observado,
                        "realizacoes": linha.realizacoes,
                        "desvio_minutos": desvio,
                        "desvio_percentual": (
                            round(desvio / previsto * 100, 1)
                            if desvio is not None and previsto
                            else None
                        ),
                    }
                )
            return linhas

    def listar_auditoria(
        self,
        id_atendimento: int | None = None,
        operacao: str | None = None,
        limite: int = 200,
    ) -> list:
        with sessao() as s:
            consulta = select(AuditoriaAtendimento)
            if id_atendimento is not None:
                consulta = consulta.where(
                    AuditoriaAtendimento.id_atendimento == id_atendimento
                )
            if operacao is not None:
                consulta = consulta.where(AuditoriaAtendimento.operacao == operacao)
            consulta = consulta.order_by(
                AuditoriaAtendimento.id_auditoria.desc()
            ).limit(limite)

            return [
                {
                    "id_auditoria": registro.id_auditoria,
                    "id_atendimento": registro.id_atendimento,
                    "operacao": registro.operacao,
                    "usuario": registro.usuario,
                    "data_hora": registro.data_hora,
                    "dados_antigos": registro.dados_antigos,
                    "dados_novos": registro.dados_novos,
                }
                for registro in s.scalars(consulta)
            ]

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
        with sessao() as s:
            consulta = select(Atendimento).options(
                joinedload(Atendimento.paciente).joinedload(Paciente.pessoa),
                joinedload(Atendimento.residente)
                .joinedload(Residente.profissional)
                .joinedload(Profissional.pessoa),
                joinedload(Atendimento.preceptor)
                .joinedload(Preceptor.profissional)
                .joinedload(Profissional.pessoa),
            )
            if id_paciente is not None:
                consulta = consulta.where(Atendimento.id_paciente == id_paciente)
            consulta = consulta.order_by(Atendimento.data_hora)

            return [
                {
                    "id_atendimento": a.id_atendimento,
                    "data_hora": a.data_hora,
                    "duracao_minutos": a.duracao_minutos,
                    "paciente": a.paciente.pessoa.nome,
                    "residente": a.residente.profissional.pessoa.nome,
                    "preceptor": a.preceptor.profissional.pessoa.nome,
                    "id_residente": a.id_residente,
                    "id_preceptor": a.id_preceptor,
                    "id_unidade": a.id_unidade,
                }
                for a in s.scalars(consulta).unique()
            ]

    def listar_procedimentos_realizados_detalhado(self, id_atendimento: int) -> list:
        """Igual à listagem original, porém com ``id_procedimento`` e
        ``is_faturado`` — o front precisa deles para montar/habilitar o
        botão de exclusão no modal.
        """
        with sessao() as s:
            consulta = (
                select(ProcedimentoRealizado)
                .join(ProcedimentoRealizado.procedimento)
                .where(ProcedimentoRealizado.id_atendimento == id_atendimento)
                .options(contains_eager(ProcedimentoRealizado.procedimento))
                .order_by(Procedimento.nome)
            )
            return [
                {
                    "id_procedimento": pr.id_procedimento,
                    "nome": pr.procedimento.nome,
                    "quantidade": pr.quantidade,
                    "tempo_real_minutos": pr.tempo_real_minutos,
                    "observacao": pr.observacao,
                    "is_faturado": pr.is_faturado,
                }
                for pr in s.scalars(consulta).unique()
            ]

    def listar_pacientes(self) -> list:
        with sessao() as s:
            consulta = (
                select(Paciente)
                .options(joinedload(Paciente.pessoa))
                .order_by(Paciente.id_pessoa)
            )
            return [
                {
                    "id_paciente": pac.id_pessoa,
                    "nome": pac.pessoa.nome,
                    "num_convenio": pac.num_convenio,
                    "grupo_sanguineo": pac.grupo_sanguineo,
                    "alergias": pac.alergias,
                    "endereco": pac.endereco,
                }
                for pac in s.scalars(consulta).unique()
            ]

    def listar_procedimentos(self) -> list:
        with sessao() as s:
            consulta = select(Procedimento).order_by(Procedimento.codigo)
            return [
                {
                    "id_procedimento": proc.id_procedimento,
                    "codigo": proc.codigo,
                    "nome": proc.nome,
                    "tempo_medio_minutos": proc.tempo_medio_minutos,
                    "nivel_risco": proc.nivel_risco,
                }
                for proc in s.scalars(consulta)
            ]

    def listar_unidades(self) -> list:
        with sessao() as s:
            consulta = select(Unidade).order_by(Unidade.nome)
            return [
                {
                    "id_unidade": uni.id_unidade,
                    "nome": uni.nome,
                    "tipo": uni.tipo,
                    "capacidade_leitos": uni.capacidade_leitos,
                }
                for uni in s.scalars(consulta)
            ]

    def listar_escalas(self) -> list:
        with sessao() as s:
            pessoa_residente = aliased(Pessoa)
            pessoa_preceptor = aliased(Pessoa)
            consulta = (
                select(
                    Escala.id_escala,
                    Unidade.nome.label("unidade"),
                    Escala.dia_semana,
                    Escala.turno,
                    Escala.mes_referencia,
                    Escala.ano_referencia,
                    pessoa_residente.nome.label("residente"),
                    pessoa_preceptor.nome.label("preceptor"),
                )
                .join(Unidade, Unidade.id_unidade == Escala.id_unidade)
                .join(
                    pessoa_residente,
                    pessoa_residente.id_pessoa == Escala.id_residente,
                )
                .join(
                    pessoa_preceptor,
                    pessoa_preceptor.id_pessoa == Escala.id_preceptor,
                )
                .order_by(
                    Escala.ano_referencia.desc(),
                    Escala.mes_referencia.desc(),
                    Unidade.nome,
                    func.field(Escala.dia_semana, *DIAS_SEMANA),
                    func.field(Escala.turno, *TURNOS),
                )
            )
            return [
                {
                    "id_escala": linha.id_escala,
                    "unidade": linha.unidade,
                    "dia_semana": linha.dia_semana,
                    "turno": linha.turno,
                    "mes_referencia": linha.mes_referencia,
                    "ano_referencia": linha.ano_referencia,
                    "residente": linha.residente,
                    "preceptor": linha.preceptor,
                }
                for linha in s.execute(consulta)
            ]

    def listar_profissionais(self) -> list:
        """Lista os profissionais com o papel atual (Residente/Preceptor).

        O detalhe traz ``ano_residencia`` para residentes e ``titulacao``
        para preceptores.
        """
        with sessao() as s:
            consulta = (
                select(Profissional)
                .options(
                    joinedload(Profissional.pessoa),
                    selectinload(Profissional.residente),
                    selectinload(Profissional.preceptor),
                )
                .order_by(Profissional.id_pessoa)
            )

            linhas = []
            for prof in s.scalars(consulta).unique():
                if prof.residente is not None:
                    papel, detalhe = "Residente", prof.residente.ano_residencia
                elif prof.preceptor is not None:
                    papel, detalhe = "Preceptor", prof.preceptor.titulacao
                else:
                    papel, detalhe = "—", None
                linhas.append(
                    {
                        "id_pessoa": prof.id_pessoa,
                        "nome": prof.pessoa.nome,
                        "CRM": prof.crm,
                        "especialidade": prof.especialidade,
                        "data_admissao": prof.data_admissao,
                        "papel": papel,
                        "detalhe": detalhe,
                    }
                )
            return linhas

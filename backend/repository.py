from sqlalchemy import extract, func, select
from sqlalchemy.orm import contains_eager, joinedload, selectinload

from database import sessao, transacao
from models import (
    Atendimento,
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
                procedimentos_realizados=[
                    ProcedimentoRealizado(
                        id_procedimento=p.id_procedimento,
                        quantidade=p.quantidade,
                        tempo_real_minutos=p.tempo_real_minutos,
                        observacao=p.observacao,
                    )
                    for p in procedimentos
                ],
            )
            s.add(atendimento)
            s.flush()
            return atendimento.id_atendimento

    def remover_procedimento_realizado(
        self, id_atendimento: int, id_procedimento: int
    ) -> None:
        with transacao() as s:
            registro = s.get(ProcedimentoRealizado, (id_atendimento, id_procedimento))
            if registro is not None:
                s.delete(registro)

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

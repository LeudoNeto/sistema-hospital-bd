from erros import EntidadeNaoEncontrada, OperacaoNaoPermitida
from repository import Repository

__all__ = ["EntidadeNaoEncontrada", "Manager", "OperacaoNaoPermitida"]


class Manager:
    """Regras de negócio do sistema hospitalar."""

    def __init__(self):
        self.repository = Repository()

    def criar_atendimento(self, atendimento) -> int:
        if not self.repository.paciente_existe(atendimento.id_paciente):
            raise EntidadeNaoEncontrada(
                f"Paciente {atendimento.id_paciente} não encontrado."
            )
        if not self.repository.residente_existe(atendimento.id_residente):
            raise EntidadeNaoEncontrada(
                f"Residente {atendimento.id_residente} não encontrado."
            )
        if not self.repository.preceptor_existe(atendimento.id_preceptor):
            raise EntidadeNaoEncontrada(
                f"Preceptor {atendimento.id_preceptor} não encontrado."
            )

        # Regra: o atendimento precisa de ao menos um procedimento (garantida
        # pelo schema Pydantic) e cada procedimento deve existir e ser único.
        ids_procedimentos = [p.id_procedimento for p in atendimento.procedimentos]
        if len(ids_procedimentos) != len(set(ids_procedimentos)):
            raise OperacaoNaoPermitida(
                "Há procedimentos repetidos para o mesmo atendimento."
            )
        for id_procedimento in ids_procedimentos:
            if not self.repository.procedimento_existe(id_procedimento):
                raise EntidadeNaoEncontrada(
                    f"Procedimento {id_procedimento} não encontrado."
                )

        # Atendimento e seus procedimentos são gravados na mesma transação:
        # se qualquer inserção falhar, nada é persistido.
        return self.repository.inserir_atendimento_com_procedimentos(
            atendimento.data_hora,
            atendimento.duracao_minutos,
            atendimento.id_paciente,
            atendimento.id_residente,
            atendimento.id_preceptor,
            atendimento.procedimentos,
            atendimento.id_unidade,
        )

    def criar_atendimento_via_procedure(self, atendimento) -> int:
        return self.repository.registrar_atendimento_completo_sp(
            atendimento.data_hora,
            atendimento.duracao_minutos,
            atendimento.id_paciente,
            atendimento.id_residente,
            atendimento.id_preceptor,
            atendimento.procedimentos,
            atendimento.id_unidade,
        )

    def listar_atendimentos_por_paciente(self, id_paciente: int) -> list:
        return self.repository.listar_atendimentos_por_paciente(id_paciente)

    def listar_procedimentos_realizados(self, id_atendimento: int) -> list:
        return self.repository.listar_procedimentos_realizados(id_atendimento)

    def remover_procedimento_realizado(
        self, id_atendimento: int, id_procedimento: int
    ) -> None:
        registro = self.repository.buscar_procedimento_realizado(
            id_atendimento, id_procedimento
        )
        if registro is None:
            raise EntidadeNaoEncontrada(
                "Procedimento realizado não encontrado para este atendimento."
            )
        if registro["is_faturado"]:
            raise OperacaoNaoPermitida(
                "Não é possível remover: o procedimento já possui faturamento associado."
            )
        # Regra de negócio: todo atendimento tem ao menos um procedimento.
        # Assim como a criação exige >= 1 procedimento, a remoção não pode
        # deixar o atendimento sem nenhum.
        if self.repository.contar_procedimentos_do_atendimento(id_atendimento) <= 1:
            raise OperacaoNaoPermitida(
                "Não é possível remover: o atendimento precisa de ao menos um "
                "procedimento."
            )

        self.repository.remover_procedimento_realizado(
            id_atendimento, id_procedimento
        )

    def atualizar_atendimento(self, id_atendimento: int, dados) -> dict:
        if not self.repository.atendimento_existe(id_atendimento):
            raise EntidadeNaoEncontrada(
                f"Atendimento {id_atendimento} não encontrado."
            )

        campos = dados.model_dump(exclude_unset=True)

        if campos.get("id_residente") is not None and not self.repository.residente_existe(
            campos["id_residente"]
        ):
            raise EntidadeNaoEncontrada(
                f"Residente {campos['id_residente']} não encontrado."
            )
        if campos.get("id_preceptor") is not None and not self.repository.preceptor_existe(
            campos["id_preceptor"]
        ):
            raise EntidadeNaoEncontrada(
                f"Preceptor {campos['id_preceptor']} não encontrado."
            )
        if campos.get("id_unidade") is not None and not self.repository.unidade_existe(
            campos["id_unidade"]
        ):
            raise EntidadeNaoEncontrada(
                f"Unidade {campos['id_unidade']} não encontrada."
            )

        self.repository.atualizar_atendimento(id_atendimento, campos)
        return campos

    def remover_atendimento(self, id_atendimento: int) -> None:
        if not self.repository.atendimento_existe(id_atendimento):
            raise EntidadeNaoEncontrada(
                f"Atendimento {id_atendimento} não encontrado."
            )
        self.repository.remover_atendimento(id_atendimento)

    def atualizar_paciente(self, id_paciente: int, dados) -> dict:
        if not self.repository.paciente_existe(id_paciente):
            raise EntidadeNaoEncontrada(f"Paciente {id_paciente} não encontrado.")

        campos = dados.model_dump(exclude_none=True)
        self.repository.atualizar_paciente(id_paciente, campos)
        return campos

    def tempo_medio_por_residente(self) -> list:
        return self.repository.tempo_medio_por_residente()

    def ranking_residentes(self) -> list:
        return self.repository.ranking_residentes()

    def preceptores_supervisao(self, mes: int, ano: int) -> list:
        return self.repository.preceptores_supervisao(mes, ano)

    def plantoes_por_unidade(self) -> list:
        return self.repository.plantoes_por_unidade()

    def pacientes_sem_procedimento_alto(self) -> list:
        return self.repository.pacientes_sem_procedimento_alto()

    def tempos_observados_procedimentos(self) -> list:
        return self.repository.tempos_observados_procedimentos()

    def listar_auditoria(
        self,
        id_atendimento: int | None = None,
        operacao: str | None = None,
        limite: int = 200,
    ) -> list:
        return self.repository.listar_auditoria(id_atendimento, operacao, limite)

    def tempo_medio_espera_por_unidade(
        self, mes: int | None = None, ano: int | None = None
    ) -> list:
        return self.repository.tempo_medio_espera_por_unidade(mes, ano)

    def criar_escala(self, dados) -> int:
        if not self.repository.unidade_existe(dados.id_unidade):
            raise EntidadeNaoEncontrada(f"Unidade {dados.id_unidade} não encontrada.")
        if not self.repository.residente_existe(dados.id_residente):
            raise EntidadeNaoEncontrada(
                f"Residente {dados.id_residente} não encontrado."
            )
        if not self.repository.preceptor_existe(dados.id_preceptor):
            raise EntidadeNaoEncontrada(
                f"Preceptor {dados.id_preceptor} não encontrado."
            )

        return self.repository.inserir_escala(dados)

    def remover_escala(self, id_escala: int) -> None:
        if not self.repository.escala_existe(id_escala):
            raise EntidadeNaoEncontrada(f"Escala {id_escala} não encontrada.")
        self.repository.remover_escala(id_escala)

    def reajustar_escala(self, dados) -> int:
        return self.repository.reajustar_escala(
            dados.id_residente,
            dados.dia_origem,
            dados.turno_origem,
            dados.dia_destino,
            dados.turno_destino,
            dados.mes,
            dados.ano,
        )

    # ==================================================================
    # Extras para o front-end
    # (delegações das listagens que alimentam as telas do painel)
    # ==================================================================

    def listar_atendimentos_com_nomes(self, id_paciente: int | None = None) -> list:
        return self.repository.listar_atendimentos_com_nomes(id_paciente)

    def listar_procedimentos_realizados_detalhado(self, id_atendimento: int) -> list:
        return self.repository.listar_procedimentos_realizados_detalhado(
            id_atendimento
        )

    def listar_pacientes(self) -> list:
        return self.repository.listar_pacientes()

    def listar_procedimentos(self) -> list:
        return self.repository.listar_procedimentos()

    def listar_profissionais(self) -> list:
        return self.repository.listar_profissionais()

    def listar_unidades(self) -> list:
        return self.repository.listar_unidades()

    def listar_escalas(self) -> list:
        return self.repository.listar_escalas()

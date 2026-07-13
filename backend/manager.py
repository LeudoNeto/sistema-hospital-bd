from repository import Repository


class EntidadeNaoEncontrada(Exception):
    """Erro de negócio: uma entidade referenciada não existe no banco."""


class OperacaoNaoPermitida(Exception):
    """Erro de negócio: a operação viola uma regra do sistema."""


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

        return self.repository.inserir_atendimento(
            atendimento.data_hora,
            atendimento.duracao_minutos,
            atendimento.id_paciente,
            atendimento.id_residente,
            atendimento.id_preceptor,
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

        self.repository.remover_procedimento_realizado(
            id_atendimento, id_procedimento
        )

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

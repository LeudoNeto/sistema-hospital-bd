from fastapi import APIRouter, HTTPException

from manager import EntidadeNaoEncontrada, Manager, OperacaoNaoPermitida
from schemas import AtendimentoCreate, PacienteUpdate


class Controller:
    """Expõe todos os endpoints da API e delega ao manager."""

    def __init__(self):
        self.manager = Manager()
        self.router = APIRouter()
        self._registrar_rotas()

    def _registrar_rotas(self):
        manager = self.manager

        @self.router.post("/atendimentos", status_code=201, tags=["Atendimentos"])
        def criar_atendimento(atendimento: AtendimentoCreate):
            try:
                novo_id = manager.criar_atendimento(atendimento)
            except EntidadeNaoEncontrada as erro:
                raise HTTPException(status_code=404, detail=str(erro))
            return {"id_atendimento": novo_id}

        @self.router.get("/atendimentos", tags=["Atendimentos"])
        def listar_atendimentos_por_paciente(id_paciente: int):
            return manager.listar_atendimentos_por_paciente(id_paciente)

        @self.router.get(
            "/atendimentos/{id_atendimento}/procedimentos",
            tags=["Procedimentos realizados"],
        )
        def listar_procedimentos_realizados(id_atendimento: int):
            return manager.listar_procedimentos_realizados(id_atendimento)

        @self.router.delete(
            "/atendimentos/{id_atendimento}/procedimentos/{id_procedimento}",
            status_code=204,
            tags=["Procedimentos realizados"],
        )
        def remover_procedimento_realizado(id_atendimento: int, id_procedimento: int):
            try:
                manager.remover_procedimento_realizado(id_atendimento, id_procedimento)
            except EntidadeNaoEncontrada as erro:
                raise HTTPException(status_code=404, detail=str(erro))
            except OperacaoNaoPermitida as erro:
                raise HTTPException(status_code=409, detail=str(erro))

        @self.router.patch("/pacientes/{id_paciente}", tags=["Pacientes"])
        def atualizar_paciente(id_paciente: int, dados: PacienteUpdate):
            try:
                atualizado = manager.atualizar_paciente(id_paciente, dados)
            except EntidadeNaoEncontrada as erro:
                raise HTTPException(status_code=404, detail=str(erro))
            return {"id_paciente": id_paciente, **atualizado}

        @self.router.get("/relatorios/tempo-medio-residentes", tags=["Relatórios"])
        def tempo_medio_por_residente():
            return manager.tempo_medio_por_residente()

        @self.router.get("/relatorios/ranking-residentes", tags=["Relatórios"])
        def ranking_residentes():
            return manager.ranking_residentes()

        @self.router.get("/relatorios/preceptores-supervisao", tags=["Relatórios"])
        def preceptores_supervisao(mes: int, ano: int):
            return manager.preceptores_supervisao(mes, ano)

        @self.router.get("/relatorios/plantoes-por-unidade", tags=["Relatórios"])
        def plantoes_por_unidade():
            return manager.plantoes_por_unidade()

        @self.router.get(
            "/relatorios/pacientes-sem-procedimento-alto", tags=["Relatórios"]
        )
        def pacientes_sem_procedimento_alto():
            return manager.pacientes_sem_procedimento_alto()

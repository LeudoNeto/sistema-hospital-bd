from typing import Optional

from fastapi import APIRouter, HTTPException

from erros import EntidadeNaoEncontrada, OperacaoNaoPermitida
from manager import Manager
from schemas import (
    AtendimentoCreate,
    AtendimentoUpdate,
    EscalaCreate,
    EscalaReajuste,
    PacienteUpdate,
)


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
            except OperacaoNaoPermitida as erro:
                raise HTTPException(status_code=409, detail=str(erro))
            return {"id_atendimento": novo_id}

        @self.router.post(
            "/atendimentos/completo", status_code=201, tags=["Atendimentos"]
        )
        def criar_atendimento_via_procedure(atendimento: AtendimentoCreate):
            try:
                novo_id = manager.criar_atendimento_via_procedure(atendimento)
            except EntidadeNaoEncontrada as erro:
                raise HTTPException(status_code=404, detail=str(erro))
            except OperacaoNaoPermitida as erro:
                raise HTTPException(status_code=409, detail=str(erro))
            return {"id_atendimento": novo_id}

        @self.router.get("/atendimentos", tags=["Atendimentos"])
        def listar_atendimentos_por_paciente(id_paciente: int):
            return manager.listar_atendimentos_por_paciente(id_paciente)

        @self.router.patch("/atendimentos/{id_atendimento}", tags=["Atendimentos"])
        def atualizar_atendimento(id_atendimento: int, dados: AtendimentoUpdate):
            try:
                atualizado = manager.atualizar_atendimento(id_atendimento, dados)
            except EntidadeNaoEncontrada as erro:
                raise HTTPException(status_code=404, detail=str(erro))
            return {"id_atendimento": id_atendimento, **atualizado}

        @self.router.delete(
            "/atendimentos/{id_atendimento}", status_code=204, tags=["Atendimentos"]
        )
        def remover_atendimento(id_atendimento: int):
            try:
                manager.remover_atendimento(id_atendimento)
            except EntidadeNaoEncontrada as erro:
                raise HTTPException(status_code=404, detail=str(erro))

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

        @self.router.get("/relatorios/tempo-medio-espera", tags=["Relatórios"])
        def tempo_medio_espera_por_unidade(
            mes: Optional[int] = None, ano: Optional[int] = None
        ):
            return manager.tempo_medio_espera_por_unidade(mes, ano)

        @self.router.get(
            "/relatorios/tempos-observados-procedimentos", tags=["Relatórios"]
        )
        def tempos_observados_procedimentos():
            return manager.tempos_observados_procedimentos()

        @self.router.get("/escalas", tags=["Escalas"])
        def listar_escalas():
            return manager.listar_escalas()

        @self.router.post("/escalas", status_code=201, tags=["Escalas"])
        def criar_escala(escala: EscalaCreate):
            try:
                novo_id = manager.criar_escala(escala)
            except EntidadeNaoEncontrada as erro:
                raise HTTPException(status_code=404, detail=str(erro))
            except OperacaoNaoPermitida as erro:
                raise HTTPException(status_code=409, detail=str(erro))
            return {"id_escala": novo_id}

        @self.router.delete("/escalas/{id_escala}", status_code=204, tags=["Escalas"])
        def remover_escala(id_escala: int):
            try:
                manager.remover_escala(id_escala)
            except EntidadeNaoEncontrada as erro:
                raise HTTPException(status_code=404, detail=str(erro))

        @self.router.post("/escalas/reajustar", tags=["Escalas"])
        def reajustar_escala(dados: EscalaReajuste):
            try:
                movidas = manager.reajustar_escala(dados)
            except EntidadeNaoEncontrada as erro:
                raise HTTPException(status_code=404, detail=str(erro))
            except OperacaoNaoPermitida as erro:
                raise HTTPException(status_code=409, detail=str(erro))
            return {"escalas_movidas": movidas}

        @self.router.get("/auditoria", tags=["Auditoria"])
        def listar_auditoria(
            id_atendimento: Optional[int] = None,
            operacao: Optional[str] = None,
            limite: int = 200,
        ):
            return manager.listar_auditoria(id_atendimento, operacao, limite)

        # ==============================================================
        # Extras para o front-end
        # (rotas de apoio às telas do painel; não fazem parte dos
        #  requisitos originais da Etapa 1)
        # ==============================================================

        @self.router.get("/atendimentos/lista", tags=["Extras front-end"])
        def listar_atendimentos_com_nomes(id_paciente: Optional[int] = None):
            return manager.listar_atendimentos_com_nomes(id_paciente)

        @self.router.get(
            "/atendimentos/{id_atendimento}/procedimentos-detalhados",
            tags=["Extras front-end"],
        )
        def listar_procedimentos_realizados_detalhado(id_atendimento: int):
            return manager.listar_procedimentos_realizados_detalhado(id_atendimento)

        @self.router.get("/pacientes", tags=["Extras front-end"])
        def listar_pacientes():
            return manager.listar_pacientes()

        @self.router.get("/procedimentos", tags=["Extras front-end"])
        def listar_procedimentos():
            return manager.listar_procedimentos()

        @self.router.get("/profissionais", tags=["Extras front-end"])
        def listar_profissionais():
            return manager.listar_profissionais()

        @self.router.get("/unidades", tags=["Extras front-end"])
        def listar_unidades():
            return manager.listar_unidades()

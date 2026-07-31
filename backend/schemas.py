from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

# Domínios de ESCALA. Espelham os CHECK CK_DIA_SEMANA e CK_TURNO do schema —
# acentuados e em minúsculo, exatamente como gravados no banco.
DiaSemana = Literal["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
Turno = Literal["manhã", "tarde", "noite"]


class ProcedimentoRealizadoCreate(BaseModel):
    id_procedimento: int
    quantidade: int = Field(default=1, gt=0)
    tempo_real_minutos: int = Field(gt=0)
    data_hora_inicio: Optional[datetime] = None
    observacao: Optional[str] = None


class AtendimentoCreate(BaseModel):
    data_hora: datetime
    duracao_minutos: int = Field(gt=0)
    id_paciente: int
    id_residente: int
    id_preceptor: int
    id_unidade: Optional[int] = None
    # Regra de negócio: todo atendimento precisa de ao menos um procedimento.
    procedimentos: list[ProcedimentoRealizadoCreate] = Field(min_length=1)


class AtendimentoUpdate(BaseModel):
    data_hora: Optional[datetime] = None
    duracao_minutos: Optional[int] = Field(default=None, gt=0)
    id_residente: Optional[int] = None
    id_preceptor: Optional[int] = None
    # Único campo que aceita null como valor: o atendimento pode não ter
    # unidade. Por isso o PATCH olha os campos *enviados*, não os não-nulos.
    id_unidade: Optional[int] = None

    @model_validator(mode="after")
    def pelo_menos_um_campo(self):
        if not self.model_fields_set:
            raise ValueError(
                "Informe ao menos um campo para atualizar: 'data_hora', "
                "'duracao_minutos', 'id_residente', 'id_preceptor' ou 'id_unidade'."
            )
        return self


class EscalaCreate(BaseModel):
    id_unidade: int
    dia_semana: DiaSemana
    turno: Turno
    mes_referencia: int = Field(ge=1, le=12)
    ano_referencia: int = Field(ge=2000)
    id_residente: int
    id_preceptor: int


class EscalaReajuste(BaseModel):
    id_residente: int
    dia_origem: str
    turno_origem: str
    dia_destino: str
    turno_destino: str
    mes: Optional[int] = Field(default=None, ge=1, le=12)
    ano: Optional[int] = Field(default=None, ge=2000)


class InternacaoCreate(BaseModel):
    id_paciente: int
    id_unidade: int
    data_hora_entrada: datetime
    data_hora_saida: Optional[datetime] = None
    leito: Optional[str] = Field(default=None, max_length=10)
    motivo: Optional[str] = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def saida_nao_antecede_entrada(self):
        if (
            self.data_hora_saida is not None
            and self.data_hora_saida < self.data_hora_entrada
        ):
            raise ValueError("A data/hora de saída não pode ser anterior à de entrada.")
        return self


class PacienteUpdate(BaseModel):
    endereco: Optional[str] = None
    num_convenio: Optional[str] = None

    @model_validator(mode="after")
    def pelo_menos_um_campo(self):
        if self.endereco is None and self.num_convenio is None:
            raise ValueError(
                "Informe ao menos um campo para atualizar: 'endereco' ou 'num_convenio'."
            )
        return self

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

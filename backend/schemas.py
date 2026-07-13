from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class AtendimentoCreate(BaseModel):
    data_hora: datetime
    duracao_minutos: int = Field(gt=0)
    id_paciente: int
    id_residente: int
    id_preceptor: int


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

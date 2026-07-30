from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Classe base declarativa: guarda o registro de metadados/mapeamentos."""


class Pessoa(Base):
    __tablename__ = "PESSOA"

    id_pessoa: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    # A coluna no banco é "CPF" (maiúsculo); o atributo Python fica em minúsculo.
    cpf: Mapped[str] = mapped_column("CPF", String(11), nullable=False, unique=True)
    data_nascimento: Mapped[date] = mapped_column(Date, nullable=False)
    is_flamengo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    telefone: Mapped[Optional[str]] = mapped_column(String(20))

    paciente: Mapped[Optional["Paciente"]] = relationship(
        back_populates="pessoa", uselist=False
    )
    profissional: Mapped[Optional["Profissional"]] = relationship(
        back_populates="pessoa", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Pessoa id={self.id_pessoa} nome={self.nome!r}>"


class Paciente(Base):
    """Especialização de PESSOA (1:1 pela PK compartilhada)."""

    __tablename__ = "PACIENTE"

    id_pessoa: Mapped[int] = mapped_column(
        ForeignKey("PESSOA.id_pessoa", ondelete="CASCADE"), primary_key=True
    )
    num_convenio: Mapped[Optional[str]] = mapped_column(String(50))
    alergias: Mapped[Optional[str]] = mapped_column(Text)
    grupo_sanguineo: Mapped[Optional[str]] = mapped_column(String(3))
    endereco: Mapped[Optional[str]] = mapped_column(String(255))

    pessoa: Mapped["Pessoa"] = relationship(back_populates="paciente")
    atendimentos: Mapped[list["Atendimento"]] = relationship(back_populates="paciente")

    def __repr__(self) -> str:
        return f"<Paciente id={self.id_pessoa}>"


class Profissional(Base):
    """Especialização de PESSOA; por sua vez especializada em RESIDENTE/PRECEPTOR."""

    __tablename__ = "PROFISSIONAL"

    id_pessoa: Mapped[int] = mapped_column(
        ForeignKey("PESSOA.id_pessoa", ondelete="CASCADE"), primary_key=True
    )
    crm: Mapped[str] = mapped_column("CRM", String(20), nullable=False, unique=True)
    data_admissao: Mapped[date] = mapped_column(Date, nullable=False)
    especialidade: Mapped[str] = mapped_column(String(100), nullable=False)

    pessoa: Mapped["Pessoa"] = relationship(back_populates="profissional")
    residente: Mapped[Optional["Residente"]] = relationship(
        back_populates="profissional", uselist=False
    )
    preceptor: Mapped[Optional["Preceptor"]] = relationship(
        back_populates="profissional", uselist=False
    )
    historicos: Mapped[list["HistoricoProfissional"]] = relationship(
        back_populates="profissional"
    )

    def __repr__(self) -> str:
        return f"<Profissional id={self.id_pessoa} crm={self.crm!r}>"


class Residente(Base):
    __tablename__ = "RESIDENTE"

    id_profissional: Mapped[int] = mapped_column(
        ForeignKey("PROFISSIONAL.id_pessoa", ondelete="CASCADE"), primary_key=True
    )
    ano_residencia: Mapped[str] = mapped_column(String(2), nullable=False)

    profissional: Mapped["Profissional"] = relationship(back_populates="residente")
    atendimentos: Mapped[list["Atendimento"]] = relationship(back_populates="residente")
    escalas: Mapped[list["Escala"]] = relationship(back_populates="residente")

    def __repr__(self) -> str:
        return f"<Residente id={self.id_profissional} ano={self.ano_residencia!r}>"


class Preceptor(Base):
    __tablename__ = "PRECEPTOR"

    id_profissional: Mapped[int] = mapped_column(
        ForeignKey("PROFISSIONAL.id_pessoa", ondelete="CASCADE"), primary_key=True
    )
    titulacao: Mapped[str] = mapped_column(String(50), nullable=False)

    profissional: Mapped["Profissional"] = relationship(back_populates="preceptor")
    atendimentos: Mapped[list["Atendimento"]] = relationship(back_populates="preceptor")
    escalas: Mapped[list["Escala"]] = relationship(back_populates="preceptor")

    def __repr__(self) -> str:
        return f"<Preceptor id={self.id_profissional} titulacao={self.titulacao!r}>"


class HistoricoProfissional(Base):
    __tablename__ = "HISTORICO_PROFISSIONAL"

    id_historico: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_profissional: Mapped[int] = mapped_column(
        ForeignKey("PROFISSIONAL.id_pessoa", ondelete="CASCADE"), nullable=False
    )
    papel: Mapped[str] = mapped_column(String(20), nullable=False)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[Optional[date]] = mapped_column(Date)

    profissional: Mapped["Profissional"] = relationship(back_populates="historicos")


class Unidade(Base):
    __tablename__ = "UNIDADE"

    id_unidade: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    capacidade_leitos: Mapped[int] = mapped_column(nullable=False, default=0)

    escalas: Mapped[list["Escala"]] = relationship(back_populates="unidade")
    atendimentos: Mapped[list["Atendimento"]] = relationship(back_populates="unidade")

    def __repr__(self) -> str:
        return f"<Unidade id={self.id_unidade} nome={self.nome!r}>"


class Atendimento(Base):
    __tablename__ = "ATENDIMENTO"

    id_atendimento: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    data_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duracao_minutos: Mapped[int] = mapped_column(nullable=False)
    id_paciente: Mapped[int] = mapped_column(
        ForeignKey("PACIENTE.id_pessoa"), nullable=False
    )
    id_residente: Mapped[int] = mapped_column(
        ForeignKey("RESIDENTE.id_profissional"), nullable=False
    )
    id_preceptor: Mapped[int] = mapped_column(
        ForeignKey("PRECEPTOR.id_profissional"), nullable=False
    )
    id_unidade: Mapped[Optional[int]] = mapped_column(ForeignKey("UNIDADE.id_unidade"))

    paciente: Mapped["Paciente"] = relationship(back_populates="atendimentos")
    residente: Mapped["Residente"] = relationship(back_populates="atendimentos")
    preceptor: Mapped["Preceptor"] = relationship(back_populates="atendimentos")
    unidade: Mapped[Optional["Unidade"]] = relationship(back_populates="atendimentos")
    procedimentos_realizados: Mapped[list["ProcedimentoRealizado"]] = relationship(
        back_populates="atendimento", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Atendimento id={self.id_atendimento} data_hora={self.data_hora}>"


class Procedimento(Base):
    __tablename__ = "PROCEDIMENTO"

    id_procedimento: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    tempo_medio_minutos: Mapped[int] = mapped_column(nullable=False)
    media_tempo_procedimento: Mapped[Optional[Decimal]] = mapped_column(Numeric(7, 2))
    nivel_risco: Mapped[str] = mapped_column(String(10), nullable=False)

    realizacoes: Mapped[list["ProcedimentoRealizado"]] = relationship(
        back_populates="procedimento"
    )

    def __repr__(self) -> str:
        return f"<Procedimento id={self.id_procedimento} codigo={self.codigo!r}>"


class ProcedimentoRealizado(Base):
    """Relacionamento N:M entre ATENDIMENTO e PROCEDIMENTO, com atributos
    próprios (quantidade, tempo real, observação, faturamento) e PK composta."""

    __tablename__ = "PROCEDIMENTO_REALIZADO"

    id_atendimento: Mapped[int] = mapped_column(
        ForeignKey("ATENDIMENTO.id_atendimento", ondelete="CASCADE"), primary_key=True
    )
    id_procedimento: Mapped[int] = mapped_column(
        ForeignKey("PROCEDIMENTO.id_procedimento"), primary_key=True
    )
    quantidade: Mapped[int] = mapped_column(nullable=False, default=1)
    tempo_real_minutos: Mapped[int] = mapped_column(nullable=False)
    data_hora_inicio: Mapped[Optional[datetime]] = mapped_column(DateTime)
    observacao: Mapped[Optional[str]] = mapped_column(Text)
    is_faturado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    atendimento: Mapped["Atendimento"] = relationship(
        back_populates="procedimentos_realizados"
    )
    procedimento: Mapped["Procedimento"] = relationship(back_populates="realizacoes")

    def __repr__(self) -> str:
        return (
            f"<ProcedimentoRealizado atendimento={self.id_atendimento} "
            f"procedimento={self.id_procedimento}>"
        )


class Escala(Base):
    __tablename__ = "ESCALA"

    id_escala: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_unidade: Mapped[int] = mapped_column(
        ForeignKey("UNIDADE.id_unidade"), nullable=False
    )
    dia_semana: Mapped[str] = mapped_column(String(15), nullable=False)
    mes_referencia: Mapped[int] = mapped_column(nullable=False)
    ano_referencia: Mapped[int] = mapped_column(nullable=False)
    turno: Mapped[str] = mapped_column(String(15), nullable=False)
    id_residente: Mapped[int] = mapped_column(
        ForeignKey("RESIDENTE.id_profissional"), nullable=False
    )
    id_preceptor: Mapped[int] = mapped_column(
        ForeignKey("PRECEPTOR.id_profissional"), nullable=False
    )

    unidade: Mapped["Unidade"] = relationship(back_populates="escalas")
    residente: Mapped["Residente"] = relationship(back_populates="escalas")
    preceptor: Mapped["Preceptor"] = relationship(back_populates="escalas")

    def __repr__(self) -> str:
        return f"<Escala id={self.id_escala} unidade={self.id_unidade} turno={self.turno!r}>"


class AuditoriaAtendimento(Base):
    __tablename__ = "AUDITORIA_ATENDIMENTO"

    id_auditoria: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_atendimento: Mapped[int] = mapped_column(Integer, nullable=False)
    operacao: Mapped[str] = mapped_column(String(10), nullable=False)
    usuario: Mapped[str] = mapped_column(String(100), nullable=False)
    data_hora: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    dados_antigos: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    dados_novos: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)

    def __repr__(self) -> str:
        return (
            f"<AuditoriaAtendimento id={self.id_auditoria} "
            f"atendimento={self.id_atendimento} operacao={self.operacao!r}>"
        )

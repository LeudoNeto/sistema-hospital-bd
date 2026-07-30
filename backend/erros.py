"""Exceções de negócio compartilhadas.

Ficam num módulo próprio porque tanto o ``manager`` (regras em Python) quanto o
``repository`` (traduzindo o ``SIGNAL`` das stored procedures) precisam
levantá-las — e o ``repository`` não pode importar o ``manager``, que já o
importa.
"""


class EntidadeNaoEncontrada(Exception):
    """Erro de negócio: uma entidade referenciada não existe no banco."""


class OperacaoNaoPermitida(Exception):
    """Erro de negócio: a operação viola uma regra do sistema."""

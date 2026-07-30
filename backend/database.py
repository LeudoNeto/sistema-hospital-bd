import os
from collections.abc import Generator
from contextlib import contextmanager
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()


def _url_conexao() -> str:
    """Monta a URL de conexão a partir das variáveis de ambiente do .env."""
    usuario = os.getenv("MYSQL_USER", "")
    senha = quote_plus(os.getenv("MYSQL_PASSWORD", ""))
    host = os.getenv("MYSQL_HOST", "localhost")
    porta = os.getenv("MYSQL_PORT", "3306")
    banco = os.getenv("MYSQL_DATABASE", "")
    return (
        f"mysql+pymysql://{usuario}:{senha}@{host}:{porta}/{banco}?charset=utf8mb4"
    )


# echo=True imprime no log todo SQL gerado pela ORM — útil para conferir as
# consultas emitidas (inclusive as extras do lazy loading). Ligue com SQL_ECHO=true.
engine = create_engine(
    _url_conexao(),
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    pool_pre_ping=True,  # descarta conexões mortas antes de usá-las
    pool_recycle=3600,   # o MySQL fecha conexões ociosas (wait_timeout)
)

# expire_on_commit=False: após o commit os objetos continuam legíveis sem
# disparar um novo SELECT — necessário porque lemos o id gerado e montamos as
# respostas ainda com base nas instâncias carregadas.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def sessao() -> Generator[Session, None, None]:
    """Sessão de leitura: abre a ``Session``, garante o ``close()`` no fim.

    A transação implícita iniciada pelos SELECTs é encerrada pelo ``close()``,
    que devolve a conexão ao pool.
    """
    with SessionLocal() as sessao_atual:
        yield sessao_atual


@contextmanager
def transacao() -> Generator[Session, None, None]:
    """Sessão de escrita (*unit of work*): ``commit`` no fim do bloco,
    ``rollback`` se qualquer exceção escapar.

    É o que garante atomicidade em operações com mais de um INSERT/DELETE.
    """
    with SessionLocal() as sessao_atual:
        try:
            yield sessao_atual
            sessao_atual.commit()
        except Exception:
            sessao_atual.rollback()
            raise

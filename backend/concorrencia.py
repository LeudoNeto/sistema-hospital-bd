import logging
import sys
import threading
import time

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from erros import OperacaoNaoPermitida
from models import Escala, Residente

# Quanto cada transação segura o recurso antes do INSERT. É a janela da corrida:
# sem ela as duas quase nunca se cruzariam e o cenário 1 passaria sem conflito.
JANELA_SEGUNDOS = 0.6


def _logger() -> logging.Logger:
    log = logging.getLogger("concorrencia")
    if not log.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s.%(msecs)03d | CONCORRÊNCIA | %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        log.addHandler(handler)
        log.setLevel(logging.INFO)
        log.propagate = False
    return log


def _filtro_do_slot(dados):
    return (
        Escala.id_unidade == dados.id_unidade,
        Escala.dia_semana == dados.dia_semana,
        Escala.turno == dados.turno,
        Escala.id_residente == dados.id_residente,
        Escala.mes_referencia == dados.mes_referencia,
        Escala.ano_referencia == dados.ano_referencia,
    )


def _exigir_slot_livre(dados) -> None:
    with SessionLocal() as s:
        ocupado = s.scalar(select(Escala.id_escala).where(*_filtro_do_slot(dados)))
        if ocupado:
            raise OperacaoNaoPermitida(
                f"A escala #{ocupado} já ocupa esse slot. Se ela sobrou de uma "
                "execução anterior desta simulação, apague-a na aba Escalas; "
                "se for escala real, escolha outro dia, turno ou mês — a "
                "simulação não escreve sobre escala existente."
            )

        em_outra_unidade = s.scalar(
            select(Escala.id_escala).where(
                Escala.id_residente == dados.id_residente,
                Escala.dia_semana == dados.dia_semana,
                Escala.turno == dados.turno,
                Escala.mes_referencia == dados.mes_referencia,
                Escala.ano_referencia == dados.ano_referencia,
                Escala.id_unidade != dados.id_unidade,
            )
        )
        if em_outra_unidade:
            raise OperacaoNaoPermitida(
                f"O residente já está na escala #{em_outra_unidade} nesse "
                "dia/turno, em outra unidade: o trigger de sobreposição barraria "
                "o INSERT antes da corrida. Escolha outro dia ou turno."
            )


def _limpar_slot(dados) -> None:
    with SessionLocal() as s:
        s.execute(delete(Escala).where(*_filtro_do_slot(dados)))
        s.commit()


def _contar_no_slot(dados) -> int:
    with SessionLocal() as s:
        return s.scalar(
            select(func.count()).select_from(Escala).where(*_filtro_do_slot(dados))
        )


def _id_no_slot(dados) -> int | None:
    """Id da escala que sobrou no slot — a vencedora do último cenário."""
    with SessionLocal() as s:
        return s.scalar(select(Escala.id_escala).where(*_filtro_do_slot(dados)))


def _transacao_concorrente(
    nome: str,
    dados,
    usar_lock: bool,
    barreira: threading.Barrier,
    resultados: dict,
    log: logging.Logger,
) -> None:
    espera_lock = 0.0
    sessao = SessionLocal()
    try:
        # A barreira solta as duas threads no mesmo instante.
        barreira.wait()
        log.info("%s: BEGIN", nome)

        if usar_lock:
            log.info(
                "%s: SELECT ... FROM RESIDENTE WHERE id_profissional=%s FOR UPDATE",
                nome,
                dados.id_residente,
            )
            marco = time.monotonic()
            sessao.scalars(
                select(Residente)
                .where(Residente.id_profissional == dados.id_residente)
                .with_for_update()
            ).one()
            espera_lock = time.monotonic() - marco
            log.info("%s: lock obtido após %.0f ms", nome, espera_lock * 1000)

        consulta = select(Escala.id_escala).where(*_filtro_do_slot(dados))
        if usar_lock:
            consulta = consulta.with_for_update()
        existente = sessao.scalar(consulta)
        log.info(
            "%s: verifica o slot -> %s",
            nome,
            f"OCUPADO pela escala #{existente}" if existente else "VAGO",
        )

        if existente:
            log.info(
                "%s: ROLLBACK — recusa por regra de negócio, sem tentar o INSERT",
                nome,
            )
            sessao.rollback()
            resultados[nome] = {
                "resultado": "RECUSADA",
                "espera_no_lock_ms": round(espera_lock * 1000),
                "detalhe": (
                    f"Slot já ocupado pela escala #{existente}; recusado antes "
                    "do INSERT."
                ),
            }
            return

        log.info(
            "%s: segura %.1fs antes do INSERT (janela da corrida)",
            nome,
            JANELA_SEGUNDOS,
        )
        time.sleep(JANELA_SEGUNDOS)

        escala = Escala(
            id_unidade=dados.id_unidade,
            dia_semana=dados.dia_semana,
            turno=dados.turno,
            mes_referencia=dados.mes_referencia,
            ano_referencia=dados.ano_referencia,
            id_residente=dados.id_residente,
            id_preceptor=dados.id_preceptor,
        )
        sessao.add(escala)
        log.info("%s: INSERT INTO ESCALA ...", nome)
        sessao.flush()
        log.info("%s: INSERT aceito, id_escala=%s (ainda sem COMMIT)", nome, escala.id_escala)
        sessao.commit()
        log.info("%s: COMMIT", nome)
        resultados[nome] = {
            "resultado": "COMMIT",
            "espera_no_lock_ms": round(espera_lock * 1000),
            "detalhe": f"Escala #{escala.id_escala} gravada.",
        }

    except IntegrityError as erro:
        sessao.rollback()
        argumentos = getattr(erro.orig, "args", ())
        codigo = argumentos[0] if argumentos else None
        log.warning(
            "%s: ROLLBACK — o banco barrou no índice único (erro %s)", nome, codigo
        )
        resultados[nome] = {
            "resultado": "ERRO DO BANCO",
            "espera_no_lock_ms": round(espera_lock * 1000),
            "detalhe": (
                f"UN_ESCALA_CONFLITO violada (MySQL {codigo}) — a corrida só foi "
                "descoberta no INSERT."
            ),
        }
    except Exception as erro:  # noqa: BLE001 - o cenário precisa reportar qualquer falha
        sessao.rollback()
        log.warning("%s: ROLLBACK — %s: %s", nome, type(erro).__name__, erro)
        resultados[nome] = {
            "resultado": "ERRO",
            "espera_no_lock_ms": round(espera_lock * 1000),
            "detalhe": f"{type(erro).__name__}: {erro}",
        }
    finally:
        sessao.close()


def _rodar_cenario(rotulo: str, dados, usar_lock: bool, log: logging.Logger) -> list:
    log.info("=" * 68)
    log.info(
        "CENÁRIO: %s | residente=%s preceptor=%s unidade=%s | slot %s/%s %s/%s",
        rotulo,
        dados.id_residente,
        dados.id_preceptor,
        dados.id_unidade,
        dados.dia_semana,
        dados.turno,
        dados.mes_referencia,
        dados.ano_referencia,
    )
    log.info("=" * 68)

    resultados: dict = {}
    barreira = threading.Barrier(2)
    threads = [
        threading.Thread(
            target=_transacao_concorrente,
            args=(nome, dados, usar_lock, barreira, resultados, log),
            name=nome,
        )
        for nome in ("T1", "T2")
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    gravadas = _contar_no_slot(dados)
    log.info(
        "FIM DO CENÁRIO '%s': %s escala(s) no slot — %s",
        rotulo,
        gravadas,
        "consistente" if gravadas == 1 else "INCONSISTENTE!",
    )

    return [
        {
            "cenario": rotulo,
            "transacao": nome,
            "resultado": resultados.get(nome, {}).get("resultado", "SEM RESPOSTA"),
            "espera_no_lock_ms": resultados.get(nome, {}).get("espera_no_lock_ms", 0),
            "detalhe": resultados.get(nome, {}).get("detalhe", "A thread não concluiu."),
            "escalas_no_slot": gravadas,
        }
        for nome in ("T1", "T2")
    ]


def simular_escala_concorrente(dados) -> list:
    log = _logger()
    _exigir_slot_livre(dados)

    linhas = []
    try:
        linhas += _rodar_cenario("1. Sem lock (check-then-insert)", dados, False, log)
        _limpar_slot(dados)
        linhas += _rodar_cenario(
            "2. Com lock pessimista (FOR UPDATE)", dados, True, log
        )
    except Exception:
        _limpar_slot(dados)
        raise

    sobreviveu = _id_no_slot(dados)
    log.info(
        "Escala #%s mantida no banco para conferência — apague-a na aba Escalas "
        "antes de repetir a simulação com os mesmos parâmetros.",
        sobreviveu,
    )
    return linhas

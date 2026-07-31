DROP VIEW IF EXISTS vw_pacientes_internados;

CREATE VIEW vw_pacientes_internados AS
SELECT
    i.id_internacao,
    pac.id_pessoa                                              AS id_paciente,
    pes.nome                                                   AS paciente,
    TIMESTAMPDIFF(YEAR, pes.data_nascimento, CURDATE())        AS idade,
    pac.grupo_sanguineo,
    pac.alergias,
    pes.telefone,
    i.id_unidade,
    uni.nome                                                   AS unidade,
    uni.tipo                                                   AS tipo_unidade,
    i.leito,
    i.data_hora_entrada,
    TIMESTAMPDIFF(DAY, i.data_hora_entrada, NOW())             AS dias_internado,
    i.motivo
FROM INTERNACAO i
JOIN PACIENTE pac ON pac.id_pessoa  = i.id_paciente
JOIN PESSOA   pes ON pes.id_pessoa  = pac.id_pessoa
JOIN UNIDADE  uni ON uni.id_unidade = i.id_unidade
WHERE i.data_hora_saida IS NULL
  AND NOT EXISTS (
      SELECT 1
        FROM INTERNACAO mais_nova
       WHERE mais_nova.id_paciente = i.id_paciente
         AND (mais_nova.data_hora_entrada > i.data_hora_entrada
              OR (mais_nova.data_hora_entrada = i.data_hora_entrada
                  AND mais_nova.id_internacao > i.id_internacao))
  );



DROP VIEW IF EXISTS vw_residentes_sem_supervisor;

CREATE VIEW vw_residentes_sem_supervisor AS
SELECT
    esc.id_escala,
    esc.id_residente,
    pes_res.nome                    AS residente,
    res.ano_residencia,
    esc.id_preceptor,
    pes_prec.nome                   AS preceptor,
    prec.titulacao                  AS titulacao_preceptor,
    (h_ativo.id_historico IS NOT NULL) AS supervisao_ativa,
    CASE
        WHEN prec.titulacao NOT IN ('doutor', 'pos-doutor')
             AND h_ativo.id_historico IS NULL
            THEN 'Preceptor sem doutorado e sem supervisão ativa'
        WHEN prec.titulacao NOT IN ('doutor', 'pos-doutor')
            THEN 'Preceptor sem doutorado'
        ELSE 'Preceptor sem supervisão ativa'
    END                             AS motivo,
    uni.nome                        AS unidade,
    esc.dia_semana,
    esc.turno,
    esc.mes_referencia,
    esc.ano_referencia
FROM ESCALA esc
JOIN RESIDENTE res      ON res.id_profissional  = esc.id_residente
JOIN PESSOA    pes_res  ON pes_res.id_pessoa    = esc.id_residente
JOIN PRECEPTOR prec     ON prec.id_profissional = esc.id_preceptor
JOIN PESSOA    pes_prec ON pes_prec.id_pessoa   = esc.id_preceptor
JOIN UNIDADE   uni      ON uni.id_unidade       = esc.id_unidade
LEFT JOIN HISTORICO_PROFISSIONAL h_ativo
       ON h_ativo.id_profissional = esc.id_preceptor
      AND h_ativo.papel           = 'preceptor'
      AND h_ativo.data_fim IS NULL
WHERE prec.titulacao NOT IN ('doutor', 'pos-doutor')
   OR h_ativo.id_historico IS NULL;



DROP VIEW IF EXISTS vw_estatisticas_atendimentos_mensal;

CREATE VIEW vw_estatisticas_atendimentos_mensal AS
WITH estatisticas AS (
    SELECT
        YEAR(a.data_hora)                     AS ano,
        MONTH(a.data_hora)                    AS mes,
        a.id_unidade,
        COUNT(*)                              AS total_atendimentos,
        ROUND(AVG(a.duracao_minutos), 2)      AS duracao_media_minutos,
        MIN(a.duracao_minutos)                AS duracao_minima_minutos,
        MAX(a.duracao_minutos)                AS duracao_maxima_minutos
    FROM ATENDIMENTO a
    WHERE a.id_unidade IS NOT NULL
    GROUP BY YEAR(a.data_hora), MONTH(a.data_hora), a.id_unidade
),
-- Quantas vezes cada procedimento foi realizado em cada mês/unidade.
contagem_procedimentos AS (
    SELECT
        YEAR(a.data_hora)      AS ano,
        MONTH(a.data_hora)     AS mes,
        a.id_unidade,
        proc.id_procedimento,
        proc.nome,
        SUM(pr.quantidade)     AS vezes
    FROM ATENDIMENTO a
    JOIN PROCEDIMENTO_REALIZADO pr ON pr.id_atendimento  = a.id_atendimento
    JOIN PROCEDIMENTO         proc ON proc.id_procedimento = pr.id_procedimento
    WHERE a.id_unidade IS NOT NULL
    GROUP BY YEAR(a.data_hora), MONTH(a.data_hora), a.id_unidade,
             proc.id_procedimento, proc.nome
),
-- Colapsa a contagem acima em uma linha por mês/unidade, com o top 3.
mais_comuns AS (
    SELECT
        ano,
        mes,
        id_unidade,
        SUM(vezes) AS total_procedimentos,
        SUBSTRING_INDEX(
            GROUP_CONCAT(
                CONCAT(nome, ' (', vezes, 'x)')
                ORDER BY vezes DESC, nome
                SEPARATOR ' · '
            ),
            ' · ', 3
        ) AS procedimentos_mais_comuns
    FROM contagem_procedimentos
    GROUP BY ano, mes, id_unidade
)
SELECT
    est.ano,
    est.mes,
    est.id_unidade,
    uni.nome                                  AS unidade,
    uni.tipo                                  AS tipo_unidade,
    est.total_atendimentos,
    est.duracao_media_minutos,
    est.duracao_minima_minutos,
    est.duracao_maxima_minutos,
    COALESCE(com.total_procedimentos, 0)      AS total_procedimentos,
    com.procedimentos_mais_comuns
FROM estatisticas est
JOIN UNIDADE uni ON uni.id_unidade = est.id_unidade
-- LEFT JOIN: um mês/unidade pode ter atendimentos sem nenhum procedimento
-- registrado; a linha aparece com os procedimentos em NULL.
LEFT JOIN mais_comuns com
       ON com.ano        = est.ano
      AND com.mes        = est.mes
      AND com.id_unidade = est.id_unidade
ORDER BY est.ano DESC, est.mes DESC, uni.nome;

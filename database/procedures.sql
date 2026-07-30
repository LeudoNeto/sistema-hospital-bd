DROP PROCEDURE IF EXISTS sp_registrar_atendimento_completo;

DELIMITER $$

CREATE PROCEDURE sp_registrar_atendimento_completo(
    IN  p_data_hora       DATETIME,
    IN  p_duracao_minutos INT,
    IN  p_id_paciente     INT,
    IN  p_id_residente    INT,
    IN  p_id_preceptor    INT,
    IN  p_id_unidade      INT,
    IN  p_procedimentos   JSON,
    OUT p_id_atendimento  INT
)
BEGIN
    DECLARE v_total      INT DEFAULT 0;   -- itens na lista
    DECLARE v_distintos  INT DEFAULT 0;   -- itens com id_procedimento distinto
    DECLARE v_i          INT DEFAULT 0;   -- índice do laço
    DECLARE v_id_proc    INT;
    DECLARE v_quantidade INT;
    DECLARE v_tempo_real INT;
    DECLARE v_inicio     DATETIME;
    DECLARE v_observacao TEXT;
    DECLARE v_msg        VARCHAR(128);

    -- atomicidade
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_id_atendimento = NULL;
        RESIGNAL;
    END;

    SET p_id_atendimento = NULL;

    IF p_procedimentos IS NULL OR JSON_TYPE(p_procedimentos) <> 'ARRAY' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT =
            'p_procedimentos deve ser um array JSON.';
    END IF;

    SET v_total = JSON_LENGTH(p_procedimentos);

    -- Regra de negócio: todo atendimento tem ao menos um procedimento.
    IF v_total = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT =
            'Todo atendimento precisa de ao menos um procedimento.';
    END IF;

    SELECT COUNT(DISTINCT itens.id_procedimento) INTO v_distintos
      FROM JSON_TABLE(p_procedimentos, '$[*]' COLUMNS (
               id_procedimento INT PATH '$.id_procedimento'
           )) AS itens;

    IF v_distintos <> v_total THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT =
            'Há procedimentos repetidos para o mesmo atendimento.';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM PACIENTE WHERE id_pessoa = p_id_paciente) THEN
        SET v_msg = CONCAT('Paciente ', IFNULL(p_id_paciente, 'NULL'), ' não encontrado.');
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM RESIDENTE WHERE id_profissional = p_id_residente) THEN
        SET v_msg = CONCAT('Residente ', IFNULL(p_id_residente, 'NULL'), ' não encontrado.');
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM PRECEPTOR WHERE id_profissional = p_id_preceptor) THEN
        SET v_msg = CONCAT('Preceptor ', IFNULL(p_id_preceptor, 'NULL'), ' não encontrado.');
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;

    -- id_unidade é opcional; se vier preenchido, precisa existir.
    IF p_id_unidade IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM UNIDADE WHERE id_unidade = p_id_unidade) THEN
        SET v_msg = CONCAT('Unidade ', p_id_unidade, ' não encontrada.');
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;

    -- ------------------------- escrita transacional -------------------------
    START TRANSACTION;

    INSERT INTO ATENDIMENTO (
        data_hora, duracao_minutos, id_paciente, id_residente, id_preceptor, id_unidade
    ) VALUES (
        p_data_hora, p_duracao_minutos, p_id_paciente, p_id_residente, p_id_preceptor, p_id_unidade
    );

    SET p_id_atendimento = LAST_INSERT_ID();

    WHILE v_i < v_total DO
        SET v_id_proc    = JSON_EXTRACT(p_procedimentos, CONCAT('$[', v_i, '].id_procedimento'));
        SET v_quantidade = IFNULL(JSON_EXTRACT(p_procedimentos, CONCAT('$[', v_i, '].quantidade')), 1);
        SET v_tempo_real = JSON_EXTRACT(p_procedimentos, CONCAT('$[', v_i, '].tempo_real_minutos'));
        SET v_inicio     = NULLIF(JSON_UNQUOTE(JSON_EXTRACT(p_procedimentos, CONCAT('$[', v_i, '].data_hora_inicio'))), 'null');
        SET v_observacao = NULLIF(JSON_UNQUOTE(JSON_EXTRACT(p_procedimentos, CONCAT('$[', v_i, '].observacao'))), 'null');

        IF v_id_proc IS NULL THEN
            SET v_msg = CONCAT('Procedimento na posição ', v_i, ' sem "id_procedimento".');
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
        END IF;

        IF NOT EXISTS (SELECT 1 FROM PROCEDIMENTO WHERE id_procedimento = v_id_proc) THEN
            SET v_msg = CONCAT('Procedimento ', v_id_proc, ' não encontrado.');
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
        END IF;

        IF v_quantidade IS NULL OR v_quantidade <= 0 THEN
            SET v_msg = CONCAT('Quantidade inválida para o procedimento ', v_id_proc, '.');
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
        END IF;

        IF v_tempo_real IS NULL OR v_tempo_real <= 0 THEN
            SET v_msg = CONCAT('Tempo real inválido para o procedimento ', v_id_proc, '.');
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
        END IF;

        INSERT INTO PROCEDIMENTO_REALIZADO (
            id_atendimento, id_procedimento, quantidade,
            tempo_real_minutos, data_hora_inicio, observacao
        ) VALUES (
            p_id_atendimento, v_id_proc, v_quantidade,
            v_tempo_real, v_inicio, v_observacao
        );

        SET v_i = v_i + 1;
    END WHILE;

    COMMIT;
END$$

DELIMITER ;



DROP PROCEDURE IF EXISTS sp_calcular_tempo_medio_espera;

DELIMITER $$

CREATE PROCEDURE sp_calcular_tempo_medio_espera(
    IN p_mes INT,
    IN p_ano INT
)
BEGIN
    SELECT
        u.id_unidade,
        u.nome                                AS unidade,
        u.tipo,
        COUNT(espera.id_atendimento)          AS atendimentos_medidos,
        ROUND(AVG(espera.espera_minutos), 2)  AS tempo_medio_espera_minutos,
        MIN(espera.espera_minutos)            AS menor_espera_minutos,
        MAX(espera.espera_minutos)            AS maior_espera_minutos
    FROM UNIDADE u
    LEFT JOIN (
        SELECT
            a.id_atendimento,
            a.id_unidade,
            TIMESTAMPDIFF(MINUTE, a.data_hora, MIN(pr.data_hora_inicio)) AS espera_minutos
        FROM ATENDIMENTO a
        JOIN PROCEDIMENTO_REALIZADO pr ON pr.id_atendimento = a.id_atendimento
        WHERE pr.data_hora_inicio IS NOT NULL
          AND (p_mes IS NULL OR MONTH(a.data_hora) = p_mes)
          AND (p_ano IS NULL OR YEAR(a.data_hora)  = p_ano)
        GROUP BY a.id_atendimento, a.id_unidade, a.data_hora
    ) AS espera ON espera.id_unidade = u.id_unidade
    GROUP BY u.id_unidade, u.nome, u.tipo
    ORDER BY tempo_medio_espera_minutos DESC, u.nome;
END$$

DELIMITER ;



DROP PROCEDURE IF EXISTS sp_reajustar_escala;

DELIMITER $$

CREATE PROCEDURE sp_reajustar_escala(
    IN  p_id_residente    INT,
    IN  p_dia_origem      VARCHAR(15),
    IN  p_turno_origem    VARCHAR(15),
    IN  p_dia_destino     VARCHAR(15),
    IN  p_turno_destino   VARCHAR(15),
    IN  p_mes             INT,
    IN  p_ano             INT,
    OUT p_escalas_movidas INT
)
BEGIN
    DECLARE v_alvos     INT DEFAULT 0;  -- escalas que casam com a origem
    DECLARE v_conflitos INT DEFAULT 0;  -- quantas delas colidem no destino
    DECLARE v_unidades  VARCHAR(255);   -- nomes das unidades em conflito
    DECLARE v_msg       VARCHAR(128);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_escalas_movidas = 0;
        RESIGNAL;
    END;

    SET p_escalas_movidas = 0;

    IF NOT EXISTS (SELECT 1 FROM RESIDENTE WHERE id_profissional = p_id_residente) THEN
        SET v_msg = CONCAT('Residente ', IFNULL(p_id_residente, 'NULL'), ' não encontrado.');
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;

    IF p_dia_origem  NOT IN ('segunda','terça','quarta','quinta','sexta','sábado','domingo')
    OR p_dia_destino NOT IN ('segunda','terça','quarta','quinta','sexta','sábado','domingo') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT =
            'Dia da semana inválido (use segunda..domingo, minúsculo e acentuado).';
    END IF;

    IF p_turno_origem  NOT IN ('manhã','tarde','noite')
    OR p_turno_destino NOT IN ('manhã','tarde','noite') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT =
            'Turno inválido (use manhã, tarde ou noite).';
    END IF;

    IF p_dia_origem = p_dia_destino AND p_turno_origem = p_turno_destino THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT =
            'Origem e destino são o mesmo dia/turno — nada a reajustar.';
    END IF;

    START TRANSACTION;

    SELECT COUNT(*),
           SUM(
               EXISTS (
                   SELECT 1
                     FROM ESCALA destino
                    WHERE destino.id_residente    = origem.id_residente
                      AND destino.id_unidade      = origem.id_unidade
                      AND destino.mes_referencia  = origem.mes_referencia
                      AND destino.ano_referencia  = origem.ano_referencia
                      AND destino.dia_semana      = p_dia_destino
                      AND destino.turno           = p_turno_destino
               )
           )
      INTO v_alvos, v_conflitos
      FROM ESCALA origem
     WHERE origem.id_residente = p_id_residente
       AND origem.dia_semana   = p_dia_origem
       AND origem.turno        = p_turno_origem
       AND (p_mes IS NULL OR origem.mes_referencia = p_mes)
       AND (p_ano IS NULL OR origem.ano_referencia = p_ano)
     FOR UPDATE;

    IF v_alvos = 0 THEN
        SET v_msg = CONCAT('Nenhuma escala do residente em ', p_dia_origem, '/', p_turno_origem, '.');
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;

    IF v_conflitos > 0 THEN
        SELECT GROUP_CONCAT(DISTINCT u.nome ORDER BY u.nome SEPARATOR ', ')
          INTO v_unidades
          FROM ESCALA origem
          JOIN UNIDADE u ON u.id_unidade = origem.id_unidade
         WHERE origem.id_residente = p_id_residente
           AND origem.dia_semana   = p_dia_origem
           AND origem.turno        = p_turno_origem
           AND (p_mes IS NULL OR origem.mes_referencia = p_mes)
           AND (p_ano IS NULL OR origem.ano_referencia = p_ano)
           AND EXISTS (
               SELECT 1
                 FROM ESCALA destino
                WHERE destino.id_residente    = origem.id_residente
                  AND destino.id_unidade      = origem.id_unidade
                  AND destino.mes_referencia  = origem.mes_referencia
                  AND destino.ano_referencia  = origem.ano_referencia
                  AND destino.dia_semana      = p_dia_destino
                  AND destino.turno           = p_turno_destino
           );

        SET v_msg = LEFT(CONCAT('Conflito em ', p_dia_destino, '/', p_turno_destino,
                                ': residente já escalado em ', v_unidades, '.'), 128);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;

    UPDATE ESCALA
       SET dia_semana = p_dia_destino,
           turno      = p_turno_destino
     WHERE id_residente = p_id_residente
       AND dia_semana   = p_dia_origem
       AND turno        = p_turno_origem
       AND (p_mes IS NULL OR mes_referencia = p_mes)
       AND (p_ano IS NULL OR ano_referencia = p_ano);

    SET p_escalas_movidas = ROW_COUNT();

    COMMIT;
END$$

DELIMITER ;

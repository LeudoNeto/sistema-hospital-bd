DROP TRIGGER IF EXISTS trg_check_sobreposicao_escala_insert;
DROP TRIGGER IF EXISTS trg_check_sobreposicao_escala_update;

DELIMITER $$

CREATE TRIGGER trg_check_sobreposicao_escala_insert
BEFORE INSERT ON ESCALA
FOR EACH ROW
BEGIN
    DECLARE v_unidades VARCHAR(255);   -- nomes das unidades em conflito
    DECLARE v_msg      VARCHAR(128);

    SELECT GROUP_CONCAT(DISTINCT u.nome ORDER BY u.nome SEPARATOR ', ')
      INTO v_unidades
      FROM ESCALA e
      JOIN UNIDADE u ON u.id_unidade = e.id_unidade
     WHERE e.id_residente    = NEW.id_residente
       AND e.dia_semana      = NEW.dia_semana
       AND e.turno           = NEW.turno
       AND e.mes_referencia  = NEW.mes_referencia
       AND e.ano_referencia  = NEW.ano_referencia
       AND e.id_unidade     <> NEW.id_unidade;

    IF v_unidades IS NOT NULL THEN
        SET v_msg = LEFT(CONCAT('Sobreposição de escala: residente já escalado em ',
                                NEW.dia_semana, '/', NEW.turno, ' (',
                                NEW.mes_referencia, '/', NEW.ano_referencia,
                                ') na unidade ', v_unidades, '.'), 128);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;
END$$

CREATE TRIGGER trg_check_sobreposicao_escala_update
BEFORE UPDATE ON ESCALA
FOR EACH ROW
BEGIN
    DECLARE v_unidades VARCHAR(255);
    DECLARE v_msg      VARCHAR(128);

    SELECT GROUP_CONCAT(DISTINCT u.nome ORDER BY u.nome SEPARATOR ', ')
      INTO v_unidades
      FROM ESCALA e
      JOIN UNIDADE u ON u.id_unidade = e.id_unidade
     WHERE e.id_escala       <> NEW.id_escala
       AND e.id_residente     = NEW.id_residente
       AND e.dia_semana       = NEW.dia_semana
       AND e.turno            = NEW.turno
       AND e.mes_referencia   = NEW.mes_referencia
       AND e.ano_referencia   = NEW.ano_referencia
       AND e.id_unidade      <> NEW.id_unidade;

    IF v_unidades IS NOT NULL THEN
        SET v_msg = LEFT(CONCAT('Sobreposição de escala: residente já escalado em ',
                                NEW.dia_semana, '/', NEW.turno, ' (',
                                NEW.mes_referencia, '/', NEW.ano_referencia,
                                ') na unidade ', v_unidades, '.'), 128);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;
END$$

DELIMITER ;



DROP TRIGGER IF EXISTS trg_audita_atendimento_insert;
DROP TRIGGER IF EXISTS trg_audita_atendimento_update;
DROP TRIGGER IF EXISTS trg_audita_atendimento_delete;

DELIMITER $$

CREATE TRIGGER trg_audita_atendimento_insert
AFTER INSERT ON ATENDIMENTO
FOR EACH ROW
BEGIN
    INSERT INTO AUDITORIA_ATENDIMENTO (
        id_atendimento, operacao, usuario, data_hora, dados_antigos, dados_novos
    ) VALUES (
        NEW.id_atendimento, 'INSERT', CURRENT_USER(), NOW(),
        NULL,
        JSON_OBJECT(
            'id_atendimento',  NEW.id_atendimento,
            'data_hora',       DATE_FORMAT(NEW.data_hora, '%Y-%m-%d %H:%i:%s'),
            'duracao_minutos', NEW.duracao_minutos,
            'id_paciente',     NEW.id_paciente,
            'id_residente',    NEW.id_residente,
            'id_preceptor',    NEW.id_preceptor,
            'id_unidade',      NEW.id_unidade
        )
    );
END$$

CREATE TRIGGER trg_audita_atendimento_update
AFTER UPDATE ON ATENDIMENTO
FOR EACH ROW
BEGIN
    INSERT INTO AUDITORIA_ATENDIMENTO (
        id_atendimento, operacao, usuario, data_hora, dados_antigos, dados_novos
    ) VALUES (
        NEW.id_atendimento, 'UPDATE', CURRENT_USER(), NOW(),
        JSON_OBJECT(
            'id_atendimento',  OLD.id_atendimento,
            'data_hora',       DATE_FORMAT(OLD.data_hora, '%Y-%m-%d %H:%i:%s'),
            'duracao_minutos', OLD.duracao_minutos,
            'id_paciente',     OLD.id_paciente,
            'id_residente',    OLD.id_residente,
            'id_preceptor',    OLD.id_preceptor,
            'id_unidade',      OLD.id_unidade
        ),
        JSON_OBJECT(
            'id_atendimento',  NEW.id_atendimento,
            'data_hora',       DATE_FORMAT(NEW.data_hora, '%Y-%m-%d %H:%i:%s'),
            'duracao_minutos', NEW.duracao_minutos,
            'id_paciente',     NEW.id_paciente,
            'id_residente',    NEW.id_residente,
            'id_preceptor',    NEW.id_preceptor,
            'id_unidade',      NEW.id_unidade
        )
    );
END$$

CREATE TRIGGER trg_audita_atendimento_delete
AFTER DELETE ON ATENDIMENTO
FOR EACH ROW
BEGIN
    INSERT INTO AUDITORIA_ATENDIMENTO (
        id_atendimento, operacao, usuario, data_hora, dados_antigos, dados_novos
    ) VALUES (
        OLD.id_atendimento, 'DELETE', CURRENT_USER(), NOW(),
        JSON_OBJECT(
            'id_atendimento',  OLD.id_atendimento,
            'data_hora',       DATE_FORMAT(OLD.data_hora, '%Y-%m-%d %H:%i:%s'),
            'duracao_minutos', OLD.duracao_minutos,
            'id_paciente',     OLD.id_paciente,
            'id_residente',    OLD.id_residente,
            'id_preceptor',    OLD.id_preceptor,
            'id_unidade',      OLD.id_unidade
        ),
        NULL
    );
END$$

DELIMITER ;


DROP TRIGGER IF EXISTS trg_atualiza_media_procedimentos;

DELIMITER $$

CREATE TRIGGER trg_atualiza_media_procedimentos
AFTER INSERT ON PROCEDIMENTO_REALIZADO
FOR EACH ROW
BEGIN
    DECLARE v_media DECIMAL(7,2);

    SELECT ROUND(AVG(pr.tempo_real_minutos), 2)
      INTO v_media
      FROM PROCEDIMENTO_REALIZADO pr
     WHERE pr.id_procedimento = NEW.id_procedimento;

    UPDATE PROCEDIMENTO
       SET media_tempo_procedimento = v_media
     WHERE id_procedimento = NEW.id_procedimento;
END$$

DELIMITER ;

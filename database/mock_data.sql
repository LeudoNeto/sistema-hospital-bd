-- 1. 5 pacientes, 5 residentes, 5 preceptores
INSERT INTO PESSOA (id_pessoa, nome, CPF, data_nascimento, is_flamengo, telefone) VALUES 
-- Pacientes
(1, 'Leudo Neto', '11111111111', '1985-04-12', TRUE, '83999991111'),
(2, 'Yosef Joseph', '22222222222', '1990-08-25', FALSE, '83999992222'),
(3, 'Joker', '33333333333', '2001-03-15', FALSE, '83999993333'),
(4, 'Mulet Boy', '44444444444', '1975-11-03', TRUE, '83999994444'),
(5, 'Risadinha', '55555555555', '2010-02-20', FALSE, '83999995555'),
-- Residentes
(6, 'Dr. Marcelo', '66666666666', '1996-05-10', FALSE, '83988881111'),
(7, 'Dr. Iury', '77777777777', '1995-12-01', TRUE, '83988882222'),
(8, 'Dr. Yuri', '88888888888', '1997-07-14', FALSE, '83988883333'),
(9, 'Dr. Malheiros', '99999999999', '1994-09-30', TRUE, '83988884444'),
(10, 'Dra. Natasha', '10101010101', '1996-01-22', FALSE, '83988885555'),
-- Preceptores
(11, 'Dra. Thais', '12121212121', '1980-03-05', FALSE, '83977771111'),
(12, 'Dra. Gaudencio', '13131313131', '1978-08-19', TRUE, '83977772222'),
(13, 'Dr. Lincoln', '14141414141', '1982-11-11', FALSE, '83977773333'),
(14, 'Dra. Yuska', '15151515151', '1975-06-25', TRUE, '83977774444'),
(15, 'Dr. Não sei mais nomes para referenciar', '16161616161', '1970-12-10', FALSE, '83977775555');

-- 2. Especializando os 5 Pacientes
INSERT INTO PACIENTE (id_pessoa, num_convenio, alergias, grupo_sanguineo, endereco) VALUES
(1, 'UNIMED123', 'Dipirona', 'A+', 'Rua das Trincheiras, 100, João Pessoa - PB'),
(2, 'SULAMERICA456', 'Nenhuma', 'O-', 'Av. Epitácio Pessoa, 1500, João Pessoa - PB'),
(3, NULL, 'Lactose', 'B+', 'Rua Gotham, 42, Campina Grande - PB'),
(4, 'BRADESCO789', 'Penicilina', 'AB+', 'Rua do Sol, 250, João Pessoa - PB'),
(5, 'AMIL012', 'Nenhuma', 'O+', 'Rua da Alegria, 7, Campina Grande - PB');

-- 3. Especializando os 10 Profissionais
INSERT INTO PROFISSIONAL (id_pessoa, CRM, data_admissao, especialidade) VALUES 
(6, 'CRM-PB-1111', '2023-03-01', 'Clínica Médica'),
(7, 'CRM-PB-2222', '2023-03-01', 'Cirurgia Geral'),
(8, 'CRM-PB-3333', '2024-03-01', 'Pediatria'),
(9, 'CRM-PB-4444', '2022-03-01', 'Ortopedia'),
(10, 'CRM-PB-5555', '2024-03-01', 'Cardiologia'),
(11, 'CRM-PB-6666', '2015-01-10', 'Clínica Médica'),
(12, 'CRM-PB-7777', '2012-05-20', 'Cirurgia Geral'),
(13, 'CRM-PB-8888', '2010-11-05', 'Pediatria'),
(14, 'CRM-PB-9999', '2018-02-15', 'Ortopedia'),
(15, 'CRM-PB-0000', '2005-08-30', 'Cardiologia');

-- 4. Definindo os 5 Residentes
INSERT INTO RESIDENTE (id_profissional, ano_residencia) VALUES 
(6, 'R2'),
(7, 'R2'),
(8, 'R1'),
(9, 'R3'),
(10, 'R1');

-- 5. Definindo os 5 Preceptores
INSERT INTO PRECEPTOR (id_profissional, titulacao) VALUES 
(11, 'mestre'),
(12, 'doutor'),
(13, 'especialista'),
(14, 'mestre'),
(15, 'pos-doutor');

-- 6. 3 unidades
INSERT INTO UNIDADE (id_unidade, nome, tipo, capacidade_leitos) VALUES 
(1, 'Ala Amarela', 'Pronto-Socorro', 20),
(2, 'UTI Geral', 'UTI', 10),
(3, 'Enfermaria Pediátrica', 'Enfermaria', 15);

-- 7. procedimentos
INSERT INTO PROCEDIMENTO (id_procedimento, codigo, nome, tempo_medio_minutos, nivel_risco) VALUES
(1, 'P001', 'Sutura Simples', 30, 'médio'),
(2, 'P002', 'Coleta de Sangue', 15, 'baixo'),
(3, 'P003', 'Eletrocardiograma', 20, 'baixo'),
(4, 'P004', 'Raio-X de Tórax', 25, 'baixo'),
(5, 'P005', 'Administração de Medicamento IV', 10, 'médio'),
(6, 'P006', 'Cirurgia de Emergência', 180, 'alto'),
(7, 'P007', 'Reanimação Cardiopulmonar', 45, 'alto');

-- 8. 10 atendimentos
INSERT INTO ATENDIMENTO (id_atendimento, data_hora, duracao_minutos, id_paciente, id_residente, id_preceptor) VALUES 
(1, '2024-10-20 08:30:00', 45, 1, 6, 11),
(2, '2024-10-20 09:15:00', 60, 2, 7, 12),
(3, '2024-10-20 10:00:00', 30, 3, 8, 13),
(4, '2024-10-21 14:00:00', 120, 4, 9, 14),
(5, '2024-10-21 15:30:00', 40, 5, 10, 15),
(6, '2024-10-22 08:00:00', 50, 1, 6, 11),
(7, '2024-10-22 11:45:00', 25, 2, 8, 13),
(8, '2024-10-23 16:20:00', 90, 3, 7, 12),
(9, '2024-10-24 19:10:00', 35, 4, 9, 14),
(10, '2024-10-25 21:00:00', 45, 5, 10, 15),
(11, '2026-07-01 08:00:00', 60, 1, 6, 11),
(12, '2026-07-02 09:00:00', 90, 2, 6, 11),
(13, '2026-07-03 10:00:00', 30, 3, 6, 11),
(14, '2026-07-04 08:30:00', 45, 1, 6, 11),
(15, '2026-07-05 11:00:00', 40, 4, 6, 11),
(16, '2026-07-06 14:00:00', 50, 5, 6, 11),
(17, '2026-07-07 08:00:00', 120, 2, 7, 12),
(18, '2026-07-08 09:30:00', 30, 3, 7, 12),
(19, '2026-07-09 10:00:00', 25, 4, 7, 12),
(20, '2026-07-10 08:00:00', 35, 5, 8, 13),
(21, '2026-07-10 13:00:00', 40, 3, 8, 13),
(22, '2026-07-11 09:00:00', 55, 4, 9, 14);

-- 9. 10 procedimentos realizados
INSERT INTO PROCEDIMENTO_REALIZADO (id_atendimento, id_procedimento, quantidade, tempo_real_minutos, observacao, is_faturado) VALUES
(1, 1, 1, 35, 'Sutura de 3 pontos no braço direito.', TRUE),
(1, 5, 2, 12, 'Paciente relatou leve ardência.', TRUE),
(2, 4, 1, 20, 'Imagem com boa nitidez.', TRUE),
(3, 2, 1, 10, 'Acesso venoso difícil, necessário duas tentativas.', FALSE),
(4, 3, 1, 25, 'Alteração leve detectada, encaminhado para especialista.', TRUE),
(4, 5, 1, 10, 'Sem intercorrências.', FALSE),
(5, 2, 1, 15, 'Coleta padrão.', TRUE),
(6, 1, 1, 40, 'Sutura extensa na perna.', TRUE),
(8, 4, 1, 30, 'Paciente com dificuldade de mobilidade.', FALSE),
(10, 3, 1, 18, 'Exame de rotina.', TRUE),
(11, 6, 1, 185, 'Cirurgia de emergência após trauma (paciente 1).', TRUE),
(11, 5, 2, 12, 'Medicação intravenosa no pós-operatório.', TRUE),
(12, 7, 1, 50, 'Reanimação cardiopulmonar bem-sucedida (paciente 2).', TRUE),
(13, 2, 1, 14, 'Coleta de rotina.', FALSE),
(14, 1, 1, 32, 'Sutura no couro cabeludo.', TRUE),
(15, 3, 1, 22, 'ECG sem alterações.', TRUE),
(16, 4, 1, 26, 'Raio-X de controle.', FALSE),
(17, 1, 1, 38, 'Sutura em membro inferior.', TRUE),
(18, 5, 1, 11, 'Antibiótico intravenoso.', TRUE),
(19, 2, 1, 15, 'Coleta para exames laboratoriais.', FALSE),
(20, 3, 1, 19, 'Eletrocardiograma de rotina.', TRUE),
(21, 4, 1, 27, 'Raio-X de tórax.', TRUE),
(22, 5, 1, 10, 'Hidratação intravenosa.', FALSE);

-- 10. Histórico profissional (papéis ao longo do tempo)
INSERT INTO HISTORICO_PROFISSIONAL (id_historico, id_profissional, papel, data_inicio, data_fim) VALUES
-- Residentes: vínculo atual em aberto (data_fim NULL)
(1, 6, 'residente', '2023-03-01', NULL),
(2, 7, 'residente', '2023-03-01', NULL),
(3, 8, 'residente', '2024-03-01', NULL),
(4, 9, 'residente', '2022-03-01', NULL),
(5, 10, 'residente', '2024-03-01', NULL),
-- Preceptores: período anterior como residente (encerrado) + vínculo atual como preceptor
(6, 11, 'residente', '2012-03-01', '2015-01-09'),
(7, 11, 'preceptor', '2015-01-10', NULL),
(8, 12, 'residente', '2009-03-01', '2012-05-19'),
(9, 12, 'preceptor', '2012-05-20', NULL),
(10, 13, 'preceptor', '2010-11-05', NULL),
(11, 14, 'preceptor', '2018-02-15', NULL),
(12, 15, 'preceptor', '2005-08-30', NULL);

-- 11. Escalas de plantão
INSERT INTO ESCALA (id_escala, id_unidade, dia_semana, mes_referencia, ano_referencia, turno, id_residente, id_preceptor) VALUES
-- Mês corrente (julho/2026)
--   Unidade 1: residente 6 = 2 plantões, residente 7 = 1, residente 8 = 1
--   Unidade 2: residente 9 = 2 plantões, residente 10 = 1
--   Unidade 3: residente 8 = 1 plantão,  residente 10 = 1
(1, 1, 'segunda', 7, 2026, 'manhã', 6, 11),
(2, 1, 'terça', 7, 2026, 'manhã', 6, 11),
(3, 1, 'quarta', 7, 2026, 'tarde', 7, 12),
(4, 1, 'quinta', 7, 2026, 'noite', 8, 13),
(5, 2, 'segunda', 7, 2026, 'noite', 9, 14),
(6, 2, 'terça', 7, 2026, 'noite', 10, 15),
(7, 2, 'quarta', 7, 2026, 'noite', 9, 14),
(8, 3, 'sexta', 7, 2026, 'manhã', 8, 13),
(9, 3, 'sábado', 7, 2026, 'tarde', 10, 15),
-- Mês anterior (junho/2026)
(10, 1, 'segunda', 6, 2026, 'manhã', 6, 11),
(11, 2, 'terça', 6, 2026, 'noite', 9, 14);
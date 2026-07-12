-- 1. TABELA: PESSOA
CREATE TABLE PESSOA (
    id_pessoa INT AUTO_INCREMENT,
    nome VARCHAR(150) NOT NULL,
    CPF VARCHAR(11) NOT NULL,
    data_nascimento DATE NOT NULL,
    is_flamengo BOOLEAN NOT NULL DEFAULT FALSE,
    telefone VARCHAR(20),
    CONSTRAINT PK_PESSOA PRIMARY KEY (id_pessoa),
    CONSTRAINT UN_PESSOA_CPF UNIQUE (CPF)
);

-- 2. TABELA: PACIENTE (Especialização de PESSOA)
CREATE TABLE PACIENTE (
    id_pessoa INT,
    num_convenio VARCHAR(50),
    alergias TEXT,
    grupo_sanguineo VARCHAR(3),
    endereco VARCHAR(255),
    CONSTRAINT PK_PACIENTE PRIMARY KEY (id_pessoa),
    CONSTRAINT FK_PACIENTE_PESSOA FOREIGN KEY (id_pessoa)
        REFERENCES PESSOA(id_pessoa) ON DELETE CASCADE
);

-- 3. TABELA: PROFISSIONAL (Especialização de PESSOA)
CREATE TABLE PROFISSIONAL (
    id_pessoa INT,
    CRM VARCHAR(20) NOT NULL,
    data_admissao DATE NOT NULL,
    especialidade VARCHAR(100) NOT NULL,
    CONSTRAINT PK_PROFISSIONAL PRIMARY KEY (id_pessoa),
    CONSTRAINT FK_PROFISSIONAL_PESSOA FOREIGN KEY (id_pessoa) 
        REFERENCES PESSOA(id_pessoa) ON DELETE CASCADE,
    CONSTRAINT UN_PROFISSIONAL_CRM UNIQUE (CRM)
);

-- 4. TABELA: PRECEPTOR (Especialização de PROFISSIONAL)
CREATE TABLE PRECEPTOR (
    id_profissional INT,
    titulacao VARCHAR(50) NOT NULL,
    CONSTRAINT PK_PRECEPTOR PRIMARY KEY (id_profissional),
    CONSTRAINT FK_PRECEPTOR_PROFISSIONAL FOREIGN KEY (id_profissional) 
        REFERENCES PROFISSIONAL(id_pessoa) ON DELETE CASCADE,
    CONSTRAINT CK_TITULACAO CHECK (titulacao IN ('especialista', 'mestre', 'doutor', 'pos-doutor'))
);

-- 5. TABELA: RESIDENTE (Especialização de PROFISSIONAL)
CREATE TABLE RESIDENTE (
    id_profissional INT,
    ano_residencia VARCHAR(2) NOT NULL,
    CONSTRAINT PK_RESIDENTE PRIMARY KEY (id_profissional),
    CONSTRAINT FK_RESIDENTE_PROFISSIONAL FOREIGN KEY (id_profissional) 
        REFERENCES PROFISSIONAL(id_pessoa) ON DELETE CASCADE,
    CONSTRAINT CK_ANO_RESIDENCIA CHECK (ano_residencia IN ('R1', 'R2', 'R3'))
);

-- 6. TABELA: HISTORICO_PROFISSIONAL
CREATE TABLE HISTORICO_PROFISSIONAL (
    id_historico INT AUTO_INCREMENT,
    id_profissional INT NOT NULL,
    papel VARCHAR(20) NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE,
    CONSTRAINT PK_HISTORICO_PROFISSIONAL PRIMARY KEY (id_historico),
    CONSTRAINT FK_HISTORICO_PROFISSIONAL FOREIGN KEY (id_profissional)
        REFERENCES PROFISSIONAL(id_pessoa) ON DELETE CASCADE,
    CONSTRAINT CK_HISTORICO_PAPEL CHECK (papel IN ('residente', 'preceptor'))
);

-- 7. TABELA: UNIDADE
CREATE TABLE UNIDADE (
    id_unidade INT AUTO_INCREMENT,
    nome VARCHAR(100) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    capacidade_leitos INT NOT NULL DEFAULT 0,
    CONSTRAINT PK_UNIDADE PRIMARY KEY (id_unidade),
    CONSTRAINT CK_TIPO_UNIDADE CHECK (tipo IN ('Enfermaria', 'UTI', 'Pronto-Socorro', 'Ambulatório'))
);

-- 8. TABELA: ATENDIMENTO
CREATE TABLE ATENDIMENTO (
    id_atendimento INT AUTO_INCREMENT,
    data_hora DATETIME NOT NULL,
    duracao_minutos INT NOT NULL,
    id_paciente INT NOT NULL,
    id_residente INT NOT NULL,
    id_preceptor INT NOT NULL,
    CONSTRAINT PK_ATENDIMENTO PRIMARY KEY (id_atendimento),
    CONSTRAINT FK_ATENDIMENTO_PACIENTE FOREIGN KEY (id_paciente) 
        REFERENCES PACIENTE(id_pessoa),
    CONSTRAINT FK_ATENDIMENTO_RESIDENTE FOREIGN KEY (id_residente) 
        REFERENCES RESIDENTE(id_profissional),
    CONSTRAINT FK_ATENDIMENTO_PRECEPTOR FOREIGN KEY (id_preceptor)
        REFERENCES PRECEPTOR(id_profissional)
);

-- 9. TABELA: PROCEDIMENTO
CREATE TABLE PROCEDIMENTO (
    id_procedimento INT AUTO_INCREMENT,
    codigo VARCHAR(20) NOT NULL,
    nome VARCHAR(100) NOT NULL,
    tempo_medio_minutos INT NOT NULL,
    nivel_risco VARCHAR(10) NOT NULL,
    CONSTRAINT PK_PROCEDIMENTO PRIMARY KEY (id_procedimento),
    CONSTRAINT UN_PROCEDIMENTO_CODIGO UNIQUE (codigo),
    CONSTRAINT CK_NIVEL_RISCO CHECK (nivel_risco IN ('baixo', 'médio', 'alto'))
);

-- 10. TABELA: PROCEDIMENTO_REALIZADO (Relacionamento N:M com PK Composta)
CREATE TABLE PROCEDIMENTO_REALIZADO (
    id_atendimento INT,
    id_procedimento INT,
    quantidade INT NOT NULL DEFAULT 1,
    tempo_real_minutos INT NOT NULL,
    observacao TEXT,
    is_faturado BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT PK_PROCEDIMENTO_REALIZADO PRIMARY KEY (id_atendimento, id_procedimento),
    CONSTRAINT FK_PROC_REALIZADO_ATENDIMENTO FOREIGN KEY (id_atendimento) 
        REFERENCES ATENDIMENTO(id_atendimento) ON DELETE CASCADE,
    CONSTRAINT FK_PROC_REALIZADO_PROCEDIMENTO FOREIGN KEY (id_procedimento)
        REFERENCES PROCEDIMENTO(id_procedimento)
);

-- 11. TABELA: ESCALA
CREATE TABLE ESCALA (
    id_escala INT AUTO_INCREMENT,
    id_unidade INT NOT NULL,
    dia_semana VARCHAR(15) NOT NULL,
    mes_referencia INT NOT NULL,
    ano_referencia INT NOT NULL,
    turno VARCHAR(15) NOT NULL,
    id_residente INT NOT NULL,
    id_preceptor INT NOT NULL,
    CONSTRAINT PK_ESCALA PRIMARY KEY (id_escala),
    CONSTRAINT FK_ESCALA_UNIDADE FOREIGN KEY (id_unidade)
        REFERENCES UNIDADE(id_unidade),
    CONSTRAINT FK_ESCALA_RESIDENTE FOREIGN KEY (id_residente)
        REFERENCES RESIDENTE(id_profissional),
    CONSTRAINT FK_ESCALA_PRECEPTOR FOREIGN KEY (id_preceptor)
        REFERENCES PRECEPTOR(id_profissional),
    CONSTRAINT UN_ESCALA_CONFLITO UNIQUE (id_unidade, dia_semana, turno, id_residente, mes_referencia, ano_referencia),
    CONSTRAINT CK_DIA_SEMANA CHECK (dia_semana IN ('segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo')),
    CONSTRAINT CK_TURNO CHECK (turno IN ('manhã', 'tarde', 'noite')),
    CONSTRAINT CK_MES_REFERENCIA CHECK (mes_referencia BETWEEN 1 AND 12),
    CONSTRAINT CK_ANO_REFERENCIA CHECK (ano_referencia >= 2000)
);
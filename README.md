# 🏥 Sistema de Gestão Hospitalar — Dra. Yuska Maritan Brito

Instruções de instalação, execução e carga do banco de dados.

Stack: **MySQL 8**, **Python 3.12 + FastAPI** com **SQLAlchemy 2.0 (ORM)** e frontend
servido por **Nginx**, tudo orquestrado por **Docker Compose**.

---

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) 20.10+
- [Docker Compose](https://docs.docker.com/compose/) v2+

## 1. Configurar o `.env`

As credenciais do banco ficam em `backend/.env`, que **não é versionado**. Use o modelo
`backend/.env.example` como base:

```bash
cp backend/.env.example backend/.env
```

Edite `backend/.env` e troque as senhas (`MYSQL_ROOT_PASSWORD` e `MYSQL_PASSWORD`). Os
demais valores podem permanecer como no exemplo — `MYSQL_HOST=hospital_mysql` é o nome do
contêiner do MySQL e é assim que o backend o encontra na rede do Docker.

> 💡 `SQL_ECHO=true` faz a SQLAlchemy imprimir no log do contêiner todo SQL que ela gera
> (`docker compose logs -f backend`). Útil para ver as consultas da ORM — inclusive as
> consultas extras disparadas pelo *lazy loading*.

## 2. Subir os contêineres

Na raiz do projeto:

```bash
docker compose up -d --build
```

Sobem três serviços: `db` (MySQL, porta 3306), `backend` (API, porta 8000) e `frontend`
(Nginx, porta 8080).

> ⏳ Na primeira execução o MySQL leva alguns segundos para ficar pronto. Aguarde a
> mensagem `ready for connections` (via `docker compose logs -f db`) antes do passo 3.

## 3. Carregar os scripts do banco

O MySQL sobe com o banco **vazio**. Carregue nesta ordem: o **schema** (criação das
tabelas), os **dados de teste**, as **stored procedures**, os **triggers** e as **views**.
Use a mesma senha definida em `MYSQL_PASSWORD`.

> 🔴 **`--default-character-set=utf8mb4` não é opcional.** O cliente `mysql` da imagem
> assume `latin1`, e os três scripts contêm acentos — sem a flag os bytes UTF-8 são
> reinterpretados e gravados duplo-codificados. Isso corrompe silenciosamente os nomes, os
> `CHECK` de `ESCALA` e os literais dentro das procedures (`'manhã'` viraria `'manhÃ£'`, e
> `sp_reajustar_escala` passaria a recusar todo turno válido).

**Linux / macOS / Git Bash:**

```bash
CARGA="docker exec -i hospital_mysql mysql --default-character-set=utf8mb4 -u hospital_user -p'SUA_SENHA' hospital_db"
$CARGA < database/schema.sql
$CARGA < database/mock_data.sql
$CARGA < database/procedures.sql
$CARGA < database/triggers.sql
$CARGA < database/views.sql
```

**Windows PowerShell** (não suporta o operador `<`):

```powershell
$carga = { docker exec -i hospital_mysql mysql --default-character-set=utf8mb4 -u hospital_user -p'SUA_SENHA' hospital_db }
Get-Content database/schema.sql     -Encoding UTF8 | & $carga
Get-Content database/mock_data.sql  -Encoding UTF8 | & $carga
Get-Content database/procedures.sql -Encoding UTF8 | & $carga
Get-Content database/triggers.sql   -Encoding UTF8 | & $carga
Get-Content database/views.sql      -Encoding UTF8 | & $carga
```

> ⚠️ Carregue sempre por `stdin`, como acima. Passar texto acentuado em `mysql -e "..."`
> não funciona no Windows: o argumento é reconvertido para a codepage ANSI antes de chegar
> ao contêiner e os acentos são corrompidos no caminho.

`procedures.sql`, `triggers.sql` e `views.sql` são idempotentes (cada objeto tem seu
`DROP ... IF EXISTS`), então podem ser recarregados sozinhos sempre que forem alterados.

> 📌 `triggers.sql` precisa vir **depois** de `schema.sql`, de onde vêm a tabela
> `AUDITORIA_ATENDIMENTO` e a coluna `PROCEDIMENTO.media_tempo_procedimento`. Rodá-lo
> depois de `mock_data.sql` também é intencional: no fim do arquivo há um `UPDATE` de
> *backfill* que calcula a média inicial dos dados já carregados — triggers só valem para
> o que acontece depois deles.
>
> 🔑 Criar trigger com *binary logging* ligado (o default do MySQL 8) exigiria o
> privilégio `SUPER`, de instância, que `hospital_user` não tem. Por isso o serviço `db`
> do `docker-compose.yml` sobe com `--log-bin-trust-function-creators=1`. Se você já
> tinha os contêineres de pé antes desta mudança, rode `docker compose up -d db` para
> recriar o contêiner do banco (os dados ficam no volume, não são perdidos).

Conferir se os acentos foram gravados corretamente (deve sair `manhã`, não `manhÃ£`):

```bash
docker exec -it hospital_mysql mysql --default-character-set=utf8mb4 -u hospital_user -p'SUA_SENHA' hospital_db -e "SELECT DISTINCT turno FROM ESCALA;"
```

Conferir a carga:

```bash
docker exec -it hospital_mysql mysql -u hospital_user -p'SUA_SENHA' hospital_db -e "SHOW TABLES; SELECT COUNT(*) FROM PESSOA;"
```

## 4. Acessar

- 🖥️ Painel web: <http://localhost:8080>
- 📚 Documentação da API (Swagger): <http://localhost:8000/docs>

---

### Reiniciar do zero (apaga os dados)

```bash
docker compose down -v
docker compose up -d --build
# repita o passo 3 para recarregar os scripts
```

### Aplicar os objetos dos triggers num banco já carregado

`schema.sql` é só `CREATE TABLE`, então não pode ser recarregado sobre um banco que já
tem dados. Para ganhar a tabela e a coluna que `triggers.sql` exige **sem** reiniciar do
zero, rode estes dois comandos uma única vez e depois carregue `triggers.sql`:

```sql
ALTER TABLE PROCEDIMENTO
    ADD COLUMN media_tempo_procedimento DECIMAL(7,2) AFTER tempo_medio_minutos;

CREATE TABLE AUDITORIA_ATENDIMENTO (
    id_auditoria INT AUTO_INCREMENT,
    id_atendimento INT NOT NULL,
    operacao VARCHAR(10) NOT NULL,
    usuario VARCHAR(100) NOT NULL,
    data_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dados_antigos JSON,
    dados_novos JSON,
    CONSTRAINT PK_AUDITORIA_ATENDIMENTO PRIMARY KEY (id_auditoria),
    CONSTRAINT CK_AUDITORIA_OPERACAO CHECK (operacao IN ('INSERT', 'UPDATE', 'DELETE')),
    INDEX IX_AUDITORIA_ATENDIMENTO (id_atendimento)
);
```

### Aplicar os objetos das views num banco já carregado

Mesma situação: `views.sql` depende da tabela `INTERNACAO`, que entrou no `schema.sql`
junto com as views. Num banco já populado, crie a tabela e carregue as internações de
teste antes de rodar `views.sql`:

```sql
CREATE TABLE INTERNACAO (
    id_internacao INT AUTO_INCREMENT,
    id_paciente INT NOT NULL,
    id_unidade INT NOT NULL,
    data_hora_entrada DATETIME NOT NULL,
    data_hora_saida DATETIME,
    leito VARCHAR(10),
    motivo VARCHAR(255),
    CONSTRAINT PK_INTERNACAO PRIMARY KEY (id_internacao),
    CONSTRAINT FK_INTERNACAO_PACIENTE FOREIGN KEY (id_paciente)
        REFERENCES PACIENTE(id_pessoa) ON DELETE CASCADE,
    CONSTRAINT FK_INTERNACAO_UNIDADE FOREIGN KEY (id_unidade)
        REFERENCES UNIDADE(id_unidade),
    CONSTRAINT CK_INTERNACAO_PERIODO
        CHECK (data_hora_saida IS NULL OR data_hora_saida >= data_hora_entrada),
    INDEX IX_INTERNACAO_PACIENTE (id_paciente, data_hora_entrada)
);
```

Depois copie o bloco `INSERT INTO INTERNACAO (...)` do fim de `mock_data.sql` e aplique
também este `UPDATE`, que encerra a supervisão do preceptor 12 — é ele que dá à
`vw_residentes_sem_supervisor` um caso do motivo "sem supervisão ativa":

```sql
UPDATE HISTORICO_PROFISSIONAL
   SET data_fim = '2026-06-30'
 WHERE id_profissional = 12 AND papel = 'preceptor' AND data_fim IS NULL;
```

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
tabelas), os **dados de teste** e as **stored procedures**. Use a mesma senha definida em
`MYSQL_PASSWORD`.

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
```

**Windows PowerShell** (não suporta o operador `<`):

```powershell
$carga = { docker exec -i hospital_mysql mysql --default-character-set=utf8mb4 -u hospital_user -p'SUA_SENHA' hospital_db }
Get-Content database/schema.sql     -Encoding UTF8 | & $carga
Get-Content database/mock_data.sql  -Encoding UTF8 | & $carga
Get-Content database/procedures.sql -Encoding UTF8 | & $carga
```

> ⚠️ Carregue sempre por `stdin`, como acima. Passar texto acentuado em `mysql -e "..."`
> não funciona no Windows: o argumento é reconvertido para a codepage ANSI antes de chegar
> ao contêiner e os acentos são corrompidos no caminho.

`procedures.sql` é idempotente (cada procedure tem `DROP PROCEDURE IF EXISTS`), então pode
ser recarregado sozinho sempre que for alterado.

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

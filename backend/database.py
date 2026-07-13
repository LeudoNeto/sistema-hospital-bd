import os

import pymysql
from dotenv import load_dotenv

load_dotenv()


def get_conexao():
    """Cria e retorna uma nova conexão pymysql com o banco de dados.

    As credenciais são lidas das variáveis de ambiente definidas no .env.
    """
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )

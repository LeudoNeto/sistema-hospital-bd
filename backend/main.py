from fastapi import FastAPI

from controller import Controller

app = FastAPI(title="Sistema Hospitalar - API")

app.include_router(Controller().router)

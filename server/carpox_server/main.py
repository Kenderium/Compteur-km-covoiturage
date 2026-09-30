"""Application ASGI pour uvicorn : `uvicorn carpox_server.main:app`."""

from carpox_server.app import create_app

app = create_app()

"""Entrypoint Serverless para a Vercel (@vercel/python).

A Vercel procura uma instância ASGI chamada `app` em `api/index.py` e roteia `/api/*` para ela.
"""
from app.main import app

__all__ = ["app"]

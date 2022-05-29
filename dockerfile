FROM python:3.10.4-slim-buster

RUN apt-get update
RUN pip install aiohttp==3.8.1 sanic==22.3.2 psycopg2 pandas numpy sqlalchemy

EXPOSE 8000

ENTRYPOINT [ "python" "app.py" ]
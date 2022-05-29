FROM python:3.10.4-slim-buster

RUN apt-get update
RUN pip install sanic==22.3.2 psycopg2-binary==2.9.3 sqlalchemy==1.4.36 PyYAML==6.0

WORKDIR /app
COPY ./ /app/

EXPOSE 8000

ENTRYPOINT [ "python", "app.py" ]
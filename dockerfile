FROM python:3.10.4-slim-buster

RUN apt-get update
RUN pip install psycopg2-binary==2.9.3 sqlalchemy==1.4.36 PyYAML==6.0 fastapi==0.78.0 uvicorn==0.17.6

WORKDIR /app
COPY ./app/ /app/

EXPOSE 8000

ENTRYPOINT [ "python", "app.py" ]
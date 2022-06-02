FROM python:3.10.4-slim-buster

RUN apt-get update
RUN pip install psycopg2-binary==2.9.3 sqlalchemy==1.4.36 PyYAML==6.0 fastapi==0.78.0 uvicorn==0.17.6 PySocks==1.7.1 requests==2.27.1 lxml==4.8.0

WORKDIR /app
COPY ./app/ /app/

EXPOSE 8000

ENTRYPOINT [ "python", "app.py" ]
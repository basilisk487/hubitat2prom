FROM python:3.11-alpine

ARG HE_URI="myhubitatdevice"
ARG HE_ACCESS_TOKEN="my-access-token"

ENV HE_URI=$HE_URI
ENV HE_ACCESS_TOKEN=$HE_ACCESS_TOKEN
ENV PIP_BREAK_SYSTEM_PACKAGES 1

# RUN apk add --no-cache python3 py3-pip

RUN mkdir -p /app/config

COPY requirements.txt /app/requirements.txt
COPY app.py /app/app.py
COPY templates /app/templates

WORKDIR /app

RUN pip install -r requirements.txt

EXPOSE 5000

CMD ["uvicorn", "--host", "0.0.0.0", "--port", "5000", "--forwarded-allow-ips", "*", "app:app"]

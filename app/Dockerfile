FROM python:3.11-slim

LABEL maintainer="Federico Rormoser <joelrormoser@gmail.com>"
LABEL project="cloud-cicd-platform"

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

EXPOSE 5000

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "src/app.py"]
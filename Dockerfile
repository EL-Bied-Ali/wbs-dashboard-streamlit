# syntax=docker/dockerfile:1

FROM python:3.11-slim

# Empêche Python de buffer les logs (pratique en container)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dépendances système minimales (utile pour certains packages Python)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Installer les deps Python d'abord (meilleur cache Docker)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code ensuite
COPY . /app

# Streamlit écoute sur 8501
EXPOSE 8501

# Recommandé: écouter sur 0.0.0.0 dans Docker
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]

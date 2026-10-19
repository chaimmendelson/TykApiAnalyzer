FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Reproducible: exact versions from the lock file, then the package itself.
COPY requirements.lock pyproject.toml ./
COPY src ./src
COPY .streamlit ./.streamlit
RUN pip install -r requirements.lock && pip install --no-deps .

RUN useradd --create-home --uid 10001 tyk
USER tyk

# Configuration (MONGO_URI and friends) is supplied at runtime, never baked in.
EXPOSE 8501
CMD ["streamlit", "run", "/usr/local/lib/python3.12/site-packages/tyk_analyzer/app.py", \
     "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", \
     "--browser.gatherUsageStats=false"]

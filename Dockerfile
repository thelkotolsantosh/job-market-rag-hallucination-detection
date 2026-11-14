FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md requirements.txt ./
COPY src/ ./src/
RUN pip install --no-cache-dir -r requirements.txt
COPY data/raw/ ./data/raw/
COPY web/ ./web/
RUN python -m job_rag.ingest --data-dir data/raw --db data/processed/jobs.sqlite
EXPOSE 8000
CMD ["uvicorn", "job_rag.api:app", "--host", "0.0.0.0", "--port", "8000"]

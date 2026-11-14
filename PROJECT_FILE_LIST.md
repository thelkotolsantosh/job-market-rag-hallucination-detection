# File list and what each file does

This is the checklist I use before publishing the repository.

| Path | Purpose |
|---|---|
| `README.md` | Main explanation, setup, examples, metrics and demo steps |
| `FAQ.md` | Exactly 20 technical interview questions with plain-English answers |
| `PROJECT_FILE_LIST.md` | This file checklist |
| `requirements.txt` | Pinned direct Python packages and editable project install |
| `pyproject.toml` | Python packaging and pytest settings |
| `.gitignore` | Keep local environment, caches and generated SQLite database out of Git |
| `.env.example` | Optional app/model configuration (no secrets) |
| `.dockerignore` | Exclude unnecessary files from Docker build |
| `Dockerfile` | Build and run the API as a container |
| `LICENSE` | MIT license for the project code |
| `DATA_LICENSE_NOTICE.md` | Important reminder to check permission before posting CSVs |
| `data/raw/benefits.csv` | Uploaded benefit records |
| `data/raw/job_industries.csv` | Uploaded industry-ID records |
| `data/raw/job_skills.csv` | Uploaded skill-code records |
| `data/raw/salaries.csv` | Uploaded salary records |
| `data/processed/.gitkeep` | Keeps the processed-data folder in Git; SQLite is generated |
| `src/job_rag/__init__.py` | Package declaration and version |
| `src/job_rag/ingest.py` | Validate the four inputs, join them and build SQLite FTS5 indexes |
| `src/job_rag/store.py` | Exact job lookup and text retrieval |
| `src/job_rag/rag.py` | Route questions and apply grounded-answer rules |
| `src/job_rag/ollama_client.py` | Optional local LLM integration with structured claim validation |
| `src/job_rag/api.py` | FastAPI health, search, job details and answer endpoints |
| `src/job_rag/cli.py` | Ask questions from a terminal |
| `src/job_rag/evaluate.py` | Build benchmark questions and score structured claims |
| `src/job_rag/evaluate_manual.py` | Calculate rates from human-reviewed free-text claims |
| `web/index.html` | Small local browser demo |
| `tests/test_pipeline.py` | Automated checks for ingestion, answering, safety and API |
| `tests/fixtures/*.csv` | Four small synthetic datasets, suitable for public CI |
| `reports/metrics.json` | Measured benchmark counts and rates |
| `reports/metrics.md` | Human-readable measured results |
| `reports/benchmark_questions.csv` | Generated benchmark questions |
| `reports/benchmark_results.csv` | Each question, answer, citation and error count |
| `docs/architecture.md` | Design choices, limits and threats |
| `docs/architecture.svg` | Diagram shown in the README |
| `docs/data_dictionary.md` | Original columns and measured data counts |
| `docs/evaluation.md` | Precise metric definitions and interpretation |
| `docs/interview_walkthrough.md` | Short demo script and talking points |
| `docs/github_publish.md` | Git and GitHub publishing steps |
| `docs/manual_annotations_template.csv` | Human-labeling template for LLM answers |
| `scripts/setup_windows.ps1` | Windows setup shortcut |
| `.github/workflows/ci.yml` | Run tests automatically on GitHub commits |

The `data/processed/jobs.sqlite` file is **not** needed in GitHub. Everyone can rebuild it from their permitted copy of the CSVs with `python -m job_rag.ingest`.

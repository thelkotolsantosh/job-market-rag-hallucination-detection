# How to publish this project on GitHub

Follow these steps from the root project folder.

## 1. Check data rights

Before putting the repo online, read `DATA_LICENSE_NOTICE.md`. The original CSV files are included here because they were provided for this exercise; **their license has not been verified**. Check whether you have permission to share them. If you cannot verify rights, remove the four files from the public copy and keep the synthetic `tests/fixtures/` files. Do not upload confidential client or employer data.

## 2. Run it locally

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m job_rag.evaluate
```

Check `reports/metrics.md` to make sure the stated results are the results from your data. Keep the benchmark report in the repository so someone can inspect it.

## 3. Create an empty repo

Sign in to GitHub, select **New repository**, enter the name `job-market-rag-hallucination-guardrails`, choose **Public** only after checking the data rights, and create it **without** another README or .gitignore. Both files already exist here.

## 4. Upload from PowerShell

Install Git first if needed. Replace `YOUR_USERNAME` with your real GitHub username:

```powershell
git init
git add .
git status
git commit -m "Build source-grounded RAG and hallucination evaluation"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/job-market-rag-hallucination-guardrails.git
git push -u origin main
```

If Git asks who you are, use `git config --global user.name "Your Name"` and `git config --global user.email "you@example.com"` with your own details.

**Check `git status` before committing.** The generated SQLite file and local virtual environment should not be in the commit. Also make sure you did not accidentally include credentials or restricted data.

## 5. Make the repo clear to recruiters

- Add a short GitHub description: `Source-grounded RAG over job data with FastAPI, SQLite, hallucination metrics and guardrails`.
- Add topics like `rag`, `llm-evaluation`, `fastapi`, `sqlite`, `hallucination-detection`, `forward-deployed-engineering`.
- Pin the repository to your GitHub profile if you want it to appear first.
- Include a screenshot of the browser demo **after you run it**, or record a short walkthrough. Do not use a fake dashboard screenshot.
- Keep the `FAQ.md` and benchmark table visible so an interviewer can see the technical reasoning.

## 6. Keep the project honest

The included numbers come from a deterministic benchmark. They are not proof that an Ollama model never hallucinates. If you later run Ollama, commit its evaluated results separately with the model name, settings, date, input questions and method.

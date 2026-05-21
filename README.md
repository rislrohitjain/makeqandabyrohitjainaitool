---
title: Antigravity Q&A Generator
emoji: 🚀
colorFrom: indigo
colorTo: purple
sdk: streamlit
app_file: app/main.py
pinned: false
---

# Antigravity 2.0 Q&A Generator

This project is a local, open-source Q&A pair generator. It allows you to parse PDF, DOCX, and TXT files, process them using local/open-source pipelines, and generate high-quality questions and answers.

## Project Structure

```
D:\projects\python\makeqandabyrohitjainaitool\
├── .gitignore
├── requirements.txt
├── README.md
├── run.bat
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── pipeline.py
│   ├── agents.py
│   └── utils.py
└── storage/
    └── outputs/
```

## Setup & Running

1. Create a Python virtual environment:
   ```cmd
   python -m venv .venv
   ```
2. Activate the virtual environment:
   ```cmd
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
4. Run the Streamlit web application:
   ```cmd
   run.bat
   ```
   Or manually:
   ```cmd
   streamlit run app/main.py
   ```

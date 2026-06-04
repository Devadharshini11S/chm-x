# CHM-X: Criminal Hash Match

**CHM-X** is a forensic similarity detection framework for identifying duplicate and similar files across evidence datasets using **fuzzy hashing (ssdeep)**. It provides both an interactive CLI (`chmx>`) and a FastAPI REST API for digital forensics workflows, malware analysis, and evidence correlation.

> ⚡ **CHM-X** – Cyber Forensics • Similarity Detection
> **Author:** Devadharshini
> **Focus:** Digital Forensics / Security Research / Evidence Analysis

---

## Features

* 📁 Recursive directory scanning for source and evidence datasets
* 🔐 SHA-256 cryptographic hashing for exact file matching
* 🎯 Fuzzy hashing with ssdeep for similarity detection
* 🔍 Similarity scoring with configurable thresholds
* 📊 Structured JSON output with metadata
* 🖥️ Interactive CLI (`chmx>`)
* 🌐 REST API integration using FastAPI

---

# Installation

## Prerequisites

* Python 3.10+
* Ubuntu/Linux environment
* pip
* virtualenv

## Setup

```bash
# Clone repository
git clone https://github.com/Devadharshini11S/chm-x.git

cd chm-x/backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

# Usage

## Start Backend API

```bash
cd ~/chm-x/backend

source venv/bin/activate

uvicorn app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger Docs:

```text
http://127.0.0.1:8000/docs
```

---

## Start CLI

```bash
cd ~/chm-x/backend

source venv/bin/activate

python3 chm_cli.py
```

CLI prompt:

```text
chmx>
```

---

## Example Scan

```text
chmx> set source /home/user/chm_source

chmx> set target /home/user/chm_target

chmx> run

chmx> show_results
```

Additional Commands:

```text
show_hash

show_metadata

show_similar

compare

help

exit
```

---

# Tech Stack

* Backend: FastAPI
* Language: Python
* Hashing: SHA-256 + ssdeep
* CLI Framework: cmd2
* API Server: Uvicorn

---

# Project Structure

```text
chm-x/
│
├── backend/
│   ├── app/
│   │   └── main.py
│   │
│   ├── chm_cli.py
│   ├── requirements.txt
│   └── .gitignore
│
└── README.md
```

---

# License

MIT License

---

# Author

Devadharshini

GitHub:

https://github.com/Devadharshini11S/chm-x

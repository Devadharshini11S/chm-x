# CHM-X: Criminal Hash Match

**CHM-X** is an enterprise-grade forensic tool for detecting similar and duplicate files across evidence sets using **fuzzy hashing (ssdeep)**. It provides both an interactive CLI (`chmx>`) and a FastAPI REST API, designed for digital forensics, malware analysis, and criminal evidence correlation.

> ⚡ **CHM-X** – Cyber • Hack • Modify  
> **Author**: Devadharshini  
> **Version**: 1.1  
> **Mode**: Red Team / Forensics / Monitoring

---

## Features

- 📁 **Directory scanning**: Recursively scan source (known) and target (evidence) folders  
- 🔐 **Cryptographic hashing**: SHA-256 for exact file matching  
- 🎯 **Fuzzy hashing**: ssdeep for similarity detection (even with slightly modified files)  
- 🔍 **Similarity scoring**: 0–100% match scores with configurable threshold (default: 70)  
- 📊 **Structured output**: JSON results with file metadata (path, MIME type, kind)  
- 🖥️ **Interactive CLI**: Professional `chmx>` shell with commands like `run`, `show_results`, `show_similar`  
- 🌐 **REST API**: Easily integrate with other forensic tools or web dashboards  

---

## Installation

### Prerequisites

- Python 3.10+  
- Ubuntu 22.04+ (or compatible Linux)  
- pip and virtualenv  

### Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/chm-x.git
cd chm-x/backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn ssdeep requests

# Create test folders (optional)
mkdir -p /home/<your_user>/chm_source
mkdir -p /home/<your_user>/chm_target
echo "test one" > /home/<your_user>/chm_source/a.txt
echo "test one"   > /home/<your_user>/chm_target/b.txt
```

---

## Usage

### 1. Start the FastAPI Backend

From `~/chm-x/backend` with venv active:

```bash
uvicorn app.main:app --reload
```

- Server runs at: `http://127.0.0.1:8000`  
- Swagger docs: `http://127.0.0.1:8000/docs`  

If your FastAPI app is in `main.py` instead of `app/main.py`, use:

```bash
uvicorn main:app --reload
```

### 2. Start the Interactive CLI (CHM-X Shell)

Open a **new terminal** and run:

```bash
cd ~/chm-x/backend
source venv/bin/activate
python3 chm_cli.py
```

You will see:

```text
chmx>
```

### 3. Run a Forensic Scan (CLI)

Inside the CLI:

```text
chmx> set source /home/<your_user>/chm_source
chmx> set target /home/<your_user>/chm_target

chmx> run
chmx> show_results
```

Other CLI commands:

```text
chmx> show_hash      # show SHA-256 and fuzzy hashes
chmx> show_metadata  # show file info (path, MIME, kind)
chmx> show_similar   # show high-similarity matches
chmx> compare        # compare two specific files
chmx> help           # show all commands
chmx> exit           # exit CLI
```

### 4. (Optional) Use the REST API with curl

Scan a folder:

```bash
curl -s -X POST "http://127.0.0.1:8000/api/scan" \
  -H "Content-Type: application/json" \
  -d '{"root_path": "/home/devadharshini/Documents"}' \
  | python3 -m json.tool
```

Upload and scan a file:

```bash
curl -s -X POST "http://127.0.0.1:8000/api/upload-scan" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@/home/devadharshini/Documents/ssdeepdemo.py" \
  | python3 -m json.tool
```

---

## Output Format

The tool returns structured JSON with summaries and match details:

```json
{
  "ok": true,
  "summary": {
    "source_files": 1,
    "target_files": 1,
    "match_count": 1
  },
  "matches": [
    {
      "fuzzy_score": 100,
      "similarity_pct": 100.0,
      "source": {
        "path": "/home/user/chm_source/a.txt",
        "sha256": "0b5a7d...",
        "fuzzy": "3:Hnn:Hn",
        "mime": "text/plain",
        "kind": "text"
      },
      "target": {
        "path": "/home/user/chm_target/b.txt",
        "sha256": "0b5a7d...",
        "fuzzy": "3:Hnn:Hn",
        "mime": "text/plain",
        "kind": "text"
      }
    }
  ]
}
```

---

## Forensic Workflow

1. **Source**: Known evidence set (e.g., known malware, contraband, prior case files)  
2. **Target**: New seized evidence (e.g., disk image folder, user profile, extracted data)  
3. Run the scan to find files that are identical or highly similar  
4. Review matches with `show_results`, `show_similar`, `show_hash`, `show_metadata`  
5. Extract hashes and metadata for formal reporting and chain-of-custody documentation  

---

## Tech Stack

- **Backend**: Python, FastAPI, Uvicorn  
- **Hashing**: ssdeep (fuzzy hashing), SHA-256 (cryptographic)  
- **CLI**: Python `cmd2`  
- **HTTP Client**: `requests`  
- **OS**: Ubuntu/Linux  

---

## Project Structure
chm-x/
├── backend/
│ ├── app/
│ │ └── main.py # FastAPI backend (API endpoints)
│ ├── chm_cli.py # Interactive CLI (chmx> shell)
│ ├── venv/ # Virtual environment (gitignored)
│ ├── .gitignore
│ └── requirements.txt
└── README.md

text

---

## Contributing

Feel free to open issues or pull requests for:
- Additional file format support  
- Improved similarity algorithms  
- Web dashboard UI  
- Docker containerization  
- Enhanced forensic reporting  

---

## License

MIT License

---

## Author

**Devadharshini**  
Criminal Hash Match Tool – Forensic Similarity Detection  
GitHub: https://github.com/Devadharshini11S/chm-x

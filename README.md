![License](https://img.shields.io/badge/license-MIT-blue.svg)
# GitIngest 🔍

Turn any GitHub repository into a prompt-friendly text ingest for LLMs. 

[Live demo](https://gitingest.com/)

## 🚀 Features

- **One-Click Analysis**: Simply paste a GitHub repository URL and get instant results
- **Smart Formatting**: Optimized output format for LLM prompts
- **Statistics about**: :
  - File and directory structure
  - Token counts and statistics
  - Repository summary
- **Web Interface**: Clean, responsive UI built with Tailwind CSS

## 🛠️ Tech Stack

- FastAPI - Backend framework
- [apianalytics.dev](https://www.apianalytics.dev/) - Usage tracking

## 📦 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/gitingest.git
cd gitingest
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
cd src
uvicorn main:app --reload
```

The application will be available at `http://localhost:8000`


## 🔒 WIP
- Feedback/suggestions: Please open a github Issue or mail me: romain@coderamp.io
- Repository cloning is limited to GitHub repositories only
- Processing timeouts are implemented (10s for cloning, 15s for processing)
- Request size limits are in place to prevent abuse


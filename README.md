# DCO: Dual-Core Orchestrator

**Version:** 2.1.0 ("Mnemosyne" Release)

DCO is a local-first, agentic pair-programming environment that orchestrates two expert AI agents—**Claude Code** and **OpenAI Codex**—to work as Peer Engineers in a "Twin-Turbo" workflow.

## Features

- **Twin-Terminal Interface:** View real-time agent output side-by-side.
- **Smart Memory Core:** Persists context and lessons learned in `.brain/`.
- **Huddle Protocol:** Agents coordinate via `HUDDLE.md` before coding.
- **Local Orchestration:** Powered by FastAPI and Python subprocesses.

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Git**

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repo-url>
    cd dco
    ```

2.  **Install Backend Dependencies:**
    ```bash
    cd backend
    pip install -r requirements.txt
    cd ..
    ```

3.  **Install Frontend Dependencies:**
    ```bash
    cd frontend
    npm install
    cd ..
    ```

## How to Start

Run the centralized startup script to launch both the orchestrator and the interface:

```bash
./start_dco.sh
```

- **Frontend:** [http://localhost:3000](http://localhost:3000)
- **Backend:** [http://localhost:8000](http://localhost:8000)

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed structural diagrams and workflow rules.
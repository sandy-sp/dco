# DCO: Dual-Core Orchestrator

**Version:** 1.0.0 (Release)

DCO is a local-first, agentic pair-programming environment that orchestrates two expert AI agents—**Claude Code** and **OpenAI Codex**—to work as Peer Engineers in a "Twin-Turbo" workflow.

## Features

- **Twin-Terminal Interface:** View real-time agent output side-by-side.
- **Smart Memory Core:** Persists context and lessons learned in `.brain/` (ChromaDB).
- **Huddle Protocol:** Agents coordinate via `HUDDLE.md` before coding.
- **Local Orchestration:** Powered by FastAPI and Python subprocesses.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repo-url>
    cd dco
    ```

2.  **Run the Launch Script:**
    ```bash
    ./start_dco.sh
    ```
    *The script automatically installs Python dependencies (in a `venv`) and Node modules.*

## Usage

- **Mission Control:** [http://localhost:3000](http://localhost:3000)
- **Backend API:** [http://localhost:8000](http://localhost:8000)

Enter a task in the **Chat Console** (e.g., "Refactor the Auth logic") to start a Twin-Turbo Sprint.

### Configuration

To enable **Real AI Execution** (default is Simulation Mode):
1.  Open `backend/scrum.py`.
2.  Set `ENABLE_REAL_AGENTS = True`.
3.  Ensure `claude` and `codex` CLIs are authenticated in your terminal.
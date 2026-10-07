# Local Development Runbook

1. Create and activate a virtual environment.
2. Install `pip install -e .[dev]`.
3. Run `pytest`.
4. Start `uvicorn apps.control_plane_api.main:app --reload --port 8001`.
5. Start `uvicorn apps.runtime_api.main:app --reload --port 8002`.

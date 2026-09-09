"""Run from the repository root with: python -m backend1.server."""

import uvicorn

from .app import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=app.state.settings.port)

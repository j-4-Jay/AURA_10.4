import sys
import asyncio
from pathlib import Path

# THE FIX: Inject the root AURA directory into sys.path so it can find the 'backend' folder
BASE_DIR = str(Path(__file__).parent.parent.resolve())
sys.path.insert(0, BASE_DIR)

# [AURA-STRICT-PROTOCOL] Force the Event Loop BEFORE Uvicorn starts
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn
from backend.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_config=None)
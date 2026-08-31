"""
Launcher script for Indy Robot Web HMI on port 9777.
"""

import uvicorn
from src.hmi.config import HMI_HOST, HMI_PORT


def main():
    print("=" * 60)
    print("      Neuromeka Indy Robot Web HMI Dashboard")
    print(f"      Server running at: http://localhost:{HMI_PORT}")
    print("=" * 60)

    uvicorn.run(
        "src.hmi.server:app",
        host=HMI_HOST,
        port=HMI_PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()

import argparse
import json
import logging
import time
from pathlib import Path

from workcell.config import Settings, load_settings
from workcell.models import CellError, State


def wait_idle(cell, timeout=20):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        snapshot = cell.snapshot()
        if snapshot["initialized"] and not snapshot["pending"]:
            return snapshot
        if snapshot["fault"]:
            raise CellError(snapshot["fault"])
        time.sleep(0.02)
    raise CellError("Controller command timed out")


def demo(cycles: int):
    from workcell.app import build_controller

    cell = build_controller(Settings(database=":memory:"))
    cell.start()
    try:
        wait_idle(cell)
        cell.submit("enable")
        wait_idle(cell)
        for _ in range(cycles):
            cell.submit("start")
            result = wait_idle(cell)
            if result["fault"]:
                raise CellError(result["fault"])
            if result["state"] == State.WAITING_FOR_PALLET_CHANGE:
                break
        print(
            json.dumps(
                {
                    "state": cell.snapshot()["state"],
                    "slots": cell.store.slots(),
                    "cycles": cell.store.history()["cycles"],
                },
                indent=2,
            )
        )
    finally:
        cell.close()


def main():
    parser = argparse.ArgumentParser(description="Neuromeka workcell; simulation by default")
    parser.add_argument(
        "--config", type=Path, help="TOML configuration (default: built-in simulation)"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    server = commands.add_parser("serve", help="Start the local operator dashboard")
    server.add_argument("--port", type=int, default=9000)
    server.add_argument("--mode", choices=["simulation", "observe", "automatic"])
    server.add_argument("--allow-motion", action="store_true")
    commands.add_parser("validate", help="Validate configuration without connecting to devices")
    demonstration = commands.add_parser(
        "demo", help="Run complete cycles using only simulated devices"
    )
    demonstration.add_argument("--cycles", type=int, choices=range(1, 9), default=1)
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    try:
        if args.command == "demo":
            demo(args.cycles)
            return
        settings = load_settings(args.config)
        if args.command == "validate":
            print(
                f"Valid configuration: mode={settings.mode}, {settings.recipe.capacity} pallet slots, hash={settings.fingerprint[:12]}"
            )
            return
        if args.mode and args.mode != settings.mode:
            data = settings.model_dump()
            data["mode"] = args.mode
            data["database"] = str(Path(settings.database).with_name(f"{args.mode}.sqlite3"))
            settings = Settings.model_validate(data)
        if settings.mode == "automatic" and not (
            args.allow_motion and settings.commissioned and settings.commissioning_reference.strip()
        ):
            raise CellError(
                "Automatic mode requires --allow-motion and a recorded commissioning approval in configuration"
            )
        import uvicorn

        from workcell.app import create_app

        print(f"Workcell mode: {settings.mode.upper()} | http://127.0.0.1:{args.port}")
        uvicorn.run(
            create_app(settings, args.allow_motion),
            host="127.0.0.1",
            port=args.port,
            workers=1,
            log_level="info",
        )
    except (CellError, ValueError, OSError) as exc:
        parser.exit(2, f"workcell: {exc}\n")


if __name__ == "__main__":
    main()

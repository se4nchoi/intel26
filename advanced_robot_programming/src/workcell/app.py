import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from workcell.config import Settings
from workcell.controller import Controller
from workcell.models import CellError, Pose
from workcell.storage import Store


def build_controller(settings: Settings, allow_motion: bool = False):
    if settings.mode == "automatic" and not (
        allow_motion and settings.commissioned and settings.commissioning_reference.strip()
    ):
        raise CellError(
            "Automatic mode requires --allow-motion, commissioned=true, and a commissioning_reference"
        )
    store = Store(settings.database, settings.recipe.capacity, settings.fingerprint)
    try:
        if settings.mode == "simulation":
            from workcell.simulation import Scenario, SimCamera, SimPLC, SimRobot

            world = Scenario()
            robot = SimRobot(world, Pose(settings.recipe.pick).at_z(settings.recipe.transfer_z_mm))
            return Controller(settings, store, robot, SimPLC(world), SimCamera(world), world)
        from workcell.hardware import MCPLC, IndyRobot
        from workcell.vision import RealSenseCamera

        writable = settings.mode == "automatic"
        return Controller(
            settings,
            store,
            IndyRobot(settings.robot, settings.workspace, writable),
            MCPLC(settings.plc, writable),
            RealSenseCamera(settings.vision),
        )
    except Exception:
        store.close()
        raise


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["enable", "disable", "start", "stop", "reset", "reconcile", "replace_pallet"]
    note: str = Field("", max_length=500)
    inspected: bool = False
    slot: int | None = Field(None, ge=0)
    occupied: bool | None = None


class ScenarioCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    part: Literal["red_cube", "blue_cylinder", "none"] | None = None
    fault: (
        Literal[
            "none",
            "robot_disconnect",
            "plc_disconnect",
            "camera_disconnect",
            "motion_failure",
            "grip_failure",
            "release_failure",
            "stale_detection",
        ]
        | None
    ) = None
    request_id: int | None = Field(None, ge=0, le=32767)
    estop: bool | None = None
    permit: bool | None = None


def create_app(
    settings: Settings | None = None,
    allow_motion: bool = False,
    controller: Controller | None = None,
):
    settings = settings or Settings()
    token = secrets.token_urlsafe(32)

    @asynccontextmanager
    async def lifespan(app):
        cell = controller or build_controller(settings, allow_motion)
        app.state.cell = cell
        cell.start()
        try:
            yield
        finally:
            cell.close()

    app = FastAPI(title="Workcell", lifespan=lifespan)
    app.state.token = token
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
    )
    assets = Path(__file__).parent / "web"
    app.mount("/static", StaticFiles(directory=assets), name="static")

    def cell(request: Request):
        return request.app.state.cell

    def authorize(request: Request):
        supplied = request.headers.get("X-Workcell-Token", "")
        if not secrets.compare_digest(supplied, token):
            raise HTTPException(403, "Missing or invalid workcell command token")

    @app.get("/", response_class=HTMLResponse)
    def index():
        return HTMLResponse(
            (assets / "index.html").read_text(encoding="utf-8").replace("__TOKEN__", token),
            headers={"Cache-Control": "no-store", "X-Frame-Options": "DENY"},
        )

    @app.get("/api/status")
    def status(c: Controller = Depends(cell)):
        return c.snapshot()

    @app.get("/api/history")
    def history(c: Controller = Depends(cell)):
        return c.store.history()

    @app.get("/api/frame")
    def frame(c: Controller = Depends(cell)):
        try:
            # Encode the camera's cached frame, independently of the motion worker.
            # RealSense acquisition remains exclusively owned by its capture thread.
            data = c.camera.jpeg()
        except Exception as exc:
            raise HTTPException(503, str(exc)) from exc
        if data is None:
            raise HTTPException(503, "No current camera frame")
        return Response(data, media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    @app.post("/api/commands", status_code=202, dependencies=[Depends(authorize)])
    def command(body: Command, c: Controller = Depends(cell)):
        if body.action == "stop":
            c.request_stop()
            return {"status": "requested", "message": "Controlled stop requested"}
        payload = {}
        if body.action in {"reset", "replace_pallet", "reconcile"}:
            if not body.inspected or not body.note.strip():
                raise HTTPException(422, "Confirm physical inspection and record a recovery note")
            payload["note"] = body.note.strip()
        if body.action == "reconcile":
            if body.slot is None or body.occupied is None:
                raise HTTPException(422, "A slot and its observed occupancy are required")
            payload.update(slot=body.slot, occupied=body.occupied)
        try:
            identifier = c.submit(body.action, **payload)
        except CellError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"status": "accepted", "command_id": identifier}

    @app.post("/api/simulation", status_code=202, dependencies=[Depends(authorize)])
    def simulation(body: ScenarioCommand, c: Controller = Depends(cell)):
        if c.scenario is None:
            raise HTTPException(409, "Simulation controls are unavailable in hardware modes")
        try:
            identifier = c.submit("scenario", **body.model_dump(exclude_none=True))
        except CellError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"status": "accepted", "command_id": identifier}

    return app

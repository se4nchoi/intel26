import logging
import queue
import threading
import time
import uuid
from dataclasses import asdict

from workcell.config import Settings
from workcell.models import CellError, Pose, State
from workcell.storage import Store

log = logging.getLogger(__name__)
IDLE_STATES = {State.DISABLED, State.READY, State.FAULT, State.WAITING_FOR_PALLET_CHANGE}


class Controller:
    """One worker owns all robot/PLC calls. HTTP threads only enqueue requests.

    The stop event is checked between operations and during bounded adapter waits.
    This is an operational controlled stop, not a hardware emergency stop.
    """

    def __init__(self, settings: Settings, store: Store, robot, plc, camera, scenario=None):
        self.settings, self.store = settings, store
        self.robot, self.plc, self.camera = robot, plc, camera
        self.scenario = scenario
        self.lock = threading.RLock()
        self.commands = queue.Queue(maxsize=1)
        self.shutdown_event = threading.Event()
        self.stop_event = threading.Event()
        self.started = threading.Event()
        self.thread = None
        self.state = State.FAULT if store.get_meta("fault") else State.DISABLED
        self.fault = store.get_meta("fault") or None
        self.enabled = False
        self.pending = False
        self.active_cycle = None
        self.active_slot = None
        self.request_id = 0
        self.last_request = int(store.get_meta("last_request") or 0)
        self.request_armed = False
        self.device_status = {}
        self.detection = None
        self.camera_error = None
        self.last_command = None
        self.initialized = False

    def start(self):
        self.thread = threading.Thread(target=self._run, name="cell-controller", daemon=True)
        self.thread.start()

    def submit(self, action: str, **payload) -> str:
        with self.lock:
            if self.shutdown_event.is_set() or not self.initialized:
                raise CellError("Controller is not initialized")
            if self.pending or self.state not in IDLE_STATES:
                raise CellError("Another operation is in progress")
            if action == "start" and self.state != State.READY:
                raise CellError("Enable the cell and resolve faults/full pallet before starting")
            if action in {"reconcile", "replace_pallet", "reset"} and self.enabled:
                raise CellError("Disable the cell before recovery or pallet changes")
            if self.settings.mode == "observe" and action in {"enable", "start"}:
                raise CellError("Observation mode does not permit cycles")
            identifier = uuid.uuid4().hex[:12]
            self.pending = True
            self.commands.put_nowait((identifier, action, payload))
            return identifier

    def request_stop(self):
        self.stop_event.set()

    def snapshot(self):
        with self.lock:
            detection = asdict(self.detection) if self.detection else None
            if detection:
                detection["age_s"] = max(0, time.monotonic() - detection.pop("captured_at"))
            return {
                "state": str(self.state),
                "mode": self.settings.mode,
                "enabled": self.enabled,
                "initialized": self.initialized,
                "pending": self.pending,
                "fault": self.fault,
                "active_cycle": self.active_cycle,
                "active_slot": self.active_slot,
                "devices": dict(self.device_status),
                "detection": detection,
                "camera_error": self.camera_error,
                "slots": self.store.slots(),
                "capacity": self.settings.recipe.capacity,
                "columns": self.settings.recipe.columns,
                "rows": self.settings.recipe.rows,
                "layers": self.settings.recipe.layers,
                "config_hash": self.settings.fingerprint[:12],
                "last_command": self.last_command,
                "simulation": self.scenario.values() if self.scenario else None,
            }

    def _state(self, state: State):
        with self.lock:
            self.state = state
        self.store.event("state", {"state": str(state), "cycle": self.active_cycle})
        self.plc.publish(self.request_id, state, self.active_slot)

    def _guard(self):
        if self.stop_event.is_set() or self.shutdown_event.is_set():
            raise CellError("Controlled stop requested; inspect the cell before recovery")
        inputs = self.plc.read()
        with self.lock:
            self.device_status["plc"] = {"connected": True, **asdict(inputs)}
        if not 0 <= time.monotonic() - inputs.captured_at <= self.settings.plc.heartbeat_timeout_s:
            raise CellError("PLC inputs are stale")
        if inputs.estop:
            raise CellError("PLC emergency-stop status is active")
        if not inputs.permit:
            raise CellError("PLC run permit is absent or heartbeat has not been verified")
        robot_status = self.robot.status()
        with self.lock:
            self.device_status["robot"] = {**robot_status, "captured_at": time.monotonic()}
        self.plc.publish(self.request_id, self.state, self.active_slot)

    def _fault(self, error):
        message = str(error)
        try:
            self.robot.stop()
        except Exception as stop_error:
            message += f"; controlled stop could not be confirmed: {stop_error}"
        with self.lock:
            self.enabled = False
            self.state = State.FAULT
            self.fault = message
            self.request_armed = False
        self.store.set_meta("fault", message)
        self.store.event("fault", {"message": message, "cycle": self.active_cycle})
        try:
            self.plc.publish(self.request_id, State.FAULT, self.active_slot)
        except Exception:
            log.exception("Could not publish fault to PLC")

    def _cycle(self, request_id: int = 0):
        cycle = None
        try:
            if not self.enabled or self.state != State.READY:
                raise CellError("Cell is not ready")
            self.request_id = request_id
            self._guard()
            if request_id == 0 and self.plc.read().request_id != 0:
                raise CellError("Clear the PLC cycle request before using manual start")
            self._state(State.INSPECTING)
            detection = self.camera.inspect()
            with self.lock:
                self.detection = detection
            if detection is None:
                raise CellError("No part detected; no motion was commanded")
            expected_source = "simulation" if self.settings.mode == "simulation" else "hardware"
            age = time.monotonic() - detection.captured_at
            if (
                detection.source != expected_source
                or not 0 <= age <= self.settings.vision.max_age_s
            ):
                raise CellError("Detection is stale or came from the wrong device mode")
            if not self.settings.vision.min_confidence <= detection.confidence <= 1:
                raise CellError("Detection confidence is below the recipe threshold")
            if detection.part not in {"red_cube", "blue_cylinder"}:
                raise CellError("Unsupported part; no route exists")
            self._state(State.PLANNING)
            cycle, slot = self.store.begin(
                detection.part, request_id, pallet=detection.part == "red_cube"
            )
            with self.lock:
                self.active_cycle, self.active_slot = cycle, slot
            recipe = self.settings.recipe
            pick = Pose(recipe.pick)
            place = recipe.slot_pose(slot) if slot is not None else Pose(recipe.magazine)
            current = Pose(tuple(self.robot.status()["pose"]))
            initial_lift = current.at_z(recipe.transfer_z_mm)
            pick_approach = pick.at_z(recipe.transfer_z_mm)
            place_approach = place.at_z(recipe.transfer_z_mm)
            # Validate every endpoint before the first actuation. This is not collision planning.
            for pose in (current, initial_lift, pick_approach, pick, place_approach, place):
                self.settings.workspace.check(pose)
            self._guard()
            self._state(State.PICKING)
            self.robot.verify_grip(False, self._guard)  # do not open a possibly loaded gripper
            self.robot.move(initial_lift, self._guard)
            self.robot.move(pick_approach, self._guard)
            self.robot.move(pick, self._guard)
            self.robot.grip(True, self._guard)
            self._state(State.VERIFYING_GRIP)
            self.robot.verify_grip(True, self._guard)
            self._state(State.PLACING)
            self.robot.move(pick_approach, self._guard)
            self.robot.move(place_approach, self._guard)
            self.robot.move(place, self._guard)
            self.robot.grip(False, self._guard)
            self._state(State.VERIFYING_RELEASE)
            self.robot.verify_grip(False, self._guard)
            self.store.placed(slot)
            self._state(State.RETREATING)
            self.robot.move(place_approach, self._guard)
            self._guard()
            # Commit physical completion before attempting the remote completion acknowledgment.
            self.store.finish(cycle)
            self._state(State.COMPLETE)
            if all(s["status"] == "OCCUPIED" for s in self.store.slots()):
                self.enabled = False
                self._state(State.WAITING_FOR_PALLET_CHANGE)
            else:
                self._state(State.READY)
        except Exception as exc:
            if cycle is not None:
                self.store.finish(cycle, str(exc))
            self._fault(exc)
        finally:
            with self.lock:
                self.active_cycle = None
                self.active_slot = None

    def _command(self, identifier, action, payload):
        try:
            self.store.event("command", {"id": identifier, "action": action, **payload})
            if action == "enable":
                if self.fault or self.state == State.FAULT:
                    raise CellError("Resolve and acknowledge the fault first")
                if any(s["status"] in {"UNKNOWN", "RESERVED"} for s in self.store.slots()):
                    raise CellError("Reconcile uncertain pallet slots")
                if all(s["status"] == "OCCUPIED" for s in self.store.slots()):
                    raise CellError("Replace the full pallet first")
                self.stop_event.clear()
                self._guard()
                self.robot.status()
                self.camera.inspect()
                self.enabled = True
                self.request_armed = False  # require PLC request=0 after each enable
                self._state(State.READY)
            elif action == "disable":
                self.enabled = False
                self.request_armed = False
                if not self.fault:
                    self._state(State.DISABLED)
            elif action == "start":
                self._cycle()
            elif action == "reset":
                self.stop_event.clear()
                self._guard()
                self.robot.status()
                if any(s["status"] in {"UNKNOWN", "RESERVED"} for s in self.store.slots()):
                    raise CellError("Reconcile every uncertain pallet slot first")
                if self.scenario is not None:
                    # The recorded inspection represents an operator clearing the simulated gripper.
                    self.robot.closed = False
                self.fault = None
                self.store.set_meta("fault", "")
                self._state(State.DISABLED)
            elif action == "reconcile":
                self.store.reconcile(payload["slot"], payload["occupied"], payload["note"])
            elif action == "replace_pallet":
                self.store.replace_pallet(payload["note"])
                if not self.fault:
                    self._state(State.DISABLED)
            elif action == "scenario" and self.scenario is not None:
                self.scenario.configure(**payload)
            else:
                raise CellError("Unsupported command")
            with self.lock:
                self.last_command = {
                    "id": identifier,
                    "action": action,
                    "status": "handled",
                    "error": self.fault if action == "start" else None,
                }
        except Exception as exc:
            if self.enabled:
                self._fault(exc)
            self.store.event("command_rejected", {"id": identifier, "error": str(exc)})
            with self.lock:
                self.last_command = {
                    "id": identifier,
                    "action": action,
                    "status": "rejected",
                    "error": str(exc),
                }
        finally:
            with self.lock:
                self.pending = False

    def _refresh(self):
        try:
            status = self.robot.status()
            with self.lock:
                self.device_status["robot"] = {**status, "captured_at": time.monotonic()}
        except Exception as exc:
            with self.lock:
                self.device_status["robot"] = {"connected": False, "error": str(exc)}
            if self.enabled:
                raise
        inputs = None
        try:
            inputs = self.plc.read()
            with self.lock:
                self.device_status["plc"] = {"connected": True, **asdict(inputs)}
            if self.enabled and (inputs.estop or not inputs.permit):
                raise CellError("PLC interlock prevents operation")
            self.plc.publish(self.request_id, self.state, self.active_slot)
        except Exception as exc:
            with self.lock:
                self.device_status["plc"] = {"connected": False, "error": str(exc)}
            if self.enabled:
                raise
        try:
            detection = self.camera.inspect()
            with self.lock:
                self.detection, self.camera_error = detection, None
        except Exception as exc:
            with self.lock:
                self.detection, self.camera_error = None, str(exc)
        if inputs and self.enabled:
            if inputs.request_id == 0:
                self.request_armed = True
            elif self.request_armed and inputs.request_id != self.last_request:
                with self.lock:
                    if self.pending:
                        return
                    self.pending = True
                self.request_armed = False
                self.last_request = inputs.request_id
                self.store.set_meta("last_request", str(self.last_request))
                try:
                    self._cycle(inputs.request_id)
                finally:
                    with self.lock:
                        self.pending = False

    def _run(self):
        try:
            self.robot.connect()
            self.plc.connect()
            self.camera.start()
            self.initialized = True
            self.store.event("startup", {"mode": self.settings.mode})
        except Exception as exc:
            self._fault(exc)
        finally:
            self.started.set()
        try:
            while not self.shutdown_event.is_set():
                if self.stop_event.is_set() and (self.enabled or self.pending):
                    self._fault("Controlled stop requested")
                try:
                    command = self.commands.get(timeout=0.1)
                except queue.Empty:
                    command = None
                if command is not None:
                    self._command(*command)
                if self.initialized:
                    try:
                        self._refresh()
                    except Exception as exc:
                        self._fault(exc)
        finally:
            for device in (self.camera, self.plc, self.robot):
                try:
                    device.close()
                except Exception:
                    log.exception("Device cleanup failed")

    def close(self):
        self.shutdown_event.set()
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=20)
            if self.thread.is_alive():
                raise CellError("Controller worker did not stop; database retained for recovery")
        self.store.close()

"""
FastAPI Backend Server with WebSocket Telemetry for IndyDCP3 Robot.
"""

import asyncio
import json
import os
import threading
import time
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from neuromeka import IndyDCP3, OpState, StopCategory, TaskBaseType, JointBaseType

from .config import HMI_HOST, HMI_PORT, DEFAULT_ROBOT_IP, DEFAULT_ROBOT_INDEX, TELEMETRY_HZ
from src.pick_and_place.gripper import VacuumGripper, PneumaticJawGripper
from src.pick_and_place.motion import wait_move_done, move_home_safe, movel_abs

app = FastAPI(title="Indy Robot Web HMI", version="1.0.0")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
WAYPOINTS_FILE = os.path.join(os.path.dirname(__file__), "waypoints.json")

# -------------------------------------------------------------
# Global Robot Manager
# -------------------------------------------------------------
class RobotManager:
    def __init__(self):
        self.ip = DEFAULT_ROBOT_IP
        self.index = DEFAULT_ROBOT_INDEX
        self.indy: Optional[IndyDCP3] = None
        self.is_connected = False
        self.lock = threading.Lock()
        self.sequence_running = False
        self.sequence_status = "Idle"
        self.direct_teaching = False

        # Wait for user manual connection
        self.is_connected = False

    def connect(self, ip: str) -> bool:
        with self.lock:
            try:
                self.indy = IndyDCP3(ip)
                # Auto recover robot on connection to clear any fault/stop state
                try:
                    self.indy.recover()
                except Exception:
                    pass
                self.ip = ip
                self.is_connected = True
                print(f"[HMI Server] Connected successfully to Indy robot at {self.ip}")
                return True
            except Exception as e:
                self.is_connected = False
                print(f"[HMI Server] Connection to {ip} failed: {e}")
                return False

    def recover(self) -> bool:
        if not self.is_connected or not self.indy:
            return False
        with self.lock:
            try:
                self.indy.recover()
                self.direct_teaching = False
                self.sequence_running = False
                self.sequence_status = "Fault Cleared / Ready"
                return True
            except Exception as e:
                print(f"[HMI Server] Recover failed: {e}")
                return False

    def get_op_state_name(self, op_state: int) -> str:
        names = {
            0: "SYSTEM_OFF",
            1: "SYSTEM_ON",
            2: "VIOLATION",
            3: "RECOVER_HARD",
            4: "RECOVER_SOFT",
            5: "IDLE",
            6: "MOVING",
            7: "TEACHING",
            8: "COLLISION",
            9: "STOP_AND_OFF",
            10: "COMPLIANCE",
            11: "BRAKE_CONTROL",
            12: "SYSTEM_RESET",
            13: "SYSTEM_SWITCH",
            15: "VIOLATE_HARD",
            16: "MANUAL_RECOVER",
            17: "TELE_OP",
        }
        return names.get(op_state, f"UNKNOWN({op_state})")

    def get_telemetry(self) -> dict:
        if not self.is_connected or not self.indy:
            return {"connected": False, "ip": self.ip}

        try:
            with self.lock:
                r_data = self.indy.get_robot_data()
                m_data = self.indy.get_motion_data()
                di_raw = self.indy.get_di()
                do_raw = self.indy.get_do()
                ai_raw = self.indy.get_ai()
                ao_raw = self.indy.get_ao()
                end_di_raw = self.indy.get_endtool_di()
                end_do_raw = self.indy.get_endtool_do()

            di_list = di_raw.get("signals", []) if isinstance(di_raw, dict) else di_raw
            do_list = do_raw.get("signals", []) if isinstance(do_raw, dict) else do_raw
            ai_list = ai_raw.get("signals", []) if isinstance(ai_raw, dict) else ai_raw
            ao_list = ao_raw.get("signals", []) if isinstance(ao_raw, dict) else ao_raw
            end_di_list = end_di_raw.get("signals", []) if isinstance(end_di_raw, dict) else end_di_raw
            end_do_list = end_do_raw.get("signals", []) if isinstance(end_do_raw, dict) else end_do_raw

            op_code = r_data.get("op_state", 0)
            return {
                "connected": True,
                "ip": self.ip,
                "op_state": op_code,
                "op_state_name": self.get_op_state_name(op_code),
                "direct_teaching": self.direct_teaching,
                "sequence_running": self.sequence_running,
                "sequence_status": self.sequence_status,
                "q": [round(x, 2) for x in r_data.get("q", [])],
                "p": [round(x, 2) for x in r_data.get("p", [])],
                "motion": {
                    "is_in_motion": m_data.get("is_in_motion", False),
                    "traj_progress": m_data.get("traj_progress", 0),
                    "is_target_reached": m_data.get("is_target_reached", False),
                },
                "di": di_list,
                "do": do_list,
                "ai": ai_list,
                "ao": ao_list,
                "endtool_di": end_di_list,
                "endtool_do": end_do_list,
                "vacuum_sealed": any(d.get("address") == 0 and d.get("state") == 1 for d in di_list if isinstance(d, dict)),
            }
        except Exception as e:
            return {"connected": False, "ip": self.ip, "error": str(e)}


robot = RobotManager()

# -------------------------------------------------------------
# WebSocket Telemetry Broadcaster
# -------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        msg = json.dumps(data)
        for conn in list(self.active_connections):
            try:
                await conn.send_text(msg)
            except Exception:
                self.disconnect(conn)


ws_manager = ConnectionManager()


@app.on_event("startup")
async def start_telemetry_loop():
    async def telemetry_worker():
        interval = 1.0 / TELEMETRY_HZ
        while True:
            data = robot.get_telemetry()
            await ws_manager.broadcast(data)
            await asyncio.sleep(interval)

    asyncio.create_task(telemetry_worker())


@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep-alive receive
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------
class ConnectRequest(BaseModel):
    ip: str


class DirectTeachRequest(BaseModel):
    enable: bool


class ToolRequest(BaseModel):
    state: bool


class SequenceRequest(BaseModel):
    pick_pose: Optional[List[float]] = None
    place_pose: Optional[List[float]] = None
    tool_type: str = "vacuum"  # "vacuum" (DO 0/1) or "gripper" (DO 3)
    repeat_count: int = 1      # 1, 2, 5, 10, or 0 (Infinite loop)
    clearance_z: float = 50.0  # mm approach offset


@app.post("/api/robot/connect")
def api_connect(req: ConnectRequest):
    success = robot.connect(req.ip)
    return {"success": success, "ip": req.ip}


@app.post("/api/robot/home")
def api_move_home():
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")

    def worker():
        with robot.lock:
            robot.indy.move_home()

    threading.Thread(target=worker, daemon=True).start()
    return {"status": "Command sent: Move Home"}


@app.post("/api/robot/zero")
def api_move_zero():
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")

    def worker():
        with robot.lock:
            robot.indy.movej([0.0, 0.0, 0.0, 0.0, 0.0, 0.0], vel_ratio=20, acc_ratio=20)

    threading.Thread(target=worker, daemon=True).start()
    return {"status": "Command sent: Move to Zero Position"}


@app.post("/api/robot/stop")
def api_stop():
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")

    with robot.lock:
        robot.indy.stop_motion(StopCategory.CAT1)
        robot.sequence_running = False
        robot.sequence_status = "Emergency Stopped"
    return {"status": "Robot stopped"}


@app.post("/api/teaching/direct_mode")
def api_direct_teaching(req: DirectTeachRequest):
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")

    with robot.lock:
        robot.indy.set_direct_teaching(req.enable)
        robot.direct_teaching = req.enable
    return {"direct_teaching": req.enable}


class TaskJogRequest(BaseModel):
    axis: str  # 'x', 'y', 'z', 'u', 'v', 'w'
    step: float  # mm or deg (e.g. +10.0 or -10.0)
    vel_ratio: Optional[int] = 20


class JointJogRequest(BaseModel):
    joint_idx: int  # 0 to 5
    step: float  # deg (e.g. +5.0 or -5.0)
    vel_ratio: Optional[int] = 20


class TeleTaskJogRequest(BaseModel):
    axis: str  # 'x', 'y', 'z', 'u', 'v', 'w'
    dir: int   # +1 or -1
    vel_ratio: float = 0.8
    acc_ratio: float = 7.0


class TeleJointJogRequest(BaseModel):
    joint_idx: int  # 0 to 5
    dir: int        # +1 or -1
    vel_ratio: float = 0.8
    acc_ratio: float = 7.0


class PalletRequest(BaseModel):
    rows: int = 2
    cols: int = 2
    layers: int = 1
    dx: float = 50.0  # mm
    dy: float = 50.0  # mm
    dz: float = 30.0  # mm
    pick_pose: Optional[List[float]] = None
    place_origin: Optional[List[float]] = None
    target_slot: Optional[Dict[str, int]] = None  # e.g. {"row": 0, "col": 1, "layer": 0}
    tool_type: str = "vacuum"  # "vacuum" or "gripper"
    repeat_cycles: int = 1
    clearance_z: float = 50.0


@app.post("/api/jog/task")
def api_jog_task(req: TaskJogRequest):
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")

    axis_map = {"x": 0, "y": 1, "z": 2, "u": 3, "v": 4, "w": 5}
    ax = req.axis.lower()
    if ax not in axis_map:
        raise HTTPException(status_code=400, detail=f"Invalid axis: {req.axis}")

    offset = [0.0] * 6
    offset[axis_map[ax]] = req.step

    def worker():
        with robot.lock:
            try:
                robot.indy.movel(
                    ttarget=offset,
                    base_type=TaskBaseType.RELATIVE,
                    vel_ratio=req.vel_ratio or 20,
                    acc_ratio=req.vel_ratio or 20,
                    teaching_mode=True,
                )
            except Exception as e:
                print(f"[HMI Server] Jog task error: {e}")

    threading.Thread(target=worker, daemon=True).start()
    return {"status": f"Jogging {ax.upper()} by {req.step}"}


@app.post("/api/jog/joint")
def api_jog_joint(req: JointJogRequest):
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")

    if not (0 <= req.joint_idx <= 5):
        raise HTTPException(status_code=400, detail="Invalid joint index (must be 0-5)")

    offset = [0.0] * 6
    offset[req.joint_idx] = req.step

    def worker():
        with robot.lock:
            try:
                robot.indy.movej(
                    jtarget=offset,
                    base_type=JointBaseType.RELATIVE,
                    vel_ratio=req.vel_ratio or 20,
                    acc_ratio=req.vel_ratio or 20,
                    teaching_mode=True,
                )
            except Exception as e:
                print(f"[HMI Server] Jog joint error: {e}")

    threading.Thread(target=worker, daemon=True).start()
    return {"status": f"Jogging J{req.joint_idx + 1} by {req.step} deg"}


@app.post("/api/jog/hold_task")
def api_hold_task(req: TeleTaskJogRequest):
    """Reliable synchronous relative Cartesian step for continuous hold jog."""
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")

    axis_map = {"x": 0, "y": 1, "z": 2, "u": 3, "v": 4, "w": 5}
    ax = req.axis.lower()
    if ax not in axis_map:
        raise HTTPException(status_code=400, detail=f"Invalid axis: {req.axis}")

    lin_scale = 5.0   # 5mm smooth step
    rot_scale = 3.0   # 3deg smooth step
    
    offset = [0.0] * 6
    step_mag = lin_scale if ax in ["x", "y", "z"] else rot_scale
    offset[axis_map[ax]] = step_mag * (1 if req.dir > 0 else -1)

    with robot.lock:
        try:
            res = robot.indy.movel(
                ttarget=offset,
                base_type=TaskBaseType.RELATIVE,
                vel_ratio=20,
                acc_ratio=20,
                teaching_mode=True,
            )
            return {"status": "ok", "result": res}
        except Exception as e:
            return {"status": "ignored", "error": str(e)}


@app.post("/api/jog/hold_joint")
def api_hold_joint(req: TeleJointJogRequest):
    """Reliable synchronous relative Joint step for continuous hold jog."""
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")

    if not (0 <= req.joint_idx <= 5):
        raise HTTPException(status_code=400, detail="Invalid joint index")

    offset = [0.0] * 6
    offset[req.joint_idx] = 3.0 * (1 if req.dir > 0 else -1)

    with robot.lock:
        try:
            res = robot.indy.movej(
                jtarget=offset,
                base_type=JointBaseType.RELATIVE,
                vel_ratio=20,
                acc_ratio=20,
                teaching_mode=True,
            )
            return {"status": "ok", "result": res}
        except Exception as e:
            return {"status": "ignored", "error": str(e)}


@app.post("/api/jog/stop")
def api_jog_stop():
    if not robot.is_connected or not robot.indy:
        return {"status": "not connected"}
    with robot.lock:
        try:
            robot.indy.stop_motion(StopCategory.CAT0)
        except Exception:
            pass
    return {"status": "Jog Stopped"}


class SetDORequest(BaseModel):
    address: int
    state: int  # 0: OFF, 1: ON


class SetAORequest(BaseModel):
    address: int
    voltage: int  # mV (0 to 10000)


class SetEndDORequest(BaseModel):
    port: str = "C"
    state: int = 1


@app.post("/api/io/set_do")
def api_set_do(req: SetDORequest):
    """Sets a specific Digital Output channel state."""
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")
    with robot.lock:
        robot.indy.set_do([{"address": req.address, "state": req.state}])
    return {"address": req.address, "state": req.state, "success": True}


@app.post("/api/io/set_ao")
def api_set_ao(req: SetAORequest):
    """Sets a specific Analog Output channel voltage in mV."""
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")
    with robot.lock:
        robot.indy.set_ao([{"address": req.address, "voltage": req.voltage}])
    return {"address": req.address, "voltage": req.voltage, "success": True}


@app.post("/api/io/set_endtool_do")
def api_set_endtool_do(req: SetEndDORequest):
    """Sets Endtool DO port state."""
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")
    with robot.lock:
        robot.indy.set_endtool_do([{"port": req.port, "states": [req.state]}])
    return {"port": req.port, "state": req.state, "success": True}


@app.post("/api/robot/recover")
def api_recover():
    """Recovers the robot from error/fault/collision/E-Stop state."""
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")
    success = robot.recover()
    return {"status": "Fault Cleared / Ready" if success else "Recover Failed", "success": success}


@app.post("/api/tool/vacuum")
def api_vacuum(req: ToolRequest):
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")

    with robot.lock:
        robot.indy.set_do([{"address": 0, "state": 1 if req.state else 0}])
    return {"vacuum": req.state}


@app.post("/api/tool/blow_off")
def api_blow_off():
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")

    def worker():
        with robot.lock:
            # Vacuum off, blow-off on
            robot.indy.set_do([{"address": 0, "state": 0}, {"address": 1, "state": 1}])
        time.sleep(0.15)
        with robot.lock:
            robot.indy.set_do([{"address": 1, "state": 0}])

    threading.Thread(target=worker, daemon=True).start()
    return {"status": "Blow-off pulse executed"}


@app.post("/api/tool/gripper")
@app.post("/api/tool/jaw")
def api_gripper(req: ToolRequest):
    """Controls Gripper / Jaws on DO #3."""
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")

    with robot.lock:
        robot.indy.set_do([{"address": 3, "state": 1 if req.state else 0}])
    return {"gripper_closed": req.state, "address": 3}


@app.get("/api/waypoints")
def api_get_waypoints():
    if os.path.exists(WAYPOINTS_FILE):
        with open(WAYPOINTS_FILE, "r") as f:
            return json.load(f)
    return {
        "pick_pose": [350.0, -150.0, 520.0, 180.0, 0.0, 180.0],
        "place_pose": [350.0, 150.0, 520.0, 180.0, 0.0, 180.0],
    }


@app.post("/api/waypoints")
def api_save_waypoints(data: dict):
    with open(WAYPOINTS_FILE, "w") as f:
        json.dump(data, f, indent=4)
    return {"status": "Saved", "waypoints": data}


@app.post("/api/robot/goto_pick")
def api_goto_pick():
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")

    wp = api_get_waypoints()
    pick_p = wp.get("pick_pose")
    if not pick_p:
        raise HTTPException(status_code=400, detail="No pick pose saved")

    def worker():
        approach = list(pick_p)
        approach[2] += 50.0
        with robot.lock:
            movel_abs(robot.indy, approach, vel_ratio=20, acc_ratio=20)

    threading.Thread(target=worker, daemon=True).start()
    return {"status": "Moving to Pick Approach"}


@app.post("/api/robot/goto_place")
def api_goto_place():
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")

    wp = api_get_waypoints()
    place_p = wp.get("place_pose")
    if not place_p:
        raise HTTPException(status_code=400, detail="No place pose saved")

    def worker():
        approach = list(place_p)
        approach[2] += 50.0
        with robot.lock:
            movel_abs(robot.indy, approach, vel_ratio=20, acc_ratio=20)

    threading.Thread(target=worker, daemon=True).start()
    return {"status": "Moving to Place Approach"}


@app.post("/api/pallet/run")
def api_run_pallet(req: PalletRequest):
    """Executes multi-slot palletization with explicit waypoint telemetry."""
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")
    if robot.sequence_running:
        raise HTTPException(status_code=400, detail="Sequence already running")

    wp = api_get_waypoints()
    pick_base = req.pick_pose or wp.get("pick_pose")
    place_base = req.place_origin or wp.get("place_pose")

    slots_to_run = []
    if req.target_slot:
        slots_to_run.append(req.target_slot)
    else:
        for lay in range(req.layers):
            for r in range(req.rows):
                for c in range(req.cols):
                    slots_to_run.append({"row": r, "col": c, "layer": lay})

    def pallet_worker():
        robot.sequence_running = True
        try:
            clearance = req.clearance_z or 50.0
            tool = req.tool_type or "vacuum"

            def grip_tool():
                if tool == "gripper2":
                    robot.indy.set_do([{"address": 2, "state": 1}])
                    time.sleep(0.4)
                elif tool == "gripper" or tool == "gripper3":
                    robot.indy.set_do([{"address": 3, "state": 1}])
                    time.sleep(0.4)
                else:
                    robot.indy.set_do([{"address": 1, "state": 0}, {"address": 0, "state": 1}])
                    time.sleep(0.4)

            def release_tool():
                if tool == "gripper2":
                    robot.indy.set_do([{"address": 2, "state": 0}])
                    time.sleep(0.3)
                elif tool == "gripper" or tool == "gripper3":
                    robot.indy.set_do([{"address": 3, "state": 0}])
                    time.sleep(0.3)
                else:
                    robot.indy.set_do([{"address": 0, "state": 0}, {"address": 1, "state": 1}])
                    time.sleep(0.15)
                    robot.indy.set_do([{"address": 1, "state": 0}])

            total = len(slots_to_run)
            for idx, slot in enumerate(slots_to_run):
                if not robot.sequence_running:
                    break

                r, c, lay = slot["row"], slot["col"], slot["layer"]
                target_place = list(place_base)
                target_place[0] += c * req.dx
                target_place[1] += r * req.dy
                target_place[2] += lay * req.dz

                appr_pick = list(pick_base)
                appr_pick[2] += clearance

                appr_place = list(target_place)
                appr_place[2] += clearance

                # 1. Approach Pick
                robot.sequence_status = f"Slot [{r+1},{c+1}] ({idx+1}/{total}): 1. Approaching Pick"
                movel_abs(robot.indy, appr_pick, vel_ratio=25, acc_ratio=25)
                if not robot.sequence_running: break

                # 2. Plunge Pick
                robot.sequence_status = f"Slot [{r+1},{c+1}] ({idx+1}/{total}): 2. Plunging to Pick"
                movel_abs(robot.indy, pick_base, vel_ratio=15, acc_ratio=15)
                if not robot.sequence_running: break

                # 3. Grip / Vacuum
                robot.sequence_status = f"Slot [{r+1},{c+1}] ({idx+1}/{total}): 3. Grasping ({tool.upper()})"
                grip_tool()

                # 4. Retract Pick
                robot.sequence_status = f"Slot [{r+1},{c+1}] ({idx+1}/{total}): 4. Retracting from Pick"
                movel_abs(robot.indy, appr_pick, vel_ratio=20, acc_ratio=20)
                if not robot.sequence_running: break

                # 5. Approach Place
                robot.sequence_status = f"Slot [{r+1},{c+1}] ({idx+1}/{total}): 5. Transiting to Place"
                movel_abs(robot.indy, appr_place, vel_ratio=25, acc_ratio=25)
                if not robot.sequence_running: break

                # 6. Lower Place
                robot.sequence_status = f"Slot [{r+1},{c+1}] ({idx+1}/{total}): 6. Placing in Slot [{r+1},{c+1}]"
                movel_abs(robot.indy, target_place, vel_ratio=15, acc_ratio=15)
                if not robot.sequence_running: break

                # 7. Release
                robot.sequence_status = f"Slot [{r+1},{c+1}] ({idx+1}/{total}): 7. Releasing ({tool.upper()})"
                release_tool()

                # 8. Retract Place
                robot.sequence_status = f"Slot [{r+1},{c+1}] ({idx+1}/{total}): 8. Retracting to Clearance"
                movel_abs(robot.indy, appr_place, vel_ratio=20, acc_ratio=20)

            if robot.sequence_running:
                robot.sequence_status = "Returning to Home Position"
                robot.indy.move_home()
                wait_move_done(robot.indy)
                robot.sequence_status = f"Palletization Complete ({total} slots)"
        except Exception as e:
            robot.sequence_status = f"Error: {e}"
        finally:
            robot.sequence_running = False

    threading.Thread(target=pallet_worker, daemon=True).start()
    return {"status": f"Pallet sequence started for {len(slots_to_run)} slots"}


@app.post("/api/sequence/run")
def api_run_sequence(req: SequenceRequest):
    if not robot.is_connected or not robot.indy:
        raise HTTPException(status_code=400, detail="Robot not connected")
    if robot.sequence_running:
        raise HTTPException(status_code=400, detail="Sequence is already running")

    current_wp = api_get_waypoints()
    pick_p = req.pick_pose or current_wp.get("pick_pose")
    place_p = req.place_pose or current_wp.get("place_pose")

    def sequence_thread():
        robot.sequence_running = True
        try:
            clearance = req.clearance_z or 50.0
            tool = req.tool_type or "vacuum"
            loops_left = req.repeat_count if req.repeat_count > 0 else 999999
            is_infinite = req.repeat_count == 0
            cycle_idx = 0

            def grip_tool():
                if tool == "gripper2":
                    robot.indy.set_do([{"address": 2, "state": 1}])
                    time.sleep(0.4)
                elif tool == "gripper" or tool == "gripper3":
                    robot.indy.set_do([{"address": 3, "state": 1}])
                    time.sleep(0.4)
                else:
                    robot.indy.set_do([{"address": 1, "state": 0}, {"address": 0, "state": 1}])
                    time.sleep(0.4)

            def release_tool():
                if tool == "gripper2":
                    robot.indy.set_do([{"address": 2, "state": 0}])
                    time.sleep(0.3)
                elif tool == "gripper" or tool == "gripper3":
                    robot.indy.set_do([{"address": 3, "state": 0}])
                    time.sleep(0.3)
                else:
                    robot.indy.set_do([{"address": 0, "state": 0}, {"address": 1, "state": 1}])
                    time.sleep(0.15)
                    robot.indy.set_do([{"address": 1, "state": 0}])

            while robot.sequence_running and loops_left > 0:
                cycle_idx += 1
                loop_tag = f"Cycle #{cycle_idx}" if not is_infinite else f"Loop #{cycle_idx}"

                # 1. Approach Pick
                robot.sequence_status = f"[{loop_tag}] 1. Approaching Pick..."
                approach_pick = list(pick_p)
                approach_pick[2] += clearance
                movel_abs(robot.indy, approach_pick, vel_ratio=25, acc_ratio=25)
                if not robot.sequence_running: break

                # 2. Plunge Pick
                robot.sequence_status = f"[{loop_tag}] 2. Plunging to Pick..."
                movel_abs(robot.indy, pick_p, vel_ratio=15, acc_ratio=15)
                if not robot.sequence_running: break

                # 3. Grip / Vacuum
                robot.sequence_status = f"[{loop_tag}] 3. Actuating {tool.upper()}..."
                grip_tool()

                # 4. Retract Pick
                robot.sequence_status = f"[{loop_tag}] 4. Retracting from Pick..."
                movel_abs(robot.indy, approach_pick, vel_ratio=20, acc_ratio=20)
                if not robot.sequence_running: break

                # 5. Approach Place
                robot.sequence_status = f"[{loop_tag}] 5. Moving to Place Approach..."
                approach_place = list(place_p)
                approach_place[2] += clearance
                movel_abs(robot.indy, approach_place, vel_ratio=25, acc_ratio=25)
                if not robot.sequence_running: break

                # 6. Lower Place
                robot.sequence_status = f"[{loop_tag}] 6. Lowering to Place..."
                movel_abs(robot.indy, place_p, vel_ratio=15, acc_ratio=15)
                if not robot.sequence_running: break

                # 7. Release
                robot.sequence_status = f"[{loop_tag}] 7. Releasing {tool.upper()}..."
                release_tool()

                # 8. Retract Place
                robot.sequence_status = f"[{loop_tag}] 8. Retracting to Clearance..."
                movel_abs(robot.indy, approach_place, vel_ratio=20, acc_ratio=20)

                if req.repeat_count > 0:
                    loops_left -= 1

            if robot.sequence_running:
                robot.sequence_status = "Returning to Home Position..."
                robot.indy.move_home()
                wait_move_done(robot.indy)
                robot.sequence_status = f"Sequence Finished ({cycle_idx} cycles)"
        except Exception as e:
            robot.sequence_status = f"Error: {e}"
        finally:
            robot.sequence_running = False

    threading.Thread(target=sequence_thread, daemon=True).start()
    return {"status": "Sequence loop started"}


@app.post("/api/sequence/abort")
def api_abort_sequence():
    """Aborts any running sequence or pallet operation immediately."""
    robot.sequence_running = False
    with robot.lock:
        try:
            robot.indy.stop_motion(StopCategory.CAT1)
        except Exception:
            pass
    robot.sequence_status = "Sequence Aborted by User"
    return {"status": "Sequence aborted"}


# -------------------------------------------------------------
# Static Files & Frontend Mount
# -------------------------------------------------------------
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

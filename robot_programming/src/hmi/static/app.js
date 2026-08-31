/**
 * IndyDCP3 Industrial HMI Client
 * Set-based action architecture with persistent telemetry/log dock.
 */

// State
let ws = null;
let currentPose = [0, 0, 0, 0, 0, 0];
let currentJoints = [0, 0, 0, 0, 0, 0];
let jogMode = "hold"; // "hold" or "step"
let currentLinearStep = 10.0; // mm
let currentRotStep = 10.0;    // deg
let holdJogInterval = null;
let selectedPalletSlot = { row: 0, col: 0, layer: 0 };

let waypoints = {
  pick_pose: [350.0, -150.0, 520.0, 180.0, 0.0, 180.0],
  place_pose: [350.0, 150.0, 520.0, 180.0, 0.0, 180.0],
};
let isVacuumOn = false;
let isGripperClosed = false;

// DOM Elements - Header
const opStatePill = document.getElementById("opStatePill");
const opStateText = document.getElementById("opStateText");
const robotIpInput = document.getElementById("robotIpInput");
const btnConnect = document.getElementById("btnConnect");
const btnResetFault = document.getElementById("btnResetFault");
const btnHeaderHome = document.getElementById("btnHeaderHome");
const btnHeaderZero = document.getElementById("btnHeaderZero");
const btnEstop = document.getElementById("btnEstop");

// DOM Elements - Telemetry Readouts
const tcpX = document.getElementById("tcpX");
const tcpY = document.getElementById("tcpY");
const tcpZ = document.getElementById("tcpZ");
const tcpU = document.getElementById("tcpU");
const tcpV = document.getElementById("tcpV");
const tcpW = document.getElementById("tcpW");

// DOM Elements - Persistent Dock
const footerTcp = document.getElementById("footerTcp");
const footerJoints = document.getElementById("footerJoints");
const footerMotion = document.getElementById("footerMotion");
const consoleLogs = document.getElementById("consoleLogs");
const btnClearLog = document.getElementById("btnClearLog");

// Jog Modes & Toolbar
const modeBtnHold = document.getElementById("modeBtnHold");
const modeBtnStep = document.getElementById("modeBtnStep");
const stepSelectorContainer = document.getElementById("stepSelectorContainer");

// Waypoints Studio
const toggleDirectTeach = document.getElementById("toggleDirectTeach");
const btnCapturePick = document.getElementById("btnCapturePick");
const btnCapturePlace = document.getElementById("btnCapturePlace");
const btnGotoPick = document.getElementById("btnGotoPick");
const btnGotoPlace = document.getElementById("btnGotoPlace");
const pickCoordsDisplay = document.getElementById("pickCoordsDisplay");
const placeCoordsDisplay = document.getElementById("placeCoordsDisplay");

// Palletization
const palletRows = document.getElementById("palletRows");
const palletCols = document.getElementById("palletCols");
const palletDx = document.getElementById("palletDx");
const palletDy = document.getElementById("palletDy");
const palletSlotGrid = document.getElementById("palletSlotGrid");
const selectedSlotInfo = document.getElementById("selectedSlotInfo");
const btnRunFullPallet = document.getElementById("btnRunFullPallet");
const btnRunSelectedSlot = document.getElementById("btnRunSelectedSlot");
const palletStatusText = document.getElementById("palletStatusText");

// Single / Loop Sequence
const btnRunSequence = document.getElementById("btnRunSequence");
const btnAbortSequence = document.getElementById("btnAbortSequence");
const seqToolSelect = document.getElementById("seqToolSelect");
const seqRepeatSelect = document.getElementById("seqRepeatSelect");
const seqClearance = document.getElementById("seqClearance");
const progressPctText = document.getElementById("progressPctText");
const motionProgressBar = document.getElementById("motionProgressBar");

// Tree Coords Displays
const treeCoord1 = document.getElementById("treeCoord1");
const treeCoord2 = document.getElementById("treeCoord2");
const treeCoord3 = document.getElementById("treeCoord3");
const treeCoord4 = document.getElementById("treeCoord4");
const treeCoord5 = document.getElementById("treeCoord5");

// Tools & I/O
const btnToggleGripper = document.getElementById("btnToggleGripper");
const gripperBtnText = document.getElementById("gripperBtnText");
const btnToggleVacuum = document.getElementById("btnToggleVacuum");
const vacuumBtnText = document.getElementById("vacuumBtnText");
const btnPulseBlow = document.getElementById("btnPulseBlow");
const diRegistersGrid = document.getElementById("diRegistersGrid");
const doRegistersGrid = document.getElementById("doRegistersGrid");

// -------------------------------------------------------------
// Logging Helper (Always visible in bottom dock)
// -------------------------------------------------------------
function log(msg, type = "sys") {
  const entry = document.createElement("div");
  entry.className = `log-line log-${type}`;
  const timestamp = new Date().toLocaleTimeString();
  entry.textContent = `[${timestamp}] ${msg}`;
  if (consoleLogs) {
    consoleLogs.appendChild(entry);
    consoleLogs.scrollTop = consoleLogs.scrollHeight;
  }
}

// -------------------------------------------------------------
// REST API Helper
// -------------------------------------------------------------
async function postAPI(endpoint, body = {}) {
  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) {
      log(`API ERR (${endpoint}): ${data.detail || 'Request failed'}`, "err");
      return null;
    }
    return data;
  } catch (err) {
    log(`NET ERR (${endpoint}): ${err.message}`, "err");
    return null;
  }
}

// -------------------------------------------------------------
// Tab Switching (Set 1, Set 2, Set 3)
// -------------------------------------------------------------
function setupTabs() {
  const tabButtons = document.querySelectorAll(".tab-btn");
  const tabPanels = document.querySelectorAll(".tab-panel");

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.dataset.tab;

      tabButtons.forEach((b) => b.classList.remove("active"));
      tabPanels.forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) targetPanel.classList.add("active");
    });
  });
}

// -------------------------------------------------------------
// Teleoperation Hold-to-Jog Engine
// -------------------------------------------------------------
function setupJogControls() {
  modeBtnHold.addEventListener("click", () => {
    jogMode = "hold";
    modeBtnHold.classList.add("active");
    modeBtnStep.classList.remove("active");
    stepSelectorContainer.style.display = "none";
    log("Jog Mode: CONTINUOUS (HOLD TO MOVE)", "sys");
  });

  modeBtnStep.addEventListener("click", () => {
    jogMode = "step";
    modeBtnStep.classList.add("active");
    modeBtnHold.classList.remove("active");
    stepSelectorContainer.style.display = "flex";
    log("Jog Mode: INCREMENTAL (STEP JOG)", "sys");
  });

  document.querySelectorAll(".step-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".step-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentLinearStep = parseFloat(btn.dataset.lin);
      currentRotStep = parseFloat(btn.dataset.rot);
      log(`Step Size Set: ${currentLinearStep}mm / ${currentRotStep}°`, "sys");
    });
  });

  document.querySelectorAll(".btn-jog-dir").forEach((btn) => {
    const type = btn.dataset.type;
    const dir = parseInt(btn.dataset.dir, 10);
    const axis = btn.dataset.axis;
    const jointIdx = parseInt(btn.dataset.joint, 10);

    let isJogActive = false;
    let isRequestInFlight = false;

    const startJog = async (e) => {
      e.preventDefault();
      btn.classList.add("jogging-active");

      if (jogMode === "step") {
        if (type === "task") {
          const isLin = ["x", "y", "z"].includes(axis);
          const stepVal = (isLin ? currentLinearStep : currentRotStep) * dir;
          log(`Step Task Jog: ${axis.toUpperCase()} ${stepVal > 0 ? '+' : ''}${stepVal} ${isLin ? 'mm' : '°'}`);
          await postAPI("/api/jog/task", { axis, step: stepVal, vel_ratio: 25 });
        } else if (type === "joint") {
          const stepVal = currentRotStep * dir;
          log(`Step Joint Jog: J${jointIdx + 1} ${stepVal > 0 ? '+' : ''}${stepVal}°`);
          await postAPI("/api/jog/joint", { joint_idx: jointIdx, step: stepVal, vel_ratio: 25 });
        }
      } else {
        isJogActive = true;
        
        // Continuous request-gated loop (never floods or conflicts)
        (async () => {
          while (isJogActive) {
            if (!isRequestInFlight) {
              isRequestInFlight = true;
              try {
                if (type === "task") {
                  await postAPI("/api/jog/hold_task", { axis, dir });
                } else if (type === "joint") {
                  await postAPI("/api/jog/hold_joint", { joint_idx: jointIdx, dir });
                }
              } catch (err) {
                console.error("Jog hold error:", err);
              } finally {
                isRequestInFlight = false;
              }
            }
            // 50ms pacing between motion steps
            await new Promise((resolve) => setTimeout(resolve, 50));
          }
        })();
      }
    };

    const stopJog = async (e) => {
      btn.classList.remove("jogging-active");
      isJogActive = false;
      if (jogMode === "hold") {
        await postAPI("/api/jog/stop");
      }
    };

    btn.addEventListener("pointerdown", startJog);
    btn.addEventListener("pointerup", stopJog);
    btn.addEventListener("pointerleave", stopJog);
    btn.addEventListener("pointercancel", stopJog);
  });
}

// -------------------------------------------------------------
// Parametric Palletization Matrix Engine
// -------------------------------------------------------------
function renderPalletGrid() {
  const rows = parseInt(palletRows.value, 10) || 2;
  const cols = parseInt(palletCols.value, 10) || 2;
  const dx = parseFloat(palletDx.value) || 50.0;
  const dy = parseFloat(palletDy.value) || 50.0;

  palletSlotGrid.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
  palletSlotGrid.innerHTML = "";

  const origin = waypoints.place_pose || [350.0, 150.0, 520.0, 180.0, 0.0, 180.0];

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const slotIndex = r * cols + c + 1;
      const targetX = origin[0] + c * dx;
      const targetY = origin[1] + r * dy;
      const targetZ = origin[2];

      const cell = document.createElement("div");
      cell.className = "pallet-cell";
      if (selectedPalletSlot.row === r && selectedPalletSlot.col === c) {
        cell.classList.add("selected");
      }

      cell.innerHTML = `
        <span class="cell-name">SLOT ${slotIndex} [R${r+1},C${c+1}]</span>
        <span class="cell-coord font-mono">[${targetX.toFixed(1)}, ${targetY.toFixed(1)}, ${targetZ.toFixed(1)}]</span>
      `;

      cell.addEventListener("click", () => {
        document.querySelectorAll(".pallet-cell").forEach(el => el.classList.remove("selected"));
        cell.classList.add("selected");
        selectedPalletSlot = { row: r, col: c, layer: 0 };
        selectedSlotInfo.textContent = `Slot [R${r+1}, C${c+1}] | Target: [${targetX.toFixed(1)}, ${targetY.toFixed(1)}, ${targetZ.toFixed(1)}]`;
        log(`Selected Pallet Slot ${slotIndex} at [${targetX.toFixed(1)}, ${targetY.toFixed(1)}, ${targetZ.toFixed(1)}]`);
      });

      palletSlotGrid.appendChild(cell);
    }
  }

  const selTargetX = origin[0] + selectedPalletSlot.col * dx;
  const selTargetY = origin[1] + selectedPalletSlot.row * dy;
  const selTargetZ = origin[2];
  selectedSlotInfo.textContent = `Slot [R${selectedPalletSlot.row+1}, C${selectedPalletSlot.col+1}] | Target: [${selTargetX.toFixed(1)}, ${selTargetY.toFixed(1)}, ${selTargetZ.toFixed(1)}]`;
}

// -------------------------------------------------------------
// Update Explicit Waypoint Tree
// -------------------------------------------------------------
function updateWaypointTree() {
  const pick = waypoints.pick_pose || [350.0, -150.0, 520.0, 180.0, 0.0, 180.0];
  const place = waypoints.place_pose || [350.0, 150.0, 520.0, 180.0, 0.0, 180.0];

  const pickAppr = [pick[0], pick[1], pick[2] + 50.0];
  const placeAppr = [place[0], place[1], place[2] + 50.0];

  if (treeCoord1) treeCoord1.textContent = `[${pickAppr.map(x => x.toFixed(1)).join(", ")}] (Z+50mm)`;
  if (treeCoord2) treeCoord2.textContent = `[${pick.slice(0, 3).map(x => x.toFixed(1)).join(", ")}] (Surface Level)`;
  if (treeCoord3) treeCoord3.textContent = `Lift Z+50mm -> Across to Dropoff Area`;
  if (treeCoord4) treeCoord4.textContent = `[${place.slice(0, 3).map(x => x.toFixed(1)).join(", ")}] (Slot Touchdown)`;
  if (treeCoord5) treeCoord5.textContent = `[0.0°, 0.0°, -90.0°, 0.0°, -90.0°, 0.0°]`;
}

// -------------------------------------------------------------
// WebSocket Telemetry Connection (Streams to Persistent Dock)
// -------------------------------------------------------------
function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;

  log(`Telemetry connecting: ${wsUrl}...`, "sys");
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    log("Telemetry stream active (15 Hz).", "ok");
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      updateTelemetryUI(data);
    } catch (e) {
      console.error("Telemetry parse error:", e);
    }
  };

  ws.onclose = () => {
    log("Telemetry link interrupted. Reconnecting in 2s...", "err");
    setTimeout(connectWebSocket, 2000);
  };
}

// -------------------------------------------------------------
// UI Telemetry Renderers
// -------------------------------------------------------------
function updateTelemetryUI(data) {
  if (!data.connected) {
    opStatePill.className = "status-badge status-alert";
    opStateText.textContent = "DISCONNECTED";
    if (footerMotion) footerMotion.textContent = "OFFLINE";
    return;
  }

  const opName = data.op_state_name || "IDLE";
  opStateText.textContent = `OP_${opName} (${data.op_state})`;

  opStatePill.className = "status-badge";
  if (data.op_state === 5) opStatePill.classList.add("status-idle");
  else if (data.op_state === 6) opStatePill.classList.add("status-moving");
  else if (data.op_state === 7 || data.direct_teaching) opStatePill.classList.add("status-teaching");
  else if ([0, 2, 8, 15].includes(data.op_state)) opStatePill.classList.add("status-alert");
  else opStatePill.classList.add("status-idle");

  if (footerMotion) footerMotion.textContent = `OP_${opName} (${data.op_state})`;

  if (toggleDirectTeach && toggleDirectTeach.checked !== data.direct_teaching) {
    toggleDirectTeach.checked = !!data.direct_teaching;
  }

  // Joint Angles
  if (data.q && data.q.length >= 6) {
    currentJoints = data.q;
    data.q.forEach((angle, idx) => {
      const valEl = document.getElementById(`jVal${idx}`);
      const barEl = document.getElementById(`jBar${idx}`);
      if (valEl) valEl.textContent = `${angle.toFixed(2)}°`;
      if (barEl) {
        const pct = Math.max(0, Math.min(100, ((angle + 180) / 360) * 100));
        barEl.style.width = `${pct}%`;
      }
    });

    if (footerJoints) {
      footerJoints.textContent = `[${data.q.map(x => x.toFixed(1) + '°').join(', ')}]`;
    }
  }

  // Cartesian TCP Pose
  if (data.p && data.p.length >= 6) {
    currentPose = data.p;
    if (tcpX) tcpX.innerHTML = `${data.p[0].toFixed(1)} <small>mm</small>`;
    if (tcpY) tcpY.innerHTML = `${data.p[1].toFixed(1)} <small>mm</small>`;
    if (tcpZ) tcpZ.innerHTML = `${data.p[2].toFixed(1)} <small>mm</small>`;
    if (tcpU) tcpU.innerHTML = `${data.p[3].toFixed(1)} <small>°</small>`;
    if (tcpV) tcpV.innerHTML = `${data.p[4].toFixed(1)} <small>°</small>`;
    if (tcpW) tcpW.innerHTML = `${data.p[5].toFixed(1)} <small>°</small>`;

    if (footerTcp) {
      footerTcp.textContent = `[${data.p.slice(0, 3).map(x => x.toFixed(1)).join(', ')}]`;
    }
  }

  // Authentic Conty Control Box I/O & Analog Updates
  renderDigitalRegisters(data.di || [], data.do || [], data.ai || [], data.ao || []);

  // Sequence / Pallet Status
  const status = data.sequence_status || "IDLE";
  if (palletStatusText) palletStatusText.textContent = `STATUS: ${status.toUpperCase()}`;

  // Step Node Highlighting
  const steps = [
    { id: "treeStep1", match: "Approaching Pick" },
    { id: "treeStep2", match: "Plunging" },
    { id: "treeStep3", match: "Retracting from Pick" },
    { id: "treeStep4", match: "Placing" },
    { id: "treeStep5", match: "Home" }
  ];

  steps.forEach(s => {
    const el = document.getElementById(s.id);
    if (el) {
      if (status.includes(s.match)) el.classList.add("active");
      else el.classList.remove("active");
    }
  });

  const prog = data.motion?.traj_progress || 0;
  if (progressPctText) progressPctText.textContent = `${prog}%`;
  if (motionProgressBar) motionProgressBar.style.width = `${prog}%`;

  if (btnAbortSequence) {
    btnAbortSequence.style.display = data.sequence_running ? "block" : "none";
  }
}

// -------------------------------------------------------------
// Authentic Conty Control Box I/O Engine
// -------------------------------------------------------------
let latestDOState = {};
let latestDIState = {};
const aiHistory = {
  ai0: new Array(50).fill(0),
  ai1: new Array(50).fill(0),
};

window.toggleDO = async function(addr) {
  const cur = latestDOState[addr] || 0;
  const next = cur === 1 ? 0 : 1;
  log(`Conty IO: Toggling DO.${addr} -> ${next === 1 ? 'ON (1)' : 'OFF (0)'}`, "sys");
  await postAPI("/api/io/set_do", { address: addr, state: next });
};

window.sendAO = async function(addr) {
  const inputEl = document.getElementById(`ao-val-${addr}`);
  const val = inputEl ? parseInt(inputEl.value, 10) || 0 : 0;
  log(`Conty IO: Setting AO.${addr} -> ${val} mV`, "sys");
  await postAPI("/api/io/set_ao", { address: addr, voltage: val });
};

function renderDigitalRegisters(diList, doList, aiList, aoList) {
  // Update DI 0..19 Pins
  if (Array.isArray(diList)) {
    diList.forEach(sig => {
      latestDIState[sig.address] = sig.state;
      const pin = document.getElementById(`conty-di-pin-${sig.address}`);
      if (pin) {
        if (sig.state === 1) {
          pin.className = "pin-circle state-on";
        } else {
          pin.className = "pin-circle state-off";
        }
      }
    });
  }

  // Update DO 0..19 Pins
  if (Array.isArray(doList)) {
    doList.forEach(sig => {
      latestDOState[sig.address] = sig.state;
      const pin = document.getElementById(`conty-do-pin-${sig.address}`);
      if (pin) {
        if (sig.state === 1) {
          pin.className = "pin-circle state-on";
        } else {
          pin.className = "pin-circle state-off";
        }
      }
    });
  }

  // Update AI 0..1 (Analog Inputs) & Oscilloscope
  if (Array.isArray(aiList)) {
    const ai0 = aiList.find(s => s.address === 0)?.voltage || 0;
    const ai1 = aiList.find(s => s.address === 1)?.voltage || 0;

    const lbl0 = document.getElementById("ai-lbl-0");
    const lbl1 = document.getElementById("ai-lbl-1");
    if (lbl0) lbl0.textContent = `AI.0 (${(ai0 / 1000).toFixed(1)}V)`;
    if (lbl1) lbl1.textContent = `AI.1 (${(ai1 / 1000).toFixed(1)}V)`;

    const pin0 = document.getElementById("conty-ai-pin-0");
    const pin1 = document.getElementById("conty-ai-pin-1");
    if (pin0) pin0.className = `pin-circle ${ai0 > 500 ? 'state-on' : 'state-off'}`;
    if (pin1) pin1.className = `pin-circle ${ai1 > 500 ? 'state-on' : 'state-off'}`;

    // Push to history
    aiHistory.ai0.push(ai0);
    aiHistory.ai0.shift();
    aiHistory.ai1.push(ai1);
    aiHistory.ai1.shift();

    drawAiOscilloscope();
  }

  // Update AO 0..1 (Analog Outputs)
  if (Array.isArray(aoList)) {
    aoList.forEach(sig => {
      const pin = document.getElementById(`conty-ao-pin-${sig.address}`);
      if (pin) {
        pin.className = `pin-circle ${sig.voltage > 500 ? 'state-on' : 'state-off'}`;
      }
    });
  }
}

function drawAiOscilloscope() {
  const canvas = document.getElementById("contyAiCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;

  ctx.clearRect(0, 0, w, h);

  // Draw Grid Lines (0V, 5V, 10V)
  ctx.strokeStyle = "#1e293b";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, h * 0.5);
  ctx.lineTo(w, h * 0.5);
  ctx.stroke();

  // Draw AI.0 (Green #22c55e)
  ctx.strokeStyle = "#22c55e";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  aiHistory.ai0.forEach((val, idx) => {
    const x = (idx / (aiHistory.ai0.length - 1)) * w;
    const y = h - (val / 10000) * (h - 8) - 4;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Draw AI.1 (Blue #3b82f6)
  ctx.strokeStyle = "#3b82f6";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  aiHistory.ai1.forEach((val, idx) => {
    const x = (idx / (aiHistory.ai1.length - 1)) * w;
    const y = h - (val / 10000) * (h - 8) - 4;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

// -------------------------------------------------------------
// Waypoints Management
// -------------------------------------------------------------
async function loadWaypoints() {
  try {
    const res = await fetch("/api/waypoints");
    waypoints = await res.json();
    updateWaypointCards();
    updateWaypointTree();
    renderPalletGrid();
  } catch (e) {
    console.error("Failed to load waypoints:", e);
  }
}

function updateWaypointCards() {
  if (pickCoordsDisplay && waypoints.pick_pose) {
    pickCoordsDisplay.textContent = `[${waypoints.pick_pose.map(x => x.toFixed(1)).join(", ")}]`;
  }
  if (placeCoordsDisplay && waypoints.place_pose) {
    placeCoordsDisplay.textContent = `[${waypoints.place_pose.map(x => x.toFixed(1)).join(", ")}]`;
  }
}

async function saveWaypoints() {
  const res = await postAPI("/api/waypoints", waypoints);
  if (res) {
    updateWaypointCards();
    updateWaypointTree();
    renderPalletGrid();
    log("Waypoints saved to persistent configuration.", "ok");
  }
}

// -------------------------------------------------------------
// Event Handlers
// -------------------------------------------------------------
function setupEventListeners() {
  // IP Connection Handlers
  const handleConnect = async () => {
    const ip = robotIpInput.value.trim();
    if (!ip) return;

    log(`Connecting to controller at ${ip}...`, "sys");
    const res = await postAPI("/api/robot/connect", { ip });
    if (res && res.success) {
      log(`Connected to controller at ${ip}. State: READY`, "ok");
    } else {
      log(`Failed to connect to controller at ${ip}. Check IP/LAN cables.`, "err");
    }
  };

  if (btnConnect) btnConnect.addEventListener("click", handleConnect);
  if (robotIpInput) {
    robotIpInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") handleConnect();
    });
  }

  // Fault Reset / Recover
  if (btnResetFault) {
    btnResetFault.addEventListener("click", async () => {
      log("Resetting Fault / Recovering Robot...", "sys");
      const res = await postAPI("/api/robot/recover");
      if (res && res.success) {
        log("Robot Fault Reset Successfully. Status: READY", "ok");
      } else {
        log("Fault Reset Failed. Check physical E-Stop or power switch.", "err");
      }
    });
  }

  // Home & Zero buttons
  if (btnHeaderHome) {
    btnHeaderHome.addEventListener("click", async () => {
      log("Commanding Return to Home Position...", "sys");
      await postAPI("/api/robot/home");
    });
  }

  if (btnHeaderZero) {
    btnHeaderZero.addEventListener("click", async () => {
      log("Commanding Move to Zero Calibration Pose...", "sys");
      await postAPI("/api/robot/zero");
    });
  }

  // E-Stop
  if (btnEstop) {
    btnEstop.addEventListener("click", async () => {
      log("EMERGENCY STOP TRIGGERED (CAT1)", "err");
      await postAPI("/api/robot/stop");
    });
  }

  // Direct Teaching
  if (toggleDirectTeach) {
    toggleDirectTeach.addEventListener("change", async (e) => {
      const enable = e.target.checked;
      log(`Direct Teaching Mode: ${enable ? 'ACTIVE (COMPLIANT)' : 'INACTIVE'}`, "sys");
      await postAPI("/api/teaching/direct_mode", { enable });
    });
  }

  // Waypoints Set & Move
  if (btnCapturePick) {
    btnCapturePick.addEventListener("click", async () => {
      waypoints.pick_pose = [...currentPose];
      log(`Captured Pick Target: [${currentPose.map(x => x.toFixed(1)).join(", ")}]`, "ok");
      await saveWaypoints();
    });
  }

  if (btnCapturePlace) {
    btnCapturePlace.addEventListener("click", async () => {
      waypoints.place_pose = [...currentPose];
      log(`Captured Place Reference: [${currentPose.map(x => x.toFixed(1)).join(", ")}]`, "ok");
      await saveWaypoints();
    });
  }

  if (btnGotoPick) {
    btnGotoPick.addEventListener("click", async () => {
      log("Commanding Move to Pick Approach...", "sys");
      await postAPI("/api/robot/goto_pick");
    });
  }

  if (btnGotoPlace) {
    btnGotoPlace.addEventListener("click", async () => {
      log("Commanding Move to Place Approach...", "sys");
      await postAPI("/api/robot/goto_place");
    });
  }

  // Tool Actuation
  if (btnToggleGripper) {
    btnToggleGripper.addEventListener("click", async () => {
      isGripperClosed = !isGripperClosed;
      if (gripperBtnText) {
        gripperBtnText.textContent = `GRIPPER (DO #3): ${isGripperClosed ? 'CLOSED (GRIP)' : 'OPEN'}`;
      }
      btnToggleGripper.classList.toggle("active", isGripperClosed);
      log(`Digital Output 3 (Gripper): ${isGripperClosed ? 'HIGH (1 / CLOSED)' : 'LOW (0 / OPEN)'}`, "sys");
      await postAPI("/api/tool/gripper", { state: isGripperClosed });
    });
  }

  if (btnToggleVacuum) {
    btnToggleVacuum.addEventListener("click", async () => {
      isVacuumOn = !isVacuumOn;
      if (vacuumBtnText) {
        vacuumBtnText.textContent = `VACUUM (DO #0): ${isVacuumOn ? 'ON' : 'OFF'}`;
      }
      btnToggleVacuum.classList.toggle("active", isVacuumOn);
      log(`Digital Output 0 (Vacuum): ${isVacuumOn ? 'HIGH (1)' : 'LOW (0)'}`, "sys");
      await postAPI("/api/tool/vacuum", { state: isVacuumOn });
    });
  }

  if (btnPulseBlow) {
    btnPulseBlow.addEventListener("click", async () => {
      log("Digital Output 1: Air Blow-Off Pulse Triggered", "sys");
      await postAPI("/api/tool/blow_off");
    });
  }

  // Palletization Inputs & Run
  [palletRows, palletCols, palletDx, palletDy].forEach(input => {
    input.addEventListener("input", renderPalletGrid);
  });

  if (btnRunFullPallet) {
    btnRunFullPallet.addEventListener("click", async () => {
      const rows = parseInt(palletRows.value, 10);
      const cols = parseInt(palletCols.value, 10);
      const dx = parseFloat(palletDx.value);
      const dy = parseFloat(palletDy.value);

      log(`Commanding Full Pallet Execution (${rows}x${cols} Matrix)...`, "sys");
      await postAPI("/api/pallet/run", {
        rows,
        cols,
        layers: 1,
        dx,
        dy,
        dz: 30.0,
        pick_pose: waypoints.pick_pose,
        place_origin: waypoints.place_pose,
      });
    });
  }

  if (btnRunSelectedSlot) {
    btnRunSelectedSlot.addEventListener("click", async () => {
      const rows = parseInt(palletRows.value, 10);
      const cols = parseInt(palletCols.value, 10);
      const dx = parseFloat(palletDx.value);
      const dy = parseFloat(palletDy.value);

      log(`Commanding Single Pallet Slot [R${selectedPalletSlot.row+1}, C${selectedPalletSlot.col+1}]...`, "sys");
      await postAPI("/api/pallet/run", {
        rows,
        cols,
        layers: 1,
        dx,
        dy,
        dz: 30.0,
        pick_pose: waypoints.pick_pose,
        place_origin: waypoints.place_pose,
        target_slot: selectedPalletSlot,
      });
    });
  }

  // Sequence Run & Abort
  if (btnRunSequence) {
    btnRunSequence.addEventListener("click", async () => {
      const toolType = seqToolSelect ? seqToolSelect.value : "gripper";
      const repeatCount = seqRepeatSelect ? parseInt(seqRepeatSelect.value, 10) : 1;
      const clearanceZ = seqClearance ? parseFloat(seqClearance.value) : 50.0;
      const repeatLabel = repeatCount === 0 ? "Continuous Loop" : `${repeatCount} Cycle(s)`;

      log(`Executing Sequence: ${repeatLabel} | Tool: ${toolType.toUpperCase()} | Clearance: ${clearanceZ}mm...`, "sys");
      if (btnAbortSequence) btnAbortSequence.style.display = "block";

      await postAPI("/api/sequence/run", {
        pick_pose: waypoints.pick_pose,
        place_pose: waypoints.place_pose,
        tool_type: toolType,
        repeat_count: repeatCount,
        clearance_z: clearanceZ,
      });
    });
  }

  if (btnAbortSequence) {
    btnAbortSequence.addEventListener("click", async () => {
      log("Aborting Running Sequence...", "err");
      await postAPI("/api/sequence/abort");
      btnAbortSequence.style.display = "none";
    });
  }

  // Clear Logs
  if (btnClearLog) {
    btnClearLog.addEventListener("click", () => {
      if (consoleLogs) consoleLogs.innerHTML = "";
    });
  }
}

// -------------------------------------------------------------
// Initialization
// -------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  setupJogControls();
  setupEventListeners();
  loadWaypoints();
  connectWebSocket();
});

const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="workcell-token"]').content;
let state = null, historyTick = 0, palletKey = '', observedCommand = '', frameUrl = null;

async function post(path, body) {
  const response = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json', 'X-Workcell-Token':token}, body:JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  $('command-result').textContent = data.command_id ? `Request ${data.command_id} accepted. Waiting for controller result…` : data.message;
}
function handle(fn) { return async () => { try { await fn(); } catch(error) { $('command-result').textContent = error.message; } }; }
for (const action of ['enable','disable','start','stop']) $(action).onclick = handle(() => post('/api/commands', {action}));
function recovery(action, extra={}) { return post('/api/commands', {action, note:$('note').value, inspected:$('inspected').checked, ...extra}); }
$('reset').onclick = handle(() => recovery('reset'));
$('replace-pallet').onclick = handle(() => recovery('replace_pallet'));
$('reconcile').onclick = handle(() => recovery('reconcile', {slot:Number($('unknown-slot').value), occupied:$('occupancy').value==='true'}));
$('apply-scenario').onclick = handle(() => post('/api/simulation', {part:$('sim-part').value, fault:$('sim-fault').value}));

function renderPallet(data) {
  const key = JSON.stringify(data.slots);
  if (key === palletKey) return;
  palletKey = key;
  $('pallet').replaceChildren();
  for (let layer=0; layer<data.layers; layer++) {
    const wrapper = document.createElement('div'); wrapper.className='layer';
    const title=document.createElement('div'); title.className='layer-title'; title.textContent=`LAYER ${layer+1}`;
    const grid=document.createElement('div'); grid.className='slots'; grid.style.gridTemplateColumns=`repeat(${data.columns},1fr)`;
    const floorSize=data.columns*data.rows;
    for (const slot of data.slots.slice(layer*floorSize,(layer+1)*floorSize)) {
      const tile=document.createElement('div'); tile.className=`slot ${slot.status.toLowerCase()}`;
      const num=document.createElement('span'); num.textContent=String(slot.id+1).padStart(2,'0');
      const status=document.createElement('span'); status.textContent=slot.status;
      tile.append(num,status); grid.append(tile);
    }
    wrapper.append(title,grid); $('pallet').append(wrapper);
  }
  $('unknown-slot').replaceChildren();
  for (const slot of data.slots.filter(s=>s.status==='UNKNOWN')) {
    const option=document.createElement('option'); option.value=slot.id; option.textContent=`Slot ${slot.id+1}`; $('unknown-slot').append(option);
  }
}
async function renderHistory() {
  const response=await fetch('/api/history'); if (!response.ok) return;
  const data=await response.json();
  if (!data.cycles.length) return;
  $('history').replaceChildren();
  for (const cycle of data.cycles) {
    const row=document.createElement('tr');
    for (const value of [`#${cycle.id}`,new Date(cycle.started).toLocaleTimeString(),cycle.part.replaceAll('_',' '),cycle.slot===null?'Magazine':`Slot ${cycle.slot+1}`,cycle.status,cycle.error||'—']) {
      const td=document.createElement('td'); td.textContent=value; row.append(td);
    }
    $('history').append(row);
  }
}
async function refreshFrame() {
  const response=await fetch('/api/frame');
  if (!response.ok) { $('camera-unavailable').hidden=false; return; }
  const blob=await response.blob(); const next=URL.createObjectURL(blob);
  $('camera').src=next; $('camera-unavailable').hidden=true;
  if (frameUrl) URL.revokeObjectURL(frameUrl); frameUrl=next;
}
async function poll() {
  try {
    const response=await fetch('/api/status'); if(!response.ok) throw new Error('Status unavailable');
    state=await response.json(); $('connection-error').hidden=true;
    $('mode').textContent=state.mode.toUpperCase(); $('source').textContent=state.mode==='simulation'?'SYNTHETIC RGB-D':'REALSENSE RGB-D';
    $('mode-description').textContent=state.mode==='simulation'?'Simulation mode · no robot, PLC, or camera connections.':state.mode==='observe'?'Observation mode · real device reads; motion and PLC writes disabled.':'Automatic mode · physical robot motion is enabled.';
    $('state').textContent=state.state.replaceAll('_',' ');
    $('fault').hidden=!state.fault; $('fault').textContent=state.fault||'';
    $('robot-status').textContent=state.devices.robot?.connected ? (state.mode==='simulation'?'SIMULATED':'CONNECTED'):'OFFLINE';
    const plc=state.devices.plc;
    $('plc-status').textContent=!plc?.connected?'OFFLINE':plc.estop?'E-STOP ACTIVE':plc.permit?'PERMITTED':'NOT PERMITTED';
    $('count').textContent=`${state.slots.filter(s=>s.status==='OCCUPIED').length} / ${state.capacity}`;
    $('part').textContent=state.detection ? state.detection.part.replaceAll('_',' ') : 'No accepted part';
    $('confidence').textContent=state.detection ? `Quality ${(100*state.detection.confidence).toFixed(0)}% · ${state.detection.age_s.toFixed(1)}s old`:'—';
    $('vision-error').textContent=state.camera_error||'Classification selects a route. Pickup uses the taught fixture position.';
    $('config-hash').textContent=`CONFIG ${state.config_hash}`;
    $('simulation').hidden=state.mode!=='simulation';
    const busy=state.pending||!['DISABLED','READY','FAULT','WAITING_FOR_PALLET_CHANGE'].includes(state.state);
    $('enable').disabled=busy||state.enabled||!!state.fault||!state.initialized||state.mode==='observe';
    $('start').disabled=busy||state.state!=='READY';
    $('disable').disabled=busy||!state.enabled;
    $('apply-scenario').disabled=busy;
    for(const id of ['reset','replace-pallet','reconcile']) $(id).disabled=busy||state.enabled;
    if(!state.slots.some(s=>s.status==='UNKNOWN')) $('reconcile').disabled=true;
    if(state.last_command && state.last_command.id!==observedCommand) {
      observedCommand=state.last_command.id;
      $('command-result').textContent=state.last_command.error||`Request ${observedCommand}: ${state.last_command.status}.`;
    }
    renderPallet(state);
    await refreshFrame();
    if(historyTick++%3===0) await renderHistory();
  } catch(error) {
    $('connection-error').hidden=false;
    for(const id of ['enable','start','disable','apply-scenario','reset','replace-pallet','reconcile']) $(id).disabled=true;
  } finally { setTimeout(poll,500); }
}
poll();

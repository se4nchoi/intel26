"""Factory I/O Numerical stacker: one S, one pallet per cycle (PyModbus 3.11)."""
from dataclasses import dataclass
from pathlib import Path
import json
import time

MASK = ('#########', '#........', '#########', '........#', '........#', '#########')
TARGETS = (46,47,48,49,50,51,52,53,54,45,36,35,34,33,32,31,30,29,28,19,10,1,2,3,4,5,6,7,8,9)
USED_COILS = (0,1,2,3,4,8,9,10,11)

@dataclass
class Settings:
    host: str = '192.168.0.117'
    port: int = 502
    device_id: int = 1
    poll: float = 0.05
    stable: float = 0.15
    pulse: float = 0.2
    feed_timeout: float = 30
    fork_timeout: float = 20
    lift_timeout: float = 15
    motion_timeout: float = 90
    motion_start_timeout: float = 5

class ControlFault(RuntimeError):
    pass

class ModbusIO:
    def __init__(self, settings):
        from pymodbus.client import ModbusTcpClient
        self.settings = settings
        self.client = ModbusTcpClient(settings.host, port=settings.port, timeout=1, retries=0)
        if not self.client.connect():
            self.client.close()
            raise ConnectionError(f'Modbus connection failed: {settings.host}:{settings.port}')

    @staticmethod
    def checked(response):
        if response.isError():
            raise ConnectionError(str(response))
        return response

    def inputs(self):
        return tuple(self.checked(self.client.read_discrete_inputs(
            0, count=8, device_id=self.settings.device_id)).bits[:8])

    def coils(self):
        return tuple(self.checked(self.client.read_coils(
            0, count=12, device_id=self.settings.device_id)).bits[:12])

    def coil(self, address, value):
        self.checked(self.client.write_coil(address, bool(value), device_id=self.settings.device_id))

    def target(self, number):
        if type(number) is not int or (number != 99 and not 1 <= number <= 54):
            raise ValueError('Target must be an integer: 1..54 or home=99')
        self.checked(self.client.write_register(0, number, device_id=self.settings.device_id))

    def close(self):
        self.client.close()

class StackerController:
    def __init__(self, io, settings=None, log_dir='logs', clock=time.monotonic, sleep=time.sleep):
        self.io = io
        self.cfg = settings or Settings()
        self.clock, self.sleep = clock, sleep
        self.state, self.completed = 'NEW', []
        self.stop_requested = False
        self.log = None
        if log_dir is not None:
            directory = Path(log_dir)
            directory.mkdir(parents=True, exist_ok=True)
            self.log = directory / (time.strftime('%Y%m%d-%H%M%S') + f'-{time.time_ns()%1000000:06d}.jsonl')

    def event(self, state, **extra):
        self.state = state
        record = dict(time=time.time(), state=state, completed=len(self.completed), **extra)
        print(json.dumps(record, ensure_ascii=False), flush=True)
        if self.log:
            with self.log.open('a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False)+'\n')

    def sample(self):
        bits = self.io.inputs()
        if self.stop_requested or bits[7]:
            raise ControlFault('Reset/stop: reset the Factory I/O scene before a new run')
        if sum(bool(bits[i]) for i in (3,4,5)) > 1:
            raise ControlFault('Conflicting fork limit inputs')
        return bits

    def wait(self, predicate, timeout, label, stable=None):
        stable = self.cfg.stable if stable is None else stable
        deadline, since = self.clock()+timeout, None
        while True:
            bits, now = self.sample(), self.clock()
            if predicate(bits):
                if since is None:
                    since = now
                if now-since >= stable:
                    return bits
            else:
                since = None
            if now >= deadline:
                raise ControlFault(f'Timeout: {label}; inputs={bits}')
            self.sleep(self.cfg.poll)

    def delay(self, seconds):
        deadline = self.clock()+seconds
        while self.clock() < deadline:
            self.sample()
            self.sleep(max(0, min(self.cfg.poll, deadline-self.clock())))

    def stopped(self, bits):
        return not bits[1] and not bits[2]

    def centered(self, bits):
        return bits[5] and not bits[3] and not bits[4]

    def fork(self, direction):
        if direction not in ('left', 'right'):
            raise ValueError('Fork direction must be left or right')
        bits = self.sample()
        if not self.stopped(bits):
            raise ControlFault('Cannot extend fork while X/Z is moving')
        address, limit = (1,3) if direction == 'left' else (2,4)
        if not self.centered(bits):
            raise ControlFault('Fork must start at Middle Limit')
        self.io.coil(3, False)
        self.io.coil(2 if address == 1 else 1, False)
        self.io.coil(address, True)
        self.wait(lambda b: b[limit] and not b[5], self.cfg.fork_timeout, direction+' limit')

    def retract(self):
        if not self.stopped(self.sample()):
            raise ControlFault('Cannot retract before lift movement completes')
        self.io.coil(1, False)
        self.io.coil(2, False)
        self.wait(self.centered, self.cfg.fork_timeout, 'Middle Limit')

    def lift(self, up):
        self.io.coil(0, up)
        self.wait(lambda b: b[2], self.cfg.motion_start_timeout, 'lift movement start', stable=0)
        self.wait(self.stopped, self.cfg.lift_timeout, 'lift movement end')
        self.delay(.25)

    def move(self, number):
        bits = self.sample()
        if not self.centered(bits) or not self.stopped(bits):
            raise ControlFault('Travel requires centered fork and stopped X/Z')
        self.io.target(number)
        self.wait(lambda b: b[1] or b[2], self.cfg.motion_start_timeout, 'travel movement start', stable=0)
        self.wait(self.stopped, self.cfg.motion_timeout, 'travel movement end')
        self.delay(.25)

    def abort(self):
        """Stop transport and retain crane outputs; simulator Pause stops active travel.

        Numerical target=0 does not cancel a previously commanded movement.
        The provided IO contains no crane emergency-stop actuator.
        """
        failures = []
        for address in (10,3,4,8,9,11):
            try:
                self.io.coil(address, False)
            except Exception as exc:
                failures.append(str(exc))
        return failures

    def run(self, *, empty_scene_confirmed=False, wait_for_start=True, targets=TARGETS):
        if not empty_scene_confirmed:
            raise ValueError('First reset Factory I/O to an empty scene, then explicitly confirm it')
        if self.state != 'NEW':
            raise ControlFault('Create a new controller after scene reset; resume is disabled')
        targets = tuple(targets)
        if not targets or len(set(targets)) != len(targets) or any(type(n) is not int or not 1<=n<=54 for n in targets):
            raise ValueError('Targets must be unique integers in 1..54')
        try:
            initial = self.sample()
            if not self.centered(initial) or not self.stopped(initial) or initial[0]:
                raise ControlFault('Initial scene must be empty, stopped, and fork centered')
            for address in USED_COILS:
                self.io.coil(address, False)
            self.io.target(99)
            self.wait(lambda b: self.centered(b) and self.stopped(b), 10, 'initial home')
            self.event('IDLE', targets=list(targets))
            if wait_for_start:
                # Require a release followed by a fresh press; a held button cannot auto-start.
                self.wait(lambda b: not b[6], 86400, 'Start release')
                self.wait(lambda b: b[6], 86400, 'Start press', stable=0)
            for number in targets:
                self.event('FEED', target=number)
                self.wait(lambda b: not b[0], 5, 'Sensor clear before feed')
                for address in (8,9,11,3):
                    self.io.coil(address, True)
                self.io.coil(10, True)
                self.delay(self.cfg.pulse)
                self.io.coil(10, False)
                self.wait(lambda b: b[0], self.cfg.feed_timeout, 'Sensor', stable=0)
                self.io.coil(3, False)
                self.delay(.25)
                self.event('PICK_LEFT', target=number)
                self.fork('left')
                self.lift(True)
                self.retract()
                self.event('TRAVEL', target=number)
                self.move(number)
                self.event('PLACE_RIGHT', target=number)
                self.fork('right')
                self.lift(False)
                self.retract()
                self.event('RETURN_HOME', target=number)
                self.move(99)
                self.completed.append(number)
                self.event('CYCLE_DONE', target=number)
            for address in USED_COILS:
                self.io.coil(address, False)
            self.event('DONE', targets=self.completed)
            return list(self.completed)
        except BaseException as exc:
            failures = self.abort()
            self.event('FAULT', error=str(exc), stop_write_errors=failures)
            raise
        finally:
            self.io.close()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default=Settings.host)
    parser.add_argument('--empty-scene-confirmed', action='store_true')
    parser.add_argument('--start-now', action='store_true', help='Commissioning only: bypass physical Start')
    args = parser.parse_args()
    config = Settings(host=args.host)
    if not args.empty_scene_confirmed:
        parser.error('Reset the scene first, then pass --empty-scene-confirmed')
    StackerController(ModbusIO(config), config).run(
        empty_scene_confirmed=True, wait_for_start=not args.start_now)

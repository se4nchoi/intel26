import contextlib
import io as textio
import unittest
from controller import Settings, StackerController, ModbusIO, ControlFault, TARGETS, MASK

class Plant:
    """Independent deterministic IO plant: delayed limit/motion acknowledgements."""
    def __init__(self, missing_motion=False, reset_on_travel=False):
        self.now = 0.
        self.b = [False]*8
        self.b[5] = True
        self.c = [False]*12
        self.events, self.commands = [], []
        self.missing_motion, self.reset_on_travel = missing_motion, reset_on_travel
        self.closed = False
        self.motion_count = 0

    def schedule(self, delay, index, value):
        self.events.append((self.now+delay, index, value))

    def sleep(self, seconds):
        self.now += seconds

    def inputs(self):
        due = sorted(e for e in self.events if e[0] <= self.now)
        self.events = [e for e in self.events if e[0] > self.now]
        for _, index, value in due:
            self.b[index] = value
        return tuple(self.b)

    def coil(self, index, value):
        old = self.c[index]
        self.c[index] = value
        self.commands.append(('coil',index,value))
        if old == value:
            return
        if index == 10 and value:
            self.schedule(.5,0,True)
        if index in (1,2):
            if value:
                self.schedule(.05,5,False)
                self.schedule(.3,3 if index==1 else 4,True)
            else:
                self.schedule(.05,3 if index==1 else 4,False)
                self.schedule(.3,5,True)
                if index==1:
                    self.schedule(.2,0,False)
        if index==0:
            self.schedule(.05,2,True)
            self.schedule(.3,2,False)

    def target(self, number):
        self.commands.append(('target',number))
        if number==99 and self.motion_count==0:
            return
        self.motion_count += 1
        if self.reset_on_travel:
            self.schedule(.1,7,True)
        if not self.missing_motion:
            self.schedule(.05,1,True)
            self.schedule(.4,1,False)

    def close(self):
        self.closed = True

class Tests(unittest.TestCase):
    def test_target_rejects_noninteger_and_nonstorage_commands_before_io(self):
        adapter=ModbusIO.__new__(ModbusIO)
        for value in (True, 1.5, '1', 0, -1, 55, 100):
            with self.subTest(value=value), self.assertRaises(ValueError):
                adapter.target(value)

    def test_invalid_fork_direction_does_not_write_output(self):
        p=Plant()
        with self.assertRaises(ValueError): self.controller(p).fork('typo')
        self.assertEqual(p.commands,[])

    def controller(self, plant):
        return StackerController(plant, Settings(motion_start_timeout=1, feed_timeout=1),
            log_dir=None, clock=lambda:plant.now, sleep=plant.sleep)

    def test_full_s_has_30_distinct_cells_and_one_pulse_each(self):
        p=Plant(); c=self.controller(p)
        result=c.run(empty_scene_confirmed=True,wait_for_start=False)
        self.assertEqual(result,list(TARGETS))
        expected={(z-1)*9+(10-x) for z,row in zip(range(6,0,-1),MASK)
                  for x,ch in enumerate(row,1) if ch=='#'}
        self.assertEqual(set(result),expected)
        self.assertEqual(sum(cmd==('coil',10,True) for cmd in p.commands),30)
        self.assertEqual([cmd[1] for cmd in p.commands if cmd[0]=='target'],
                         [99]+[n for target in TARGETS for n in (target,99)])
        self.assertFalse(any(p.c))
        self.assertTrue(p.closed)

    def test_no_motion_start_never_extends_place_fork(self):
        p=Plant(missing_motion=True);c=self.controller(p)
        with self.assertRaisesRegex(ControlFault,'travel movement start'):
            c.run(empty_scene_confirmed=True,wait_for_start=False,targets=(1,))
        self.assertNotIn(('coil',2,True),p.commands)
        self.assertEqual(c.completed,[])
        self.assertFalse(p.c[10] or p.c[3] or p.c[8])
        self.assertTrue(p.c[0])  # Abort preserves the load's lift state.
        self.assertTrue(p.closed)

    def test_reset_during_travel_latches_fault_without_auto_home(self):
        p=Plant(reset_on_travel=True);c=self.controller(p)
        with self.assertRaisesRegex(ControlFault,'Reset/stop'):
            c.run(empty_scene_confirmed=True,wait_for_start=False,targets=(1,))
        self.assertEqual([x for x in p.commands if x[0]=='target'],[('target',99),('target',1)])
        self.assertNotIn(('coil',2,True),p.commands)
        self.assertEqual(c.state,'FAULT')

    def test_interlocks_reject_travel_with_extended_fork(self):
        p=Plant();p.b[5]=False;p.b[3]=True
        with self.assertRaises(ControlFault): self.controller(p).move(1)
        self.assertEqual(p.commands,[])

    def test_explicit_empty_scene_required_before_output(self):
        p=Plant()
        with self.assertRaises(ValueError):self.controller(p).run()
        self.assertEqual(p.commands,[])

    def test_held_start_requires_release_then_new_press(self):
        p=Plant();p.b[6]=True;p.schedule(.5,6,False);p.schedule(1,6,True)
        c=self.controller(p)
        c.run(empty_scene_confirmed=True,targets=(1,))
        self.assertGreater(p.now,1)
        self.assertEqual(c.completed,[1])

if __name__=='__main__':
    with contextlib.redirect_stdout(textio.StringIO()):
        unittest.main(verbosity=2)

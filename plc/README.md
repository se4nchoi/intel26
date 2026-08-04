# PLC and Automation

Course notes, controller projects, HMI screens, and practical-exam artifacts from the Intel-26 K-DT PLC module. The material focuses on Mitsubishi MELSEC-Q controllers (primarily the Q02H CPU), GX Works2 ladder programming, and GP-Pro EX operator-interface design.

## What is here

```text
plc/
├── archive_gxw/       GX Works2 exercises and reference projects
├── course_exam/       Final practical-exam PLC and HMI files
├── hmi-screens/       GP-Pro EX HMI projects
├── notes/             Dated lecture and lab notes
├── solidworks/        CAD practice files
├── exam_practice.gxw  PLC exam-practice project
├── hmi-multi-program_cylinder.gxw
└── plc-io-map.xlsx    I/O mapping and reference workbook
```

## Topics covered

- PLC hardware, I/O modules, sensors, relays, motors, and solenoid valves
- Ladder logic, self-holding circuits, interlocks, and `SET`/`RST`
- Timers, counters, data registers, index registers, and word operations
- Boolean logic, binary and hexadecimal values, bitmasks, shifts, and rotation
- Sequence control, master control, jumps, subroutines, and multiple programs
- Labels, retained variables, and function blocks
- Conveyor, pneumatic-cylinder, analog-I/O, encoder, positioning, and servo concepts
- Ethernet configuration and industrial communication basics
- HMI controls, animation, alarms, diagnostics, and PLC synchronization
- Practical panel wiring and three-phase motor-control exercises

## File formats and software

| Extension | Contents | Typical software |
| --- | --- | --- |
| `.gxw` | PLC ladder and sequence projects | Mitsubishi GX Works2 |
| `.prx` | HMI screens and configuration | Pro-face GP-Pro EX |
| `.SLDPRT`, `.SLDDRW` | Part and drawing models | SOLIDWORKS |
| `.xlsx` | I/O maps and reference tables | Excel-compatible spreadsheet software |
| `.txt`, `.md` | Lecture notes | Any text editor |

The proprietary project files are preserved as course artifacts and generally require their corresponding Windows engineering software to open. Review the I/O assignments and target hardware configuration before downloading any project to a physical PLC.

## Suggested path through the material

Start with the self-holding, flip-flop, and interlock projects in `archive_gxw/`. Continue with timers, counters, word/bit operations, and `STEP_SEQUENCE.gxw`, then move to labeled programs, function blocks, Ethernet, and the HMI projects. The dated files in `notes/` provide classroom context for the exercises.

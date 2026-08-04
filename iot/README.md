# IoT and Edge Computing

Notes and practice projects from the Intel-26 K-DT IoT module. The current material begins with development environments, Linux networking, computer and circuit fundamentals, and C++ preparation before moving toward Arduino, Raspberry Pi, and edge-computing work.

## What is here

```text
iot/
├── July/
│   ├── 0720/   Python tooling, virtual environments, and cloud/MLOps context
│   ├── 0721/   Ubuntu VM setup, SSH, web/database services, and networking
│   ├── 0727/   Computer architecture, binary data, and circuit fundamentals
│   └── 0728/   Signed data, two's complement, transistors, and motor control
├── Aug/
│   ├── 0803/   C++ environment and language introduction
│   └── 0804/   C++ and Python project-based practice
├── library-simulator-py/   PySide6 and SQLite desktop application
├── windows-calculator-py/  PySide6 expression calculator
└── README.md
```

## Topics covered

- Python environment management with `uv`
- VirtualBox Ubuntu guests, NAT networking, port forwarding, and static IPs
- SSH, Nginx/Apache, MariaDB, and basic Linux service administration
- CPU organization, memory, binary and hexadecimal representation, and overflow
- Digital logic, pull-up/pull-down circuits, transistors, and PWM motor control
- C++ syntax, headers, libraries, CLI/GUI concepts, and cross-language comparison
- Arduino, Raspberry Pi, GPIO, and edge-computing concepts (introduced as the module direction)

## Practice applications

### [Library Simulator](library-simulator-py/)

A Windows-compatible PySide6 application with a service layer and persistent SQLite database. It includes member and administrator roles, catalogue management, borrowing and returns, automated service tests, and a PyInstaller build script. See its README for setup instructions and demo accounts.

### [Windows Calculator](windows-calculator-py/)

A PySide6 calculator with editable expressions, standard operator precedence, light and dark themes, calculation history, and automated tests. Its parser uses `Decimal` and does not rely on Python's `eval()`. See its README for the `uv`-based setup and controls.

## Using the materials

The dated note files can be read with any text editor. The two desktop projects have independent dependencies and setup instructions, so create and use their project-local virtual environments rather than installing packages globally.

The folder represents an in-progress course archive: early lessons are foundational preparation, and not every item is a hardware IoT implementation yet. When working with mains voltage, motors, PLCs, or other physical hardware, follow the equipment documentation and appropriate electrical-safety procedures.

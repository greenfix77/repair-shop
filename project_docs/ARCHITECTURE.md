# Current Architecture

Current Status

The application is partially prepared for modularization.

Current structure:

project_root/
│
├── app.py
│
├── repair_manager/
│   ├── main.py
│   ├── config/
│   ├── core/
│   └── ui/
│
└── project_docs/

Current state:

- app.py contains almost all application code.
- repair_manager/core exists but is not yet used.
- repair_manager/ui exists but is not yet used.
- repair_manager/config exists but is not yet used.
- main.py exists as future application entry point.
- Modular migration has not started yet.
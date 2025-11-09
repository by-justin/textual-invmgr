# Inventory Manager (TUI)

A fast, keyboard-friendly inventory manager that runs entirely in your terminal. Browse products, inspect details, manage a cart, place orders, and (as a sales user) view reports and maintain inventory. The app is self-contained, backed by a local SQLite database, and serves as a concise reference for building TUIs with Textual.

### Features at a glance
- Product search with detail view
- Add/remove items in a cart; adjust quantities
- Guided checkout with address capture and order summary
- Past orders view with totals
- Sales views for simple inventory management and sales reports
- Database initialized automatically from SQL scripts on first run

### Quick demo (optional)
If you have Asciinema installed, you can play the bundled demo cast:
```bash
asciinema play demo/demo.cast
```

### Tech Stack
- Language: Python (>= 3.12)
- UI: Textual (`textual`, `textual-dev`)
- Database: SQLite (`data/db.sqlite`) and `aiosqlite`
- Tooling: `ruff`, `pre-commit`

### Requirements
- Python 3.12 or newer
- macOS/Linux/Windows terminal
- Ability to install packages from `requirements.txt`

Optional (for development convenience)
- `uv` (fast Python package manager)

### Setup
Choose one of the following setups.

Option A — using uv
```bash
# from project root
uv run src/main.py
```

Option B — using pip
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 src/main.py

# with live reload (for dev only) 
textual run --dev src/main.py
```


### Database
- File: `data/db.sqlite`
- On first run, the app initializes the database if the `users` table does not exist by executing scripts in order:
  - `src/db/prj-tables.sql`
  - `src/db/views-triggers.sql`
  - `src/db/dummy-data.sql`
  (see `src/db/database.py`)

Resetting the database
```bash
rm -f data/db.sqlite
python3 src/main.py  # re-initializes from SQL scripts
```

To test the code with your dataset instead of the dummy data, modify the `src/db/database.py` file to use your dataset.  
Delete the dummy data to start from fresh.


### Tests
Automated backend tests are included and run against an isolated temporary SQLite database.

Run the full test suite:
```bash
pytest -q
```


### Common Tasks / Scripts

Pre-commit will handle the code formating and standardization at commit.
```bash
pre-commit install
pre-commit run --all-files
```

### Documentation
- System overview and user guide: docs/system_overview_user_guide.md
- Detailed software design (architecture/modules/schema): docs/detailed_software_design.md
- Testing strategy and example test cases: docs/testing_strategy.md
- Team work and coordination (breakdown, time allocation, progress, coordination): docs/teamwork_coordination.md
- Consolidated report (Markdown): designDoc.md (exported PDF: designDoc.pdf)


### License
This project is licensed under the terms of the license found in the `LICENSE` file.
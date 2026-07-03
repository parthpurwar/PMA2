# PMO Resource Management Platform

A complete FastAPI application for PMO-controlled resource allocation with separate production and temporary SQLite databases.

## What is included

- PMO and Project Lead authentication with session management
- Role-based dashboards and navigation
- Main database and synchronized temporary working database
- Demand creation, resource matching, recommendation ranking, and reservation
- Future resource blocking with overlap validation and PMO approval
- Three-month availability calendars inside the resource Block dialog
- Employee login, self-managed profile, CV uploads, and CV reminder workflow
- Detailed clickable employee pages with personal details, experience, skills, and project history
- Lead "My Resources" view with extension alerts and blocked-resource tracking
- PDF CV upload and viewing on resource tables
- Role-based demand matching across resource, recommendation, approval, and report views
- PMO approval, rejection, and modification workflow
- Production updates only after PMO approval
- Audit logs for approved requests
- Reports for resources, projects, demand history, utilization, skill availability, and allocations
- Seeded sample users, projects, resources, and allocations

## Demo users

- PMO: `pmo` / `pmo123`
- Project Lead: `lead1` / `lead123`
- Project Lead: `lead2` / `lead123`

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:8000 in your browser.

The application creates `data/main.db` and `data/temp.db` automatically on startup.

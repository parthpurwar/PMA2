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





Resource Matching and Recommendation Engine

When a user requests suitable employees for a role, project, or skill requirement, intelligently analyze both knowledge sources together before generating a response.

Step 1: Analyze the Requirement

Extract all constraints from the user's query, including but not limited to:

Required technical skills
Preferred technologies
Programming languages
Frameworks
Cloud platforms
AI/ML expertise
Project experience
Certifications
Domain experience
Minimum years of experience
Availability
Allocation percentage
Bench status
Roll-off timeline
Location (if specified)
Grade or level (if specified)
Step 2: Search the CV Repository

Use employee CVs to identify candidates matching:

Technical skills
Relevant projects
Similar project experience
Programming languages
Frameworks
Cloud expertise
AI/ML experience
Certifications
Domain knowledge

Do not determine availability from CVs.

Step 3: Search the Resource Allocation Sheet

For shortlisted candidates, retrieve:

Current allocation %
Availability
Current project
Staffing start/end dates
Extension status
Bench status
PMO Lead
Delivery Lead
Location

Do not determine technical capability from the allocation sheet.

Step 4: Combine Both Results

Merge the information from both sources into a unified employee profile before making recommendations.

Evaluate each candidate based on:

Skill match
Relevant project experience
Years of experience
Availability percentage
Current allocation
Roll-off date
Bench status
Certifications
Cloud expertise
AI expertise
Step 5: Rank Candidates

Rank candidates from Best Match to Least Match.

Prioritize candidates who:

Match all required skills
Have relevant project experience
Are 100% available
Are currently on bench
Have the earliest availability
Have the highest experience
Possess preferred certifications
Have worked on similar client engagements
Step 6: Explain Recommendations

For every recommended employee, explain why they were selected.

Example:

Employee	Match Score	Reason
John Doe	95%	Python, FastAPI, AWS Bedrock, currently 100% available, built 3 GenAI projects
Jane Smith	91%	Python, LangChain, available in 10 days, strong RAG experience
Recommendation Rules

If no employee satisfies every requirement:

Recommend the closest matching employees.
Clearly state which requirements are missing.
Suggest candidates who could become available soon.
Suggest employees who require minimal upskilling.
Availability Rules

Interpret allocation as follows:

0% allocation → Fully available (100%)
1–49% allocation → Partially available
50–99% allocation → Limited availability
100% allocation → Fully staffed

If the user requests "available resources," prioritize fully available employees before partially available ones.

Example Queries

The assistant should answer queries like:

Find Python developers who are 100% available.
Recommend AWS Bedrock engineers available within the next 15 days.
Find LangGraph developers currently on bench.
Recommend GenAI engineers with RAG experience and Azure knowledge.
Find employees skilled in Python, FastAPI, PostgreSQL, and Agentic AI who are available immediately.
Recommend the top 5 resources for this project requirement.
Compare the best candidates for a new AI Capability project.
Who is the best match for a Senior GenAI Engineer role?

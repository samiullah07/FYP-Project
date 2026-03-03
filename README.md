# AI Outreach Lead Generator

Turn live job postings into ready-to-send cold outreach emails and LinkedIn DMs for your AI and engineering services in a single run.

This Actor searches multiple public job APIs (Remotive, Jobicy, Arbeitnow), extracts key details for each role, and uses an LLM to generate personalized outreach you can plug directly into your CRM, email tool, or LinkedIn workflow. [web:74][web:107][web:109]

## Why use this Actor?

- **Multi-source coverage**: Pulls roles from Remotive, Jobicy, and Arbeitnow so you are not dependent on a single board. [web:74][web:107][web:109]
- **AI-native outbound**: Every job becomes a structured lead with tailored email copy and LinkedIn DMs focused on LLM agents, data pipelines, and automation.
- **Fast lead lists**: Configure once, run, and export a dataset of ready-to-contact companies in minutes.

## Input configuration

The Actor uses an input schema, so you can configure it from Apify Console without code. Key fields:

- **Role keywords** (`keywords`, required, array of strings)  
  Example: `["LLM", "AI engineer", "automation", "data engineer"]`  
  Used to filter job titles and descriptions from all sources. [web:79]

- **Locations** (`locations`, optional, array of strings)  
  Example: `["US", "UK", "Remote"]`.  
  Leave empty to search all locations the APIs return. [web:74]

- **Max number of jobs** (`max_results`, required, integer)  
  Total number of unique leads to generate outreach for, after merging and deduplication across sources.  
  Default: `10`.

- **Remote only** (`remote_only`, optional, boolean)  
  When supported by the API, restricts results to remote roles.  
  Default: `true`.

- **Seniority level filter** (`seniority`, optional, string)  
  Free-text filter such as `"junior"`, `"mid"`, `"senior"` applied in your own post-processing.

- **Outreach language** (`language`, optional, string)  
  Language for generated outreach (currently optimized for English).  
  Default: `"English"`.

- **Job sources** (`job_sources`, optional, array of strings)  
  Choose which APIs to use:  
  - `"remotive"` – Remote-friendly tech jobs. [web:74]  
  - `"jobicy"` – Curated remote jobs feed. [web:107]  
  - `"arbeitnow"` – Aggregated jobs from multiple ATS-powered career pages. [web:109]  
  Default: `["remotive"]`.

The Actor also expects the secret environment variable **`GROQ_API_KEY`** to be set, used for calling the Groq LLM API that generates outreach content.

## Output

Each lead is stored as one item in the default dataset with at least:

- `type`: `"lead"`  
- `source`: `"remotive" | "jobicy" | "arbeitnow"`  
- `keyword`: keyword that matched  
- `location`: location string from the job listing  
- `company_name`  
- `job_title`  
- `job_url`  
- `snippet`: short text snippet from the description  
- `summary`: 2–3 sentence explanation of why this is a promising AI/automation lead  
- `emails`: list of objects with `subject` and `body` for cold emails  
- `linkedin_messages`: list of short DM texts

Example item:

{
"type": "lead",
"source": "jobicy",
"keyword": "engineer",
"location": "Remote, Europe",
"company_name": "Example Labs",
"job_title": "Senior AI Engineer",
"job_url": "https://example.com/jobs/123",
"snippet": "We are looking for an engineer to build AI-powered features...",
"summary": "...",
"emails": [
{ "subject": "...", "body": "..." }
],
"linkedin_messages": [
{ "message": "..." }
]
}


The last dataset item is a `run_metadata` record summarizing the run:

- `type`: `"run_metadata"`  
- `total_leads`: number of outreach leads generated  
- `keyword_used`, `locations_used`, `generated_at`

Use the **Dataset** tab to inspect items and the **Export** button to download JSON, CSV, or Excel. [web:38]

## How to use

1. Open the Actor in Apify and go to the **Input** tab.
2. Fill in:
   - 3–5 **role keywords** that match the work you want (e.g., LLM, AI agent, data engineer).
   - Optional **locations** (or leave empty for global).
   - **Max number of jobs** (start with 5–10 while testing).
   - Choose one or more **job sources** (Remotive, Jobicy, Arbeitnow).
3. Click **Start** and wait for the run to finish.
4. Open **Output → All outreach leads** or **Storage → Dataset** to review the generated leads and outreach copy.
5. Export as CSV/JSON and plug into your email tool, CRM, or LinkedIn workflow. [web:83]

For best results, lightly edit the generated messages to match your voice and portfolio before sending.

## Notes and limitations

- Job availability depends on the external APIs; some queries or locations may yield few or no results. [web:74][web:107][web:109]
- This Actor focuses on outbound sales for AI/data/automation services and is not a general job-application tool.
- Always respect job-board terms and anti-spam regulations when using the generated outreach.


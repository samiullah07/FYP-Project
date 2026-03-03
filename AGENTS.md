# AI Outreach Lead Generator

Turn live job postings into ready-to-send cold outreach emails and LinkedIn DMs for your AI services in one run.

## What this Actor does

- Finds open tech roles that match your **AI / data / automation skills** using a public jobs API.
- Extracts the company, role, and context from each listing.
- Generates **personalized outreach emails and LinkedIn messages** positioning you or your team as the solution.
- Stores everything in the run dataset so you can export to CSV, Sheets, or your CRM.

## Typical use cases

- Solo AI freelancers looking for a steady stream of warm companies to contact.
- Small agencies selling AI agents, data automation, or MLOps services.
- Developers validating demand for a new AI product by seeing who is hiring for related skills.

## Input

You configure the Actor through a simple form:

- **Role keywords** (`keywords`, required, array of strings)  
  Example: `["LLM", "AI agent", "MLOps", "data engineer"]`  
  Used to match relevant job titles and descriptions.

- **Locations** (`locations`, optional, array of strings)  
  Example: `["US", "Canada", "Remote"]`.  
  Leave empty to search all available locations.

- **Max number of jobs** (`max_results`, required, integer)  
  Maximum number of job posts to process in one run.  
  Default: `10`.

- **Remote only** (`remote_only`, optional, boolean)  
  If enabled, restricts results to remote roles when supported.  
  Default: `true`.

- **Seniority level filter** (`seniority`, optional, string)  
  Example: `"junior"`, `"mid"`, `"senior"`.  
  Leave empty for any level.

- **Outreach language** (`language`, optional, string)  
  Language of the generated outreach messages.  
  Default: `"English"`.

This Actor also expects the secret environment variable **`GROQ_API_KEY`** to be set in the Apify console or via `apify secrets`. The key is used to call the Groq LLM API to generate outreach content.

## Output

Each dataset item represents one job and its outreach package, for example:


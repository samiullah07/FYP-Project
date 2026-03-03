"""Module defines the main entry point for the Apify Actor.

To build Apify Actors, utilize the Apify SDK toolkit:
https://docs.apify.com/sdk/python
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import os
import json
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from apify import Actor
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Lead:
    source: str
    keyword: str
    location: str | None
    company_name: str | None
    job_title: str | None
    job_url: str | None
    snippet: str | None


@dataclass
class OutreachPack:
    lead: Lead
    summary: str
    emails: list[str]
    linkedin_messages: list[str]


async def fetch_job_signals(
    keywords: list[str],
    locations: list[str],
    max_results: int,
) -> list[Lead]:
    leads: list[Lead] = []

    if not keywords:
        return leads

    # Use first keyword for API search; all for later filtering if needed
    search_term = keywords[0]
    params = {"search": search_term}

    async with httpx.AsyncClient(timeout=15.0) as client:
        url = "https://remotive.com/api/remote-jobs"
        Actor.log.info(f"Fetching jobs from Remotive: {url} with params {params}")

        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
        except Exception as e:
            Actor.log.warning(f"Failed to fetch Remotive API: {e}")
            return leads

        data = resp.json()
        jobs = data.get("jobs", [])

        # Normalize locations filter
        loc_filters = [loc.lower() for loc in locations] if locations else []

        for job in jobs:
            if len(leads) >= max_results:
                break

            candidate_loc = job.get("candidate_required_location") or ""
            candidate_loc_lower = candidate_loc.lower()

            # If user provided locations, keep only matching ones
            if loc_filters and not any(l in candidate_loc_lower for l in loc_filters):
                continue

            company_name = job.get("company_name")
            job_title = job.get("title")
            job_url = job.get("url")
            snippet_html = job.get("description") or ""
            snippet_text = BeautifulSoup(
                snippet_html, "html.parser"
            ).get_text(" ", strip=True)[:400]

            lead = Lead(
                source="remotive",
                keyword=search_term,
                location=candidate_loc,
                company_name=company_name,
                job_title=job_title,
                job_url=job_url,
                snippet=snippet_text,
            )
            leads.append(lead)

    return leads


async def fetch_jobicy_signals(
    keywords: list[str],
    locations: list[str],
    max_results: int,
) -> list[Lead]:
    leads: list[Lead] = []
    if not keywords:
        return leads

    search_term = keywords[0]
    url = "https://jobicy.com/api/v2/remote-jobs"
    params = {"tag": search_term}

    async with httpx.AsyncClient(timeout=15.0) as client:
        Actor.log.info(f"Fetching jobs from Jobicy: {url} with params {params}")
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
        except Exception as e:
            Actor.log.warning(f"Failed to fetch Jobicy API: {e}")
            return leads

        data = resp.json()
        jobs = data.get("jobs", [])

        loc_filters = [loc.lower() for loc in locations] if locations else []

        for job in jobs:
            if len(leads) >= max_results:
                break

            candidate_loc = job.get("jobGeo") or job.get("jobRegion") or ""
            candidate_loc_lower = candidate_loc.lower()
            if loc_filters and not any(l in candidate_loc_lower for l in loc_filters):
                continue

            company_name = job.get("companyName")
            job_title = job.get("jobTitle")
            job_url = job.get("url")
            snippet_html = job.get("jobDescription") or ""
            snippet_text = BeautifulSoup(
                snippet_html, "html.parser"
            ).get_text(" ", strip=True)[:400]

            leads.append(
                Lead(
                    source="jobicy",
                    keyword=search_term,
                    location=candidate_loc,
                    company_name=company_name,
                    job_title=job_title,
                    job_url=job_url,
                    snippet=snippet_text,
                )
            )

    return leads

async def fetch_arbeitnow_signals(
    keywords: list[str],
    locations: list[str],
    max_results: int,
) -> list[Lead]:
    leads: list[Lead] = []
    if not keywords:
        return leads

    search_term = keywords[0]
    url = "https://www.arbeitnow.com/api/job-board-api"  # note www + https

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        Actor.log.info(f"Fetching jobs from Arbeitnow: {url}")
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except Exception as e:
            Actor.log.warning(f"Failed to fetch Arbeitnow API: {e}")
            return leads

        data = resp.json()
        jobs = data.get("data", [])


        loc_filters = [loc.lower() for loc in locations] if locations else []

        for job in jobs:
            if len(leads) >= max_results:
                break

            title = job.get("title") or ""
            description = job.get("description") or ""
            text_lower = (title + " " + description).lower()
            if not any(k.lower() in text_lower for k in keywords):
                continue

            locations_list = job.get("location", []) or []

        # Some responses return location as a list of single characters; fix that.
            if locations_list and all(len(x) == 1 for x in locations_list):
                candidate_loc = "".join(locations_list).strip()
            else:
                candidate_loc = ", ".join(locations_list)

            candidate_loc_lower = candidate_loc.lower()

            if loc_filters and not any(l in candidate_loc_lower for l in loc_filters):
                continue

            company_name = job.get("company")
            job_url = job.get("url")
            snippet_text = BeautifulSoup(
                description, "html.parser"
            ).get_text(" ", strip=True)[:400]

            leads.append(
                Lead(
                    source="arbeitnow",
                    keyword=search_term,
                    location=candidate_loc,
                    company_name=company_name,
                    job_title=title,
                    job_url=job_url,
                    snippet=snippet_text,
                )
            )

    return leads

# Groq client (expects GROQ_API_KEY in env)
groq_client = Groq()


async def generate_outreach_for_leads(
    leads: list[Lead],
    email_style: str,
    max_emails_per_lead: int,
    max_dms_per_lead: int,
) -> list[OutreachPack]:
    packs: list[OutreachPack] = []

    if not leads:
        return packs

    for lead in leads:
        base_desc = (
            f"Company: {lead.company_name or 'Unknown'}\n"
            f"Job title or signal: {lead.job_title or 'Unknown'}\n"
            f"URL: {lead.job_url or 'N/A'}\n"
            f"Snippet: {lead.snippet or ''}\n"
        )
        SERVICE_DESC = (
                        "I design and build LLM-powered agents, data pipelines, and workflow automation "
                        "for SaaS and tech companies, as a solo freelance AI engineer.")


        prompt = (
            "You are a B2B sales assistant helping an AI engineer who sells services "
            "for building LLM-powered agents, data pipelines, and automation workflows for companies.\n\n"
            "Input lead:\n"
            f"{base_desc}\n\n"
            f"{SERVICE_DESC}\n\n"
            f"Email tone: {email_style}.\n\n"
            "Based on this lead, do the following:\n"
            "1) Write a 2–3 sentence summary of why this is a promising lead for AI / data automation services.\n"
            "2) Then write 3 cold outreach emails (4–6 sentences each) explicitly pitching AI agents, data pipelines, "
            "or workflow automation relevant to the lead.\n"
            "3) Then write 3 very short LinkedIn DMs (1–2 sentences each) that can be sent as connection follow-ups.\n\n"
            "Important rules:\n"
            "- Do not invent company details; only use the information in the input.\n"
            "- Do not include markdown or code fences in the response.\n\n"
            "Return ONLY JSON with this structure (no markdown, no explanations):\n"
            "{\n"
            "  \"summary\": \"...\",\n"
            "  \"emails\": [\n"
            "    {\"subject\": \"...\", \"body\": \"...\"}\n"
            "  ],\n"
            "  \"linkedin_messages\": [\n"
            "    {\"message\": \"...\"}\n"
            "  ]\n"
            "}\n"
           
        )


        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        raw = completion.choices[0].message.content or ""
        text = raw.strip()
        if text.startswith("```"):
            text = text.lstrip("`")
            if "\n" in text:
                text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0].strip()

        try:
            parsed = json.loads(text)
        except Exception:
            parsed = {
                "summary": text,
                "emails": [],
                "linkedin_messages": [],
            }
        
                # Normalize placeholders in generated text
        def normalize_placeholders(s: str) -> str:
            return (
                s.replace("[Name]", "{first_name}")
                 .replace("[Lead's Name]", "{first_name}")
                 .replace("[First Name]", "{first_name}")
                 .replace("[First Name]", "{first_name}")
                 .replace("[Your Name]", "{your_name}")
                 .replace("[Sr. Data Scientist's Name]", "{first_name}")
                 .replace("[Recipient]", "{first_name}")
            )

        for email in parsed.get("emails", []):
            if "subject" in email:
                email["subject"] = normalize_placeholders(email["subject"])
            if "body" in email:
                email["body"] = normalize_placeholders(email["body"])

        for msg in parsed.get("linkedin_messages", []):
            if "message" in msg:
                msg["message"] = normalize_placeholders(msg["message"])



        emails = parsed.get("emails", [])[:max_emails_per_lead]
        linkedin_messages = parsed.get("linkedin_messages", [])[:max_dms_per_lead]

        pack = OutreachPack(
            lead=lead,
            summary=parsed.get("summary", ""),
            emails=emails,
            linkedin_messages=linkedin_messages,
        )
        packs.append(pack)

    return packs


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}

        keywords = actor_input.get("keywords", [])
        locations = actor_input.get("locations", [])
        max_results = actor_input.get("max_results", 30)
        email_style = actor_input.get("email_style", "balanced")
        use_jobs_source = actor_input.get("use_jobs_source", True)
        max_emails_per_lead = actor_input.get("max_emails_per_lead", 3)
        max_dms_per_lead = actor_input.get("max_dms_per_lead", 3)
        job_sources = actor_input.get("job_sources", ["remotive"])


        Actor.log.info(f"Input keywords: {keywords}")
        Actor.log.info(f"Input locations: {locations}")
        Actor.log.info(f"Max results: {max_results}")
        Actor.log.info(f"Email style: {email_style}")
        Actor.log.info(f"Use jobs source: {use_jobs_source}")
        Actor.log.info(f"Max emails per lead: {max_emails_per_lead}")
        Actor.log.info(f"Max DMs per lead: {max_dms_per_lead}")

        all_leads: list[Lead] = []

        max_leads_per_source = actor_input.get("max_leads_per_source", 20)
        skip_llm_if_no_snippet = actor_input.get("skip_llm_if_no_snippet", True)


        if use_jobs_source:
            if "remotive" in job_sources:
                job_leads = await fetch_job_signals(keywords, locations, max_leads_per_source)
                Actor.log.info(f"Fetched {len(job_leads)} job-based leads from Remotive.")
                all_leads.extend(job_leads)

            if "jobicy" in job_sources:
                jobicy_leads = await fetch_jobicy_signals(keywords, locations, max_leads_per_source)
                Actor.log.info(f"Fetched {len(jobicy_leads)} job-based leads from Jobicy.")
                all_leads.extend(jobicy_leads)

            if "arbeitnow" in job_sources:
                arbeit_leads = await fetch_arbeitnow_signals(keywords, locations, max_leads_per_source)
                Actor.log.info(f"Fetched {len(arbeit_leads)} job-based leads from Arbeitnow.")
                all_leads.extend(arbeit_leads)

        # dedupe and cap
        seen = set()
        unique_leads: list[Lead] = []
        for lead in all_leads:
            key = (lead.company_name, lead.job_title, lead.job_url)
            if key in seen:
                continue
            seen.add(key)
            unique_leads.append(lead)

        all_leads = unique_leads[:max_results]

        required_tech = [k.lower() for k in actor_input.get("required_tech_keywords", [])]
        exclude_company = [k.lower() for k in actor_input.get("exclude_company_keywords", [])]

        filtered_leads: list[Lead] = []
        for lead in all_leads:
            text = (lead.company_name or "") + " " + (lead.snippet or "")
            text_lower = text.lower()

            if exclude_company and any(k in text_lower for k in exclude_company):
                continue

            if required_tech and not any(k in text_lower for k in required_tech):
                continue

            filtered_leads.append(lead)

        all_leads = filtered_leads
        if skip_llm_if_no_snippet:
            all_leads = [l for l in all_leads if (l.snippet or "").strip()]


        outreach_packs = await generate_outreach_for_leads(
            all_leads,
            email_style,
            max_emails_per_lead,
            max_dms_per_lead,
        )
        Actor.log.info(f"Generated outreach for {len(outreach_packs)} leads.")
        campaign_name = actor_input.get("campaign_name", "")
        your_name = actor_input.get("your_name", "")

        for pack in outreach_packs:
            lead_dict = asdict(pack.lead)

            score = 0
            # keyword match strength
            if lead_dict["keyword"]:
                score += 30
            # remote preference
            if actor_input.get("remote_only", True) and lead_dict["location"] and "remote" in lead_dict["location"].lower():
                score += 30
            # tech keyword hits
            text = (lead_dict["company_name"] or "") + " " + (lead_dict["snippet"] or "")
            hits = sum(1 for k in required_tech if k in text.lower())
            score += min(hits * 10, 40)

            tags: list[str] = []
            if "remote" in (lead_dict["location"] or "").lower():
                tags.append("remote")
            if any(w in (lead_dict["job_title"] or "").lower() for w in ["senior", "lead", "principal"]):
                tags.append("senior")
            if hits:
                tags.append("tech-match")
            
            

            await Actor.push_data(
                {
                    "type": "lead",
                    "source": lead_dict["source"],
                    "keyword": lead_dict["keyword"],
                    "location": lead_dict["location"],
                    "company_name": lead_dict["company_name"],
                    "job_title": lead_dict["job_title"],
                    "job_url": lead_dict["job_url"],
                    "snippet": lead_dict["snippet"],
                    "summary": pack.summary,
                    "emails": pack.emails,
                    "linkedin_messages": pack.linkedin_messages,
                    "fit_score": score,
                    "tags": tags,
                    "campaign_name": campaign_name,
                    "your_name": your_name,
                }
            )

        Actor.log.info(f"Pushed {len(outreach_packs)} outreach packs to dataset.")

    


        # Push run metadata as the last item
        run_metadata = {
            "type": "run_metadata",
            "total_leads": len(outreach_packs),
            "keyword_used": keywords[0] if keywords else None,
            "locations_used": locations,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        await Actor.push_data(run_metadata)



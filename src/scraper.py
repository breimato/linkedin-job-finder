import hashlib
import re
from typing import TypedDict

import pandas as pd
from jobspy import scrape_jobs
from loguru import logger
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential
import logging

from .config import Settings


class JobPosting(TypedDict):
    job_id: str
    title: str
    company: str
    location: str
    is_remote: bool
    job_url: str
    site: str
    date_posted: str
    description: str
    salary_str: str
    easy_apply: bool


def _make_job_id(url: str) -> str:
    return hashlib.sha256(f"linkedin:{url}".encode()).hexdigest()


def _make_salary_str(row: pd.Series) -> str:
    min_a = row.get("min_amount")
    max_a = row.get("max_amount")
    currency = row.get("currency", "") or ""
    if pd.notna(min_a) and pd.notna(max_a):
        return f"{int(min_a / 1000)}k-{int(max_a / 1000)}k {currency}".strip()
    if pd.notna(min_a):
        return f"{int(min_a / 1000)}k+ {currency}".strip()
    return ""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=30, max=120),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logging.getLogger("tenacity"), logging.WARNING),
    reraise=True,
)
def _scrape(settings: Settings) -> pd.DataFrame:
    search = settings.search
    kwargs: dict = dict(
        site_name=["linkedin"],
        search_term=" OR ".join(search.keywords),
        location=search.location,
        distance=search.distance_miles,
        job_type=search.job_type,
        results_wanted=search.results_wanted,
        hours_old=search.hours_old,
        linkedin_fetch_description=True,
    )
    if search.is_remote:
        kwargs["is_remote"] = True
    return scrape_jobs(**kwargs)


def _apply_filters(df: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    search = settings.search

    df = df.dropna(subset=["job_url"])

    if search.exclude_keywords:
        pattern = "|".join(re.escape(kw) for kw in search.exclude_keywords)
        title_match = df["title"].str.contains(pattern, case=False, na=False)
        desc_match = df["description"].str.contains(pattern, case=False, na=False)
        df = df[~(title_match | desc_match)]

    if search.require_keywords_in_title:
        pattern = "|".join(re.escape(kw) for kw in search.require_keywords_in_title)
        df = df[df["title"].str.contains(pattern, case=False, na=False)]

    if search.salary_min > 0 and "min_amount" in df.columns:
        has_salary = df["min_amount"].notna() | df["max_amount"].notna()
        meets_salary = df["min_amount"].fillna(0) >= search.salary_min
        df = df[~has_salary | meets_salary]

    return df


def fetch_jobs(settings: Settings) -> list[JobPosting]:
    try:
        df = _scrape(settings)
    except Exception as exc:
        logger.error(f"Scraping fallido tras reintentos: {exc}")
        return []

    if df is None or df.empty:
        logger.info("LinkedIn no devolvió resultados")
        return []

    df = _apply_filters(df, settings)
    logger.debug(f"{len(df)} trabajos tras aplicar filtros")

    jobs: list[JobPosting] = []
    for _, row in df.iterrows():
        url = str(row.get("job_url", ""))
        if not url:
            continue
        jobs.append(
            JobPosting(
                job_id=_make_job_id(url),
                title=str(row.get("title", "")),
                company=str(row.get("company", "")),
                location=str(row.get("location", "")),
                is_remote=bool(row.get("is_remote", False)),
                job_url=url,
                site="linkedin",
                date_posted=str(row.get("date_posted", "")),
                description=str(row.get("description", ""))[:2000],
                salary_str=_make_salary_str(row),
                easy_apply=bool(row.get("easy_apply", False)),
            )
        )

    seen_urls: set[str] = set()
    unique: list[JobPosting] = []
    for job in jobs:
        if job["job_url"] not in seen_urls:
            seen_urls.add(job["job_url"])
            unique.append(job)

    return unique

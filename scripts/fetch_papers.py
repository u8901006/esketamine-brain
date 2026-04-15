#!/usr/bin/env python3
"""
Fetch latest Esketamine / TRD research papers from PubMed E-utilities API.
Keywords sourced from comprehensive_esketamine_medical_journals_pubmed_templates.md.
Targets esketamine-relevant journals across psychiatry, psychopharmacology,
translational neuroscience, anesthesiology, and pain medicine.
"""

import json
import sys
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import quote_plus

PUBMED_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

JOURNALS = [
    "American Journal of Psychiatry",
    "JAMA Psychiatry",
    "The Journal of Clinical Psychiatry",
    "Journal of Affective Disorders",
    "Journal of Psychiatric Research",
    "Depression and Anxiety",
    "Acta Psychiatrica Scandinavica",
    "Psychological Medicine",
    "General Hospital Psychiatry",
    "European Psychiatry",
    "Psychiatry Research",
    "Frontiers in Psychiatry",
    "CNS Spectrums",
    "World Journal of Biological Psychiatry",
    "BMC Psychiatry",
    "Asian Journal of Psychiatry",
    "CNS Drugs",
    "International Journal of Neuropsychopharmacology",
    "European Neuropsychopharmacology",
    "Neuropsychopharmacology",
    "Psychopharmacology",
    "Therapeutic Advances in Psychopharmacology",
    "Journal of Psychopharmacology",
    "Human Psychopharmacology",
    "Expert Opinion on Pharmacotherapy",
    "Current Neuropharmacology",
    "Frontiers in Pharmacology",
    "Clinical Drug Investigation",
    "Drug Design, Development and Therapy",
    "Pharmacology, Biochemistry and Behavior",
    "Current Medical Research and Opinion",
    "Biological Psychiatry",
    "Molecular Psychiatry",
    "Translational Psychiatry",
    "Brain Stimulation",
    "NeuroImage: Clinical",
    "Frontiers in Neuroscience",
    "Neuroscience and Biobehavioral Reviews",
    "International Journal of Molecular Sciences",
    "Frontiers in Molecular Neuroscience",
    "eBioMedicine",
    "Anesthesia and Analgesia",
    "Anesthesiology",
    "British Journal of Anaesthesia",
    "European Journal of Anaesthesiology",
    "Journal of Clinical Anesthesia",
    "BMC Anesthesiology",
    "Pediatric Anesthesia",
    "Regional Anesthesia and Pain Medicine",
    "Pain Medicine",
    "The Clinical Journal of Pain",
    "Journal of Pain Research",
    "Pain Reports",
    "Critical Care",
    "Annals of Intensive Care",
    "Journal of Intensive Care",
    "Sleep Medicine",
]

ESKETAMINE_KEYWORDS_CORE = [
    "esketamine",
    '"intranasal esketamine"',
    '"S-ketamine"',
    "Spravato",
]

TRD_KEYWORDS_CORE = [
    '"treatment-resistant depression"',
    "TRD",
    '"major depressive disorder"',
    "MDD",
]

SUICIDALITY_KEYWORDS = [
    "suicid*",
    '"suicidal ideation"',
    '"suicidal thoughts"',
    '"acute suicidal ideation or behavior"',
]

MAINTENANCE_KEYWORDS = [
    "maintenance",
    '"long-term"',
    "relapse",
    "safety",
    "tolerability",
]

MECHANISM_KEYWORDS = [
    "glutamate",
    "NMDA",
    "AMPA",
    "biomarker*",
    "neuroimag*",
    "fMRI",
    "EEG",
    "neuroplastic*",
    "synapt*",
]

COMPARATIVE_KEYWORDS = [
    "ketamine",
    '"racemic ketamine"',
    '"IV ketamine"',
    "comparison",
    "comparative",
]

PERIOPERATIVE_KEYWORDS = [
    "anesthe*",
    "analges*",
    "perioperat*",
    "postoperative",
    "pain",
    "sedation",
    "ICU",
    "sleep",
]

REALWORLD_KEYWORDS = [
    '"real-world"',
    "implementation",
    "barrier*",
    "utilization",
    "persistence",
    "adherence",
    '"quality of life"',
    "access",
]

CLINICAL_KEYWORDS = [
    "dissociation",
    "sedation",
    '"blood pressure"',
    "cognition",
    "response",
    "remission",
    '"rapid-acting antidepressant"',
]

HEADERS = {"User-Agent": "EsketamineBrainBot/1.0 (research aggregator)"}


def build_query(days: int = 7, max_journals: int = 25) -> str:
    journal_part = " OR ".join([f'"{j}"[Journal]' for j in JOURNALS[:max_journals]])

    esk_core = " OR ".join([f"{k}[Title/Abstract]" for k in ESKETAMINE_KEYWORDS_CORE])
    trd_core = " OR ".join([f"{k}[Title/Abstract]" for k in TRD_KEYWORDS_CORE])
    suic = " OR ".join([f"{k}[Title/Abstract]" for k in SUICIDALITY_KEYWORDS])
    maint = " OR ".join([f"{k}[Title/Abstract]" for k in MAINTENANCE_KEYWORDS])
    mech = " OR ".join([f"{k}[Title/Abstract]" for k in MECHANISM_KEYWORDS])
    comp = " OR ".join([f"{k}[Title/Abstract]" for k in COMPARATIVE_KEYWORDS])
    peri = " OR ".join([f"{k}[Title/Abstract]" for k in PERIOPERATIVE_KEYWORDS])
    rw = " OR ".join([f"{k}[Title/Abstract]" for k in REALWORLD_KEYWORDS])
    clin = " OR ".join([f"{k}[Title/Abstract]" for k in CLINICAL_KEYWORDS])

    lookback = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y/%m/%d")
    date_part = f'"{lookback}"[Date - Publication] : "3000"[Date - Publication]'

    query = (
        f"(({journal_part})) AND "
        f"(({esk_core}) OR "
        f"(({trd_core}) AND ({clin} OR {suic} OR {maint} OR {mech} OR {comp} OR {peri} OR {rw}))) AND "
        f"{date_part}"
    )
    return query


def search_papers(query: str, retmax: int = 50) -> list[str]:
    params = (
        f"?db=pubmed&term={quote_plus(query)}&retmax={retmax}&sort=date&retmode=json"
    )
    url = PUBMED_SEARCH + params
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        return data.get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"[ERROR] PubMed search failed: {e}", file=sys.stderr)
        return []


def fetch_details(pmids: list[str]) -> list[dict]:
    if not pmids:
        return []
    ids = ",".join(pmids)
    params = f"?db=pubmed&id={ids}&retmode=xml"
    url = PUBMED_FETCH + params
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=60) as resp:
            xml_data = resp.read().decode()
    except Exception as e:
        print(f"[ERROR] PubMed fetch failed: {e}", file=sys.stderr)
        return []

    papers = []
    try:
        root = ET.fromstring(xml_data)
        for article in root.findall(".//PubmedArticle"):
            medline = article.find(".//MedlineCitation")
            art = medline.find(".//Article") if medline else None
            if art is None:
                continue

            title_el = art.find(".//ArticleTitle")
            title = (
                (title_el.text or "").strip()
                if title_el is not None and title_el.text
                else ""
            )

            abstract_parts = []
            for abs_el in art.findall(".//Abstract/AbstractText"):
                label = abs_el.get("Label", "")
                text = "".join(abs_el.itertext()).strip()
                if label and text:
                    abstract_parts.append(f"{label}: {text}")
                elif text:
                    abstract_parts.append(text)
            abstract = " ".join(abstract_parts)[:2000]

            journal_el = art.find(".//Journal/Title")
            journal = (
                (journal_el.text or "").strip()
                if journal_el is not None and journal_el.text
                else ""
            )

            pub_date = art.find(".//PubDate")
            date_str = ""
            if pub_date is not None:
                year = pub_date.findtext("Year", "")
                month = pub_date.findtext("Month", "")
                day = pub_date.findtext("Day", "")
                parts = [p for p in [year, month, day] if p]
                date_str = " ".join(parts)

            pmid_el = medline.find(".//PMID")
            pmid = pmid_el.text if pmid_el is not None else ""
            link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

            keywords = []
            for kw in medline.findall(".//KeywordList/Keyword"):
                if kw.text:
                    keywords.append(kw.text.strip())

            authors = []
            for author in art.findall(".//AuthorList/Author")[:6]:
                last = author.findtext("LastName", "")
                fore = author.findtext("ForeName", "")
                if last:
                    authors.append(f"{last} {fore}".strip())
            if len(art.findall(".//AuthorList/Author")) > 6:
                authors.append("et al.")

            papers.append(
                {
                    "pmid": pmid,
                    "title": title,
                    "authors": "; ".join(authors),
                    "journal": journal,
                    "date": date_str,
                    "abstract": abstract,
                    "url": link,
                    "keywords": keywords,
                }
            )
    except ET.ParseError as e:
        print(f"[ERROR] XML parse failed: {e}", file=sys.stderr)

    return papers


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Esketamine/TRD papers from PubMed"
    )
    parser.add_argument("--days", type=int, default=7, help="Lookback days")
    parser.add_argument(
        "--max-papers", type=int, default=50, help="Max papers to fetch"
    )
    parser.add_argument("--output", default="-", help="Output file (- for stdout)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    query = build_query(days=args.days)
    print(
        f"[INFO] Searching PubMed for Esketamine/TRD papers from last {args.days} days...",
        file=sys.stderr,
    )

    pmids = search_papers(query, retmax=args.max_papers)
    print(f"[INFO] Found {len(pmids)} papers", file=sys.stderr)

    if not pmids:
        print("NO_CONTENT", file=sys.stderr)
        if args.json:
            print(
                json.dumps(
                    {
                        "date": datetime.now(timezone(timedelta(hours=8))).strftime(
                            "%Y-%m-%d"
                        ),
                        "count": 0,
                        "papers": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        return

    papers = fetch_details(pmids)
    print(f"[INFO] Fetched details for {len(papers)} papers", file=sys.stderr)

    output_data = {
        "date": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"),
        "count": len(papers),
        "papers": papers,
    }

    out_str = json.dumps(output_data, ensure_ascii=False, indent=2)

    if args.output == "-":
        print(out_str)
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out_str)
        print(f"[INFO] Saved to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()

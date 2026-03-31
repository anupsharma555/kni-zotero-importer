from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import requests

from .http_utils import build_retry_session
from .models import PubMedRecord


class PubMedClient:
    def __init__(self, api_key: str = "", tool: str = "KNI_Zotero_Importer", email: str = "", session: requests.Session | None = None) -> None:
        self.api_key = api_key
        self.tool = tool
        self.email = email
        self.session = session or build_retry_session()

    def fetch_by_pmid(self, pmid: str) -> PubMedRecord | None:
        params: dict[str, Any] = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "xml",
            "tool": self.tool,
        }
        if self.api_key:
            params["api_key"] = self.api_key
        if self.email:
            params["email"] = self.email
        response = self.session.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi", params=params, timeout=30)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        article = root.find(".//PubmedArticle")
        if article is None:
            return None

        title = _node_text(article.find(".//Article/ArticleTitle"))
        abstract_parts = [_node_text(node) for node in article.findall(".//Abstract/AbstractText")]
        journal = _node_text(article.find(".//Journal/Title"))
        volume = _node_text(article.find(".//JournalIssue/Volume"))
        issue = _node_text(article.find(".//JournalIssue/Issue"))
        pages = _node_text(article.find(".//Pagination/MedlinePgn"))
        date = _extract_pub_date(article)
        doi = ""
        pmcid = ""
        for article_id in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
            id_type = (article_id.attrib.get("IdType") or "").lower()
            if id_type == "doi":
                doi = (article_id.text or "").strip()
            if id_type == "pmc":
                pmcid = (article_id.text or "").strip()
        creators = _extract_creators(article)
        return PubMedRecord(
            pmid=pmid,
            title=title,
            abstract="\n\n".join(part for part in abstract_parts if part),
            journal=journal,
            volume=volume,
            issue=issue,
            pages=pages,
            date=date,
            doi=doi,
            pmcid=pmcid,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            creators=creators,
        )


def _node_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return "".join(node.itertext()).strip()


def _extract_pub_date(article: ET.Element) -> str:
    year = _node_text(article.find(".//JournalIssue/PubDate/Year"))
    month = _node_text(article.find(".//JournalIssue/PubDate/Month"))
    day = _node_text(article.find(".//JournalIssue/PubDate/Day"))
    medline = _node_text(article.find(".//JournalIssue/PubDate/MedlineDate"))
    if year:
        return "-".join(part for part in [year, month, day] if part)
    return medline


def _extract_creators(article: ET.Element) -> list[dict[str, str]]:
    creators: list[dict[str, str]] = []
    for author in article.findall(".//AuthorList/Author"):
        collective = _node_text(author.find("CollectiveName"))
        if collective:
            creators.append({"creatorType": "author", "name": collective})
            continue
        last_name = _node_text(author.find("LastName"))
        fore_name = _node_text(author.find("ForeName"))
        if last_name or fore_name:
            creators.append({"creatorType": "author", "firstName": fore_name, "lastName": last_name})
    return creators

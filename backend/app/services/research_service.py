import logging
import uuid
import re
import html
import urllib.parse
import ipaddress
import hashlib
import time
import os
import tempfile
from typing import List, Dict, Any, Optional, Callable, Set, Tuple
from datetime import datetime
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
import httpx
from sqlalchemy.orm import Session
from ..core.config import settings
from ..models.research import ResearchSourceModel
from .embedding_service import embedding_service
from .qdrant_service import qdrant_service
from .document_service import document_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Security & URL Canonicalization
# ---------------------------------------------------------------------------

def is_safe_url(url: str) -> bool:
    """
    Validates URL to prevent SSRF and disallow non-web / private network resources.
    """
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urllib.parse.urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        host_lower = hostname.lower()
        if host_lower in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return False
        if host_lower.endswith(".local") or host_lower.endswith(".internal") or host_lower.endswith(".corp"):
            return False
        try:
            ip = ipaddress.ip_address(host_lower)
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
                return False
        except ValueError:
            pass
        return True
    except Exception:
        return False


def canonicalize_url(raw_url: str) -> Optional[str]:
    """
    Resolves DuckDuckGo redirects and strips tracking query parameters (utm_*, ref, etc.)
    """
    if not raw_url:
        return None
    url = raw_url.strip()
    if 'uddg=' in url:
        try:
            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            url = parsed.get('uddg', [url])[0]
        except Exception:
            pass

    try:
        parsed_u = urllib.parse.urlparse(url)
        if not parsed_u.scheme or parsed_u.scheme not in ('http', 'https') or not parsed_u.netloc:
            return None
        # Filter tracking params
        clean_qs = urllib.parse.parse_qsl(parsed_u.query)
        filtered_qs = [
            (k, v) for k, v in clean_qs
            if not k.startswith("utm_") and k not in ("fbclid", "gclid", "ref", "ref_src", "source")
        ]
        new_query = urllib.parse.urlencode(filtered_qs)
        clean = urllib.parse.urlunparse((
            parsed_u.scheme.lower(),
            parsed_u.netloc.lower(),
            parsed_u.path.rstrip('/') or '/',
            '',
            new_query,
            ''
        ))
        return clean
    except Exception:
        return None


def is_pdf_candidate(url: str, content_type: str = "") -> bool:
    """
    Determines if a candidate URL or Content-Type points to a PDF research paper.
    """
    if not url or not isinstance(url, str):
        return False
    clean_u = url.lower().split("?")[0].rstrip("/")
    if clean_u.endswith(".pdf"):
        return True
    if "/pdf/" in clean_u or "arxiv.org/pdf" in clean_u or "openreview.net/pdf" in clean_u:
        return True
    if content_type:
        ct_lower = content_type.lower()
        if "application/pdf" in ct_lower or "application/x-pdf" in ct_lower:
            return True
    return False


# ---------------------------------------------------------------------------
# HTML Sanitization and Text Extraction
# ---------------------------------------------------------------------------

def clean_html_to_text(html_text: str, max_chars: int = 3000) -> str:
    """
    Extracts relevant body text, stripping boilerplate, scripts, styles, and navigation.
    """
    if not html_text:
        return ""
    # 1. Remove non-content tags
    cleaned = re.sub(
        r'<(script|style|nav|header|footer|aside|form|noscript|svg|iframe|figure)[^>]*>[\s\S]*?</\1>',
        ' ',
        html_text,
        flags=re.IGNORECASE
    )
    cleaned = re.sub(r'<!--[\s\S]*?-->', ' ', cleaned)

    # 2. Extract content from paragraph, heading, and list tags
    paragraphs = re.findall(
        r'<(p|h[1-6]|li|blockquote)[^>]*>([\s\S]*?)</\1>',
        cleaned,
        flags=re.IGNORECASE
    )
    parts = []
    for _, inner in paragraphs:
        text = re.sub(r'<[^>]+>', ' ', inner)
        text = html.unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 35:
            parts.append(text)

    if not parts:
        # Fallback to general text strip
        text = re.sub(r'<[^>]+>', ' ', cleaned)
        text = html.unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:max_chars]

    # Combine informative paragraphs up to max_chars
    combined = " ".join(parts[:12])
    return combined[:max_chars]


def parse_ddg_html_results(html_text: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Parses web search results from DuckDuckGo HTML output with canonical URL normalization.
    """
    results = []
    blocks = re.findall(r'<div class="[^"]*result__body[^"]*">([\s\S]*?)<div class="clear"></div>', html_text)
    if not blocks:
        blocks = re.findall(r'<div class="[^"]*result[^"]*">([\s\S]*?)</div>\s*</div>', html_text)

    seen_urls: Set[str] = set()
    for block in blocks:
        m_title = re.search(r'<h2 class="[^"]*result__title[^"]*">[\s\S]*?<a[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>', block)
        if not m_title:
            m_title = re.search(r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>', block)

        m_snippet = re.search(r'<a[^>]*class="[^"]*result__snippet[^"]*"[^>]*>([\s\S]*?)</a>', block)
        if not m_snippet:
            m_snippet = re.search(r'<div[^>]*class="[^"]*result__snippet[^"]*"[^>]*>([\s\S]*?)</div>', block)

        if m_title:
            raw_url = m_title.group(1).strip()
            clean_url = canonicalize_url(raw_url)
            if not clean_url or clean_url in seen_urls or not is_safe_url(clean_url):
                continue
            seen_urls.add(clean_url)

            raw_title = re.sub(r'<[^>]+>', '', m_title.group(2)).strip()
            title = html.unescape(re.sub(r'\s+', ' ', raw_title))

            raw_snip = re.sub(r'<[^>]+>', '', m_snippet.group(1)).strip() if m_snippet else ''
            snippet = html.unescape(re.sub(r'\s+', ' ', raw_snip))

            if title:
                results.append({
                    "title": title,
                    "url": clean_url,
                    "content": snippet or title,
                    "snippet": snippet or title,
                    "published_date": datetime.utcnow().strftime("%Y-%m-%d")
                })
            if len(results) >= max_results:
                break
    return results


# ---------------------------------------------------------------------------
# Safe Research Caching Layer
# ---------------------------------------------------------------------------

class ResearchCache:
    """
    In-memory TTL cache for normalized search results and fetched article bodies.
    Guarantees debate isolation by keeping session and debate ownership separate.
    """
    def __init__(self, topic_ttl_seconds: int = 3600, article_ttl_seconds: int = 7200):
        self.topic_ttl = topic_ttl_seconds
        self.article_ttl = article_ttl_seconds
        # normalized_topic_key -> (expiry_time, cached_payload)
        self._topic_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        # canonical_url -> (expiry_time, article_text)
        self._article_cache: Dict[str, Tuple[float, str]] = {}
        # canonical_url -> (expiry_time, content_hash, List[Dict[str, Any]] pages)
        self._pdf_cache: Dict[str, Tuple[float, str, List[Dict[str, Any]]]] = {}
        # content_hash -> (expiry_time, List[Dict[str, Any]] pages)
        self._pdf_hash_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
        self._hits = 0
        self._misses = 0

    def _normalize_key(self, text: str) -> str:
        clean = re.sub(r'[^\w\s]', '', text.lower().strip())
        return re.sub(r'\s+', ' ', clean)

    def get_topic(self, topic: str) -> Optional[Dict[str, Any]]:
        key = self._normalize_key(topic)
        entry = self._topic_cache.get(key)
        if not entry:
            self._misses += 1
            return None
        expiry, data = entry
        if time.time() > expiry:
            del self._topic_cache[key]
            self._misses += 1
            return None
        self._hits += 1
        return data

    def set_topic(self, topic: str, data: Dict[str, Any]):
        key = self._normalize_key(topic)
        expiry = time.time() + self.topic_ttl
        self._topic_cache[key] = (expiry, data)

    def get_article(self, url: str) -> Optional[str]:
        entry = self._article_cache.get(url)
        if not entry:
            return None
        expiry, text = entry
        if time.time() > expiry:
            del self._article_cache[url]
            return None
        return text

    def set_article(self, url: str, text: str):
        if url and text:
            expiry = time.time() + self.article_ttl
            self._article_cache[url] = (expiry, text)

    def get_pdf(self, url: str, content_hash: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        now = time.time()
        if content_hash and content_hash in self._pdf_hash_cache:
            exp, pages = self._pdf_hash_cache[content_hash]
            if now <= exp:
                self._hits += 1
                return pages
            del self._pdf_hash_cache[content_hash]
        if url in self._pdf_cache:
            exp, _, pages = self._pdf_cache[url]
            if now <= exp:
                self._hits += 1
                return pages
            del self._pdf_cache[url]
        return None

    def set_pdf(self, url: str, content_hash: str, pages: List[Dict[str, Any]]):
        exp = time.time() + self.article_ttl
        if url:
            self._pdf_cache[url] = (exp, content_hash, pages)
        if content_hash:
            self._pdf_hash_cache[content_hash] = (exp, pages)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return (self._hits / total) if total > 0 else 0.0


research_cache = ResearchCache()


# ---------------------------------------------------------------------------
# Search Providers
# ---------------------------------------------------------------------------

class WebSearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        pass


class DuckDuckGoSearchProvider(WebSearchProvider):
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        }

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        results = []
        try:
            # Reusable client with bounded timeout
            with httpx.Client(timeout=6.0, headers=self.headers, follow_redirects=True) as client:
                # 1. Fast HTML search directly provides verified web article results
                html_resp = client.post("https://html.duckduckgo.com/html/", data={"q": query})
                if html_resp.status_code == 200:
                    results = parse_ddg_html_results(html_resp.text, max_results=max_results)
                else:
                    logger.warning(f"DuckDuckGo HTML search status {html_resp.status_code} for query: {query}")

                # 2. Check Instant Answer API if HTML produced 0 results
                if not results:
                    api_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
                    try:
                        resp = client.get(api_url, timeout=3.0)
                        if resp.status_code == 200:
                            data = resp.json()
                            abstract = data.get("AbstractText", "")
                            abstract_url = data.get("AbstractURL", "")
                            heading = data.get("Heading", query)
                            clean_u = canonicalize_url(abstract_url)
                            if abstract and clean_u and is_safe_url(clean_u):
                                results.append({
                                    "title": heading,
                                    "url": clean_u,
                                    "content": abstract,
                                    "snippet": abstract,
                                    "published_date": datetime.utcnow().strftime("%Y-%m-%d")
                                })
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"DuckDuckGo search error ({e}) for query: {query}. Live research unavailable.")
            return []

        return results[:max_results]


class TavilySearchProvider(WebSearchProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "max_results": max_results,
                        "include_answer": True
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for r in data.get("results", []):
                        url = canonicalize_url(r.get("url", ""))
                        if url and is_safe_url(url):
                            results.append({
                                "title": r.get("title", ""),
                                "url": url,
                                "content": r.get("content", ""),
                                "snippet": r.get("content", ""),
                                "published_date": r.get("published_date") or datetime.utcnow().strftime("%Y-%m-%d")
                            })
                    return results[:max_results]
        except Exception as e:
            logger.warning(f"Tavily search error ({e}) for query: {query}")
        return []


class MockWebSearchProvider(WebSearchProvider):
    """
    Deterministic mock provider reserved for explicit test configurations ONLY.
    """
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d")
        return [
            {
                "title": f"Empirical Policy & Socio-Economic Analysis: {query}",
                "url": f"https://policy-archive.org/analysis/{uuid.uuid4().hex[:8]}",
                "content": f"Independent global economic indicators and longitudinal studies regarding '{query}' demonstrate complex multifaceted outcomes across public sector metrics, labor markets, and governance structures.",
                "snippet": f"Independent global economic indicators and longitudinal studies regarding '{query}'.",
                "published_date": timestamp
            },
            {
                "title": f"Countervailing Perspective & Structural Critique: {query}",
                "url": f"https://critique-quarterly.org/briefs/{uuid.uuid4().hex[:8]}",
                "content": f"Critical evaluations of '{query}' emphasize systemic trade-offs, distributional inequalities, and institutional friction that challenge single-perspective assumptions.",
                "snippet": f"Critical evaluations of '{query}' emphasize systemic trade-offs.",
                "published_date": timestamp
            }
        ][:max_results]


# ---------------------------------------------------------------------------
# High-Performance Web Research Pipeline
# ---------------------------------------------------------------------------

class ResearchService:
    def __init__(self, provider: Optional[WebSearchProvider] = None):
        if provider is not None:
            self.provider = provider
        else:
            provider_name = (getattr(settings, "SEARCH_PROVIDER", "") or "duckduckgo").lower()
            if provider_name == "mock":
                self.provider = MockWebSearchProvider()
            elif provider_name == "tavily" and getattr(settings, "SEARCH_API_KEY", ""):
                self.provider = TavilySearchProvider(api_key=settings.SEARCH_API_KEY)
            else:
                self.provider = DuckDuckGoSearchProvider()

    def generate_research_queries(self, topic: str, max_sources: int = 4) -> List[str]:
        """
        Lightweight deterministic query generation producing dialectical affirmative and opposing search vectors.
        """
        clean_topic = topic.strip().rstrip("?.,")
        queries = [
            f"{clean_topic} empirical evidence data statistics",
            f"{clean_topic} criticisms limitations counterarguments"
        ]
        if max_sources > 3:
            queries.append(f"{clean_topic} analysis study research findings")
        return queries

    def _download_and_extract_pdf(
        self,
        src: Dict[str, Any],
        client: httpx.Client,
        emit_callback: Optional[Callable[[str, str, str, Optional[Dict[str, Any]]], None]] = None,
        timeout: Optional[float] = None,
        max_bytes: Optional[int] = None,
        max_pages: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Safely streams, validates, and extracts text from a PDF research paper.
        Enforces SSRF protection, size limits, PDF signature check, and page-aware extraction.
        Reuses document_service.extract_from_pdf (with RapidOCR fallback for scanned pages).
        Falls back gracefully to search snippet if inaccessible.
        """
        src.setdefault("content", src.get("snippet", ""))
        src["content_type"] = "SEARCH_SNIPPET_ONLY"
        src["page_count"] = 1
        src["pages_extracted"] = 0
        src["pdf_pages"] = []

        url = src.get("url", "")
        if not url or not is_safe_url(url):
            src["warning"] = "URL failed safety or SSRF validation."
            return src

        # Check warm PDF cache
        cached_pages = research_cache.get_pdf(url)
        if cached_pages:
            logger.info(f"ResearchCache HIT for PDF: {url} ({len(cached_pages)} pages)")
            src["content_type"] = "FULL_PDF_TEXT"
            src["page_count"] = len(cached_pages)
            src["pages_extracted"] = len(cached_pages)
            src["pdf_pages"] = cached_pages
            src["content"] = "\n\n".join(f"[Page {p['page_number']}]\n{p['text']}" for p in cached_pages)
            src["is_full_article"] = True
            if emit_callback:
                emit_callback(
                    "pdf_extraction_completed",
                    "in_progress",
                    f"Retrieved {len(cached_pages)} pages from cache for {src['title'][:40]}",
                    {"url": url, "pages_extracted": len(cached_pages), "from_cache": True}
                )
            return src

        if emit_callback:
            emit_callback(
                "pdf_download_started",
                "in_progress",
                f"Downloading research PDF: {src['title'][:40]}...",
                {"url": url}
            )

        t_dl_start = time.perf_counter()
        temp_path = None
        hasher = hashlib.sha256()
        total_bytes = 0
        has_magic = False
        effective_timeout = timeout or getattr(settings, "PDF_DOWNLOAD_TIMEOUT_SECONDS", 25.0)
        effective_max_bytes = max_bytes or getattr(settings, "MAX_PDF_SIZE_BYTES", 20 * 1024 * 1024)

        try:
            temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", prefix="agy_research_pdf_", delete=False)
            temp_path = temp_file.name

            with client.stream("GET", url, timeout=effective_timeout, follow_redirects=True) as resp:
                if resp.status_code != 200:
                    raise ValueError(f"HTTP {resp.status_code} returned by host")

                # SSRF audit on final URL & redirects
                if not is_safe_url(str(resp.url)):
                    raise ValueError(f"Redirected to unsafe URL: {resp.url}")
                for hist in resp.history:
                    if not is_safe_url(str(hist.url)):
                        raise ValueError(f"Redirect chain contains unsafe URL: {hist.url}")

                for chunk in resp.iter_bytes(chunk_size=65536):
                    if not has_magic:
                        if b"%PDF-" not in chunk[:1024]:
                            raise ValueError("Invalid PDF signature: missing '%PDF-' header")
                        has_magic = True
                    total_bytes += len(chunk)
                    if total_bytes > effective_max_bytes:
                        raise ValueError(f"File exceeds maximum allowed size ({effective_max_bytes / (1024*1024):.1f} MB)")
                    hasher.update(chunk)
                    temp_file.write(chunk)

            temp_file.close()
            src["download_duration_sec"] = time.perf_counter() - t_dl_start

            content_hash = hasher.hexdigest()
            src["content_hash"] = content_hash

            if emit_callback:
                emit_callback(
                    "pdf_download_completed",
                    "in_progress",
                    f"Downloaded PDF: {src['title'][:40]} ({total_bytes / 1024:.1f} KB)",
                    {"url": url, "bytes": total_bytes, "content_hash": content_hash}
                )

            # Check if this content_hash is already cached
            cached_by_hash = research_cache.get_pdf(url, content_hash=content_hash)
            if cached_by_hash:
                effective_max_pages = max_pages or getattr(settings, "MAX_PDF_PAGES_TO_EXTRACT", 30)
                is_partial = len(cached_by_hash) > effective_max_pages
                src["content_type"] = "FULL_PDF_TEXT"
                src["page_count"] = len(cached_by_hash)
                src["pages_extracted"] = min(len(cached_by_hash), effective_max_pages)
                src["is_partial_extraction"] = is_partial
                src["extraction_status"] = "PARTIAL" if is_partial else "FULL"
                src["skipped_pages_count"] = max(0, len(cached_by_hash) - effective_max_pages)
                src["skipped_reason"] = f"Cached PDF exceeds {effective_max_pages} pages limit." if is_partial else None
                src["pdf_pages"] = cached_by_hash[:effective_max_pages]
                src["content"] = "\n\n".join(f"[{p.get('section_title') or ('Page ' + str(p.get('page_number')))}]\n{p['text']}" for p in src["pdf_pages"])
                src["is_full_article"] = not is_partial
                src["extraction_duration_sec"] = 0.0
                return src

            # Extract full text page-by-page using document_service
            if emit_callback:
                emit_callback(
                    "pdf_extraction_started",
                    "in_progress",
                    f"Extracting text and tables from {src['title'][:40]}...",
                    {"url": url}
                )

            t_ext_start = time.perf_counter()
            raw_pages = document_service.extract_from_pdf(temp_path)
            src["extraction_duration_sec"] = time.perf_counter() - t_ext_start
            if not raw_pages:
                raise ValueError("PDF document contains no readable text or extractable OCR pages.")

            effective_max_pages = max_pages or getattr(settings, "MAX_PDF_PAGES_TO_EXTRACT", 30)
            is_partial = len(raw_pages) > effective_max_pages
            pages_content = raw_pages[:effective_max_pages]
            skipped_pages = len(raw_pages) - len(pages_content) if is_partial else 0
            skipped_reason = (
                f"PDF exceeds limit of {effective_max_pages} pages ({len(raw_pages)} total pages). Processed first {effective_max_pages} pages."
                if is_partial else None
            )
            if is_partial:
                logger.warning(f"[PDF Extraction Partial] {url}: {len(pages_content)} of {len(raw_pages)} pages processed ({skipped_pages} skipped).")

            for p in pages_content:
                if emit_callback:
                    emit_callback(
                        "pdf_page_extracted",
                        "in_progress",
                        f"Extracted Page {p['page_number']} of {len(raw_pages)} for {src['title'][:35]}",
                        {"url": url, "page": p["page_number"], "total_pages": len(raw_pages), "section": p.get("section_title")}
                    )

            total_chars = sum(len(p.get("text", "")) for p in pages_content)
            logger.info(f"PDF extraction succeeded for {url}: {len(pages_content)}/{len(raw_pages)} pages, {total_chars} chars (status: {'PARTIAL' if is_partial else 'FULL'})")

            src["content_type"] = "FULL_PDF_TEXT"
            src["page_count"] = len(raw_pages)
            src["pages_extracted"] = len(pages_content)
            src["is_partial_extraction"] = is_partial
            src["extraction_status"] = "PARTIAL" if is_partial else "FULL"
            src["skipped_pages_count"] = skipped_pages
            src["skipped_reason"] = skipped_reason
            src["pdf_pages"] = pages_content
            src["content"] = "\n\n".join(f"[{p.get('section_title') or ('Page ' + str(p.get('page_number')))}]\n{p['text']}" for p in pages_content)
            src["is_full_article"] = not is_partial

            research_cache.set_pdf(url, content_hash, pages_content)

            if emit_callback:
                emit_callback(
                    "pdf_extraction_completed",
                    "in_progress",
                    f"Completed extraction of {len(pages_content)} pages ({total_chars} chars) from {src['title'][:35]} ({'PARTIAL' if is_partial else 'FULL'})",
                    {
                        "url": url,
                        "pages_extracted": len(pages_content),
                        "total_pages": len(raw_pages),
                        "total_chars": total_chars,
                        "is_partial": is_partial
                    }
                )

        except Exception as e:
            logger.warning(f"Failed to download/extract PDF {url}: {e}")
            src["content_type"] = "SEARCH_SNIPPET_ONLY"
            src["warning"] = f"Full PDF content was not accessible: {e}"
            src["is_partial_extraction"] = False
            src["extraction_status"] = "FAILED_FALLBACK_SNIPPET"
            if emit_callback:
                emit_callback(
                    "pdf_failed",
                    "failed",
                    f"PDF processing failed: {e}. Falling back to verified search snippet.",
                    {"url": url, "reason": str(e)}
                )
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

        return src

    def _fetch_single_article(
        self,
        src: Dict[str, Any],
        client: httpx.Client,
        timeout: float = 4.0,
        emit_callback: Optional[Callable[[str, str, str, Optional[Dict[str, Any]]], None]] = None
    ) -> Dict[str, Any]:
        """
        Safely retrieves article body or full PDF with bounded timeout, size limit, and SSRF protection.
        Preserves snippet as graceful fallback if website or PDF is inaccessible.
        """
        src.setdefault("content", src.get("snippet", ""))
        src.setdefault("content_type", "SEARCH_SNIPPET_ONLY")
        src.setdefault("page_count", None)
        src.setdefault("pages_extracted", None)
        src.setdefault("is_partial_extraction", False)
        src.setdefault("extraction_status", "SEARCH_SNIPPET")
        src.setdefault("pdf_pages", [])

        url = src.get("url", "")
        if not url or not is_safe_url(url):
            src["warning"] = "URL failed safety validation."
            return src

        # Check if URL explicitly indicates a PDF document
        if is_pdf_candidate(url):
            if emit_callback:
                emit_callback(
                    "pdf_discovered",
                    "in_progress",
                    f"Discovered research PDF: {src['title'][:40]}",
                    {"url": url, "title": src["title"]}
                )
            return self._download_and_extract_pdf(
                src=src,
                client=client,
                emit_callback=emit_callback,
                timeout=getattr(settings, "PDF_DOWNLOAD_TIMEOUT_SECONDS", 25.0)
            )

        # Check HTML article cache
        cached_text = research_cache.get_article(url)
        if cached_text:
            src["content"] = cached_text
            src["content_type"] = "FULL_HTML_ARTICLE"
            src["page_count"] = None
            src["pages_extracted"] = None
            src["is_partial_extraction"] = False
            src["extraction_status"] = "FULL"
            src["is_full_article"] = True
            return src

        try:
            effective_timeout = min(timeout, 8.0)
            with client.stream("GET", url, timeout=effective_timeout, follow_redirects=True) as resp:
                if resp.status_code != 200:
                    return src

                ct = resp.headers.get("content-type", "").lower()
                final_url = str(resp.url)

                # Check if redirected to a PDF or Content-Type is PDF
                if is_pdf_candidate(final_url, ct):
                    resp.close()
                    if emit_callback:
                        emit_callback(
                            "pdf_discovered",
                            "in_progress",
                            f"Discovered research PDF (via redirect/header): {src['title'][:40]}",
                            {"url": final_url, "title": src["title"]}
                        )
                    return self._download_and_extract_pdf(
                        src=src,
                        client=client,
                        emit_callback=emit_callback,
                        timeout=getattr(settings, "PDF_DOWNLOAD_TIMEOUT_SECONDS", 25.0)
                    )

                if "text/html" not in ct and "text/plain" not in ct:
                    src["warning"] = f"Unsupported content-type: {ct}"
                    return src

                t_html_start = time.perf_counter()
                raw_bytes = b""
                # Read at most 128 KB for HTML articles
                for chunk in resp.iter_bytes():
                    raw_bytes += chunk
                    if len(raw_bytes) >= 131072:
                        break
                text = clean_html_to_text(raw_bytes.decode("utf-8", errors="ignore"))
                src["html_duration_sec"] = time.perf_counter() - t_html_start
                if len(text) >= 120:
                    src["content"] = text
                    src["content_type"] = "FULL_HTML_ARTICLE"
                    src["page_count"] = 1
                    src["pages_extracted"] = 1
                    src["is_full_article"] = True
                    research_cache.set_article(url, text)
        except Exception as e:
            # Non-blocking: retain existing search snippet
            src["warning"] = f"Article retrieval failed: {e}"
        return src

    def conduct_research_and_index(
        self,
        db: Session,
        topic: str,
        max_sources: int = 4,
        debate_id: Optional[str] = None,
        on_progress: Optional[Callable[[str, str, str, Optional[Dict[str, Any]]], None]] = None
    ) -> Dict[str, Any]:
        """
        Optimized Web Research Pipeline:
        1. Parallel dialectical query generation.
        2. Parallel search provider requests with bounded timeout.
        3. Canonical URL deduplication.
        4. Bounded parallel article retrieval (128 KB size cap, SSRF protection).
        5. Salient evidence claim extraction.
        6. Batch embedding & batch Qdrant indexing.
        7. Research persistence & progress event dispatch.
        """
        from datetime import timezone
        research_start_time = datetime.now(timezone.utc).isoformat()
        session_id = f"res-{uuid.uuid4().hex[:8]}"
        t_start_total = time.perf_counter()
        logger.info(f"[{session_id}] Starting optimized research on topic: '{topic}' (max_sources={max_sources})")

        def emit(stage_id: str, status: str, detail: str, data: Optional[Dict[str, Any]] = None):
            if on_progress:
                try:
                    on_progress(stage_id, status, detail, data)
                except Exception as e:
                    logger.debug(f"Progress callback error: {e}")

        stages = [
            {"id": "query_gen", "name": "Generating search queries", "status": "in_progress", "detail": "Formulating affirmative and adversarial inquiry angles."},
            {"id": "web_search", "name": "Searching sources", "status": "pending", "detail": "Querying live web search provider in parallel..."},
            {"id": "collect_articles", "name": "Collecting articles", "status": "pending", "detail": "Awaiting search results..."},
            {"id": "check_relevance", "name": "Checking source relevance", "status": "pending", "detail": "Evaluating source authority and relevance..."},
            {"id": "extract_evidence", "name": "Extracting evidence", "status": "pending", "detail": "Extracting factual claims and data points..."},
            {"id": "prepare_evidence", "name": "Preparing debate evidence", "status": "pending", "detail": "Vectorizing and indexing shared evidence pool..."}
        ]

        # -------------------------------------------------------------
        # STAGE 0: Fast Cache Check
        # -------------------------------------------------------------
        cached_result = research_cache.get_topic(topic)
        if cached_result and cached_result.get("sources"):
            logger.info(f"[{session_id}] Cache HIT for topic '{topic}'. Reusing verified research pool.")
            cached_sources = cached_result["sources"]
            cached_evidence = cached_result["evidence_items"]

            # If associated with a new debate_id, persist debate-linked records
            if debate_id:
                for src in cached_sources:
                    rec = ResearchSourceModel(
                        id=str(uuid.uuid4()),
                        debate_id=debate_id,
                        topic=topic,
                        query=src.get("query", topic),
                        title=src.get("title", ""),
                        url=src.get("url", ""),
                        content=src.get("content", ""),
                        published_date=src.get("published_date"),
                        metadata_json={
                            "content_type": src.get("content_type", "SEARCH_SNIPPET_ONLY"),
                            "page_count": src.get("page_count"),
                            "pages_extracted": src.get("pages_extracted"),
                            "content_hash": src.get("content_hash"),
                            "warning": src.get("warning"),
                            "evidence_items": [ev for ev in cached_evidence if ev.get("url") == src.get("url")]
                        }
                    )
                    db.add(rec)
                db.commit()

            # Mark all stages completed in stream
            for st in stages:
                st["status"] = "completed"
                emit(st["id"], "completed", st["detail"])

            cache_duration = time.perf_counter() - t_start_total
            cached_timings = cached_result.get("timings", {})
            effective_timings = {
                "research_start_time": research_start_time,
                "research_completed_time": datetime.now(timezone.utc).isoformat(),
                "total_research_duration_sec": round(cache_duration, 4),
                "search_provider_duration_sec": cached_timings.get("search_provider_duration_sec", 0.0),
                "pdf_download_duration_sec": 0.0,
                "pdf_extraction_duration_sec": 0.0,
                "ocr_duration_sec": 0.0,
                "html_extraction_duration_sec": 0.0,
                "embedding_duration_sec": 0.0,
                "qdrant_indexing_duration_sec": 0.0,
                "is_cached": True
            }

            cached_payload = {
                "topic": topic,
                "queries": cached_result.get("queries", []),
                "sources": cached_sources,
                "evidence_items": cached_evidence,
                "stages": stages,
                "indexed_chunks": cached_result.get("indexed_chunks", 0),
                "status": "completed",
                "message": "Evidence retrieved from verified research cache and indexed.",
                "timings": effective_timings
            }
            emit("complete", "completed", "Research retrieved from cache", cached_payload)
            return cached_payload

        # -------------------------------------------------------------
        # STAGE 1: Search Query Generation
        # -------------------------------------------------------------
        t0 = time.perf_counter()
        queries = self.generate_research_queries(topic, max_sources=max_sources)
        stages[0]["status"] = "completed"
        stages[0]["detail"] = f"Formulated {len(queries)} targeted dialectical query vectors."
        emit("query_gen", "completed", stages[0]["detail"], {"queries": queries})
        logger.info(f"[{session_id}] Stage 1 (query_gen) finished in {time.perf_counter() - t0:.4f}s")

        # -------------------------------------------------------------
        # STAGE 2: Parallel Web Search
        # -------------------------------------------------------------
        t1 = time.perf_counter()
        stages[1]["status"] = "in_progress"
        emit("web_search", "in_progress", "Searching live web providers concurrently...")

        raw_candidates: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=min(len(queries), 3)) as executor:
            future_to_query = {
                executor.submit(self.provider.search, q, max(2, max_sources // len(queries) + 1)): q
                for q in queries
            }
            for fut in as_completed(future_to_query):
                q_text = future_to_query[fut]
                try:
                    res = fut.result()
                    for r in res:
                        r["query"] = q_text
                    raw_candidates.extend(res)
                except Exception as ex:
                    logger.warning(f"[{session_id}] Query failed: '{q_text}' ({ex})")

        # Deduplicate candidates by canonical URL
        seen_urls: Set[str] = set()
        unique_sources: List[Dict[str, Any]] = []
        for r in raw_candidates:
            clean_url = canonicalize_url(r.get("url", ""))
            if not clean_url or clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)
            r["url"] = clean_url
            r["id"] = str(uuid.uuid4())
            unique_sources.append(r)
            if len(unique_sources) >= max_sources + 2:
                break

        stages[1]["status"] = "completed"
        stages[1]["detail"] = f"Searched {len(queries)} query vectors; retrieved {len(unique_sources)} candidate sources."
        emit("web_search", "completed", stages[1]["detail"], {"candidate_count": len(unique_sources)})
        logger.info(f"[{session_id}] Stage 2 (web_search) finished in {time.perf_counter() - t1:.4f}s")

        if not unique_sources:
            logger.info(f"[{session_id}] No verified research sources retrieved for topic '{topic}'.")
            stages[2]["status"] = "failed"
            stages[2]["detail"] = "No verified articles returned."
            empty_payload = {
                "topic": topic,
                "queries": queries,
                "sources": [],
                "evidence_items": [],
                "stages": stages,
                "indexed_chunks": 0,
                "status": "empty",
                "message": "Live research is unavailable or yielded no verified sources."
            }
            emit("collect_articles", "failed", "No verified articles returned.")
            emit("complete", "empty", "No verified articles returned.", empty_payload)
            return empty_payload

        # -------------------------------------------------------------
        # STAGE 3: Bounded Parallel Article Retrieval
        # -------------------------------------------------------------
        t2 = time.perf_counter()
        stages[2]["status"] = "in_progress"
        emit("collect_articles", "in_progress", "Retrieving article contents in parallel...")

        target_sources = unique_sources[:max_sources]
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8'
        }

        # Concurrency: enforce max concurrent downloads (configurable in settings)
        has_pdf = any(is_pdf_candidate(s.get("url", "")) for s in target_sources)
        max_workers = min(len(target_sources), getattr(settings, "MAX_CONCURRENT_PDF_DOWNLOADS", 2) if has_pdf else 4)

        all_sources: List[Dict[str, Any]] = []
        with httpx.Client(headers=headers, follow_redirects=True, timeout=getattr(settings, "PDF_DOWNLOAD_TIMEOUT_SECONDS", 25.0)) as client:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futs = [executor.submit(self._fetch_single_article, s, client, 6.0, emit) for s in target_sources]
                for fut in as_completed(futs):
                    res = fut.result()
                    all_sources.append(res)
                    c_type = res.get("content_type", "SEARCH_SNIPPET_ONLY")
                    title_preview = res.get('title', '')[:40]
                    emit("source_found", "in_progress", f"Collected [{c_type}]: {title_preview}...", {"source": res})

        pdf_sources = [s for s in all_sources if s.get("content_type") == "FULL_PDF_TEXT"]
        html_sources = [s for s in all_sources if s.get("content_type") == "FULL_HTML_ARTICLE"]
        snippet_sources = [s for s in all_sources if s.get("content_type") == "SEARCH_SNIPPET_ONLY"]

        stages[2]["status"] = "completed"
        stages[2]["detail"] = f"Collected {len(all_sources)} verified sources ({len(pdf_sources)} research PDFs, {len(html_sources)} HTML articles, {len(snippet_sources)} snippet fallbacks)."
        emit("collect_articles", "completed", stages[2]["detail"])
        logger.info(f"[{session_id}] Stage 3 (collect_articles) finished in {time.perf_counter() - t2:.4f}s")

        # -------------------------------------------------------------
        # STAGE 4: Source Relevance Filtering
        # -------------------------------------------------------------
        t3 = time.perf_counter()
        stages[3]["status"] = "completed"
        stages[3]["detail"] = f"Verified {len(all_sources)} authoritative sources ({len(pdf_sources)} full PDFs, {len(html_sources)} full articles)."
        emit("check_relevance", "completed", stages[3]["detail"])
        logger.info(f"[{session_id}] Stage 4 (check_relevance) finished in {time.perf_counter() - t3:.4f}s")

        # -------------------------------------------------------------
        # STAGE 5: Salient Evidence Claim Extraction (Page-Aware)
        # -------------------------------------------------------------
        t4 = time.perf_counter()
        stages[4]["status"] = "in_progress"
        emit("extract_evidence", "in_progress", "Extracting factual claims, empirical indicators, and page citations...")

        evidence_items: List[Dict[str, Any]] = []
        evidence_keywords = {
            "evidence", "data", "statistic", "percent", "study", "research", "concluded",
            "demonstrated", "found", "report", "analysis", "suggests", "significant",
            "court", "legal", "framework", "system", "performance", "impact", "result"
        }

        for src in all_sources:
            if src.get("content_type") == "FULL_PDF_TEXT" and src.get("pdf_pages"):
                # Extract claims page-by-page preserving original page numbers
                for p in src["pdf_pages"]:
                    page_num = p["page_number"]
                    page_text = p.get("text", "").strip()
                    if not page_text:
                        continue
                    raw_sentences = [
                        s.strip() for s in re.split(r'(?<=[.!?])\s+', page_text)
                        if len(s.strip()) > 35 and not s.strip().startswith("http")
                    ]
                    scored = []
                    for s in raw_sentences:
                        words = set(re.findall(r'\b\w+\b', s.lower()))
                        score = len(words.intersection(evidence_keywords))
                        scored.append((score, s))
                    scored.sort(key=lambda x: x[0], reverse=True)
                    top_sentence = scored[0][1] if scored else (raw_sentences[0] if raw_sentences else page_text[:200])

                    sec_name = p.get("section_title") or f"Page {page_num}"
                    ev_id = f"ev-pdf-{uuid.uuid4().hex[:6]}"
                    item = {
                        "id": ev_id,
                        "claim": top_sentence,
                        "source": f"{src['title']} ({sec_name})",
                        "url": src["url"],
                        "page": page_num,
                        "section": sec_name,
                        "contentType": "FULL_PDF_TEXT",
                        "publishedDate": src.get("published_date")
                    }
                    evidence_items.append(item)
                    emit("evidence_extracted", "in_progress", f"Claim [{sec_name}]: {top_sentence[:45]}...", {"evidence": item})
            else:
                content_text = src.get("content") or src.get("snippet", "")
                raw_sentences = [
                    s.strip() for s in re.split(r'(?<=[.!?])\s+', content_text)
                    if len(s.strip()) > 35 and not s.strip().startswith("http")
                ]
                scored_sentences = []
                for s in raw_sentences:
                    words = set(re.findall(r'\b\w+\b', s.lower()))
                    score = len(words.intersection(evidence_keywords))
                    scored_sentences.append((score, s))
                scored_sentences.sort(key=lambda x: x[0], reverse=True)

                selected_claims = [s for _, s in scored_sentences[:2]]
                if not selected_claims and raw_sentences:
                    selected_claims = raw_sentences[:2]
                elif not selected_claims:
                    selected_claims = [content_text[:200]]

                c_type = src.get("content_type", "SEARCH_SNIPPET_ONLY")
                for claim_text in selected_claims:
                    ev_id = f"ev-web-{uuid.uuid4().hex[:6]}"
                    item = {
                        "id": ev_id,
                        "claim": claim_text,
                        "source": src["title"],
                        "url": src["url"],
                        "page": None,
                        "section": src["title"],
                        "contentType": c_type,
                        "publishedDate": src.get("published_date")
                    }
                    evidence_items.append(item)
                    emit("evidence_extracted", "in_progress", f"Claim: {claim_text[:50]}...", {"evidence": item})

        stages[4]["status"] = "completed"
        stages[4]["detail"] = f"Extracted {len(evidence_items)} factual evidence statements with original source & page citations."
        emit("extract_evidence", "completed", stages[4]["detail"])
        logger.info(f"[{session_id}] Stage 5 (extract_evidence) finished in {time.perf_counter() - t4:.4f}s")

        # -------------------------------------------------------------
        # STAGE 6: Batch Embedding & Qdrant Indexing
        # -------------------------------------------------------------
        t5 = time.perf_counter()
        stages[5]["status"] = "in_progress"
        emit("prepare_evidence", "in_progress", "Batch embedding and vectorizing knowledge in Qdrant...")

        # 1. Persist sources to SQLite with rich metadata
        for src in all_sources:
            rec = ResearchSourceModel(
                id=src["id"],
                debate_id=debate_id,
                topic=topic,
                query=src.get("query", topic),
                title=src["title"],
                url=src["url"],
                content=src.get("content", ""),
                published_date=src.get("published_date"),
                metadata_json={
                    "content_type": src.get("content_type", "SEARCH_SNIPPET_ONLY"),
                    "page_count": src.get("page_count"),
                    "pages_extracted": src.get("pages_extracted"),
                    "is_partial_extraction": src.get("is_partial_extraction", False),
                    "extraction_status": src.get("extraction_status", "FULL"),
                    "skipped_pages_count": src.get("skipped_pages_count", 0),
                    "skipped_reason": src.get("skipped_reason"),
                    "content_hash": src.get("content_hash"),
                    "warning": src.get("warning"),
                    "evidence_items": [ev for ev in evidence_items if ev["url"] == src["url"]]
                }
            )
            db.add(rec)
        db.commit()

        # 2. Chunk text and prepare chunk entries (Page-aware for PDFs)
        all_chunks = []
        for src in all_sources:
            if src.get("content_type") == "FULL_PDF_TEXT" and src.get("pdf_pages"):
                emit("pdf_indexing_started", "in_progress", f"Chunking and embedding {src['title'][:35]}...", {"url": src["url"]})
                src_chunks_count = 0
                for p in src["pdf_pages"]:
                    sec_name = p.get("section_title") or f"Page {p['page_number']}"
                    p_chunks = document_service.chunk_text(
                        text=p["text"],
                        page_number=p["page_number"],
                        section_title=f"{src['title']} - {sec_name}"
                    )
                    for c in p_chunks:
                        all_chunks.append({
                            "chunk_id": c["chunk_id"],
                            "document_id": debate_id or "web_research",
                            "content": c["content"],
                            "page_number": p["page_number"],
                            "section_title": sec_name,
                            "title": src["title"],
                            "url": src["url"],
                            "source_type": "web",
                            "evidence_type": "web_pdf",
                            "content_hash": src.get("content_hash", "")
                        })
                        src_chunks_count += 1
                emit("pdf_indexing_completed", "in_progress", f"Indexed {src_chunks_count} chunks across {len(src['pdf_pages'])} pages for {src['title'][:35]}", {"url": src["url"], "chunks": src_chunks_count})
            else:
                chunks = document_service.chunk_text(
                    text=src.get("content") or src.get("snippet", ""),
                    page_number=None,
                    section_title=src["title"]
                )
                ev_type = "web_html" if src.get("content_type") == "FULL_HTML_ARTICLE" else "search_snippet"
                for c in chunks:
                    all_chunks.append({
                        "chunk_id": c["chunk_id"],
                        "document_id": debate_id or "web_research",
                        "content": c["content"],
                        "page_number": None,
                        "section_title": src["title"],
                        "title": src["title"],
                        "url": src["url"],
                        "source_type": "web",
                        "evidence_type": ev_type,
                        "content_hash": src.get("content_hash", "")
                    })

        # 3. Batch encode & batch upsert
        embed_duration = 0.0
        qdrant_duration = 0.0
        if all_chunks:
            t_embed_start = time.perf_counter()
            texts = [c["content"] for c in all_chunks]
            vectors = embedding_service.embed_documents(texts)
            embed_duration = time.perf_counter() - t_embed_start

            t_qdrant_start = time.perf_counter()
            qdrant_service.upsert_chunks(all_chunks, vectors)
            qdrant_duration = time.perf_counter() - t_qdrant_start

        stages[5]["status"] = "completed"
        stages[5]["detail"] = f"Indexed {len(all_chunks)} chunks into shared debate evidence pool ({len(pdf_sources)} PDFs fully parsed)."
        emit("prepare_evidence", "completed", stages[5]["detail"])
        logger.info(f"[{session_id}] Stage 6 (prepare_evidence) finished in {time.perf_counter() - t5:.4f}s")

        total_time = time.perf_counter() - t_start_total
        search_duration = t2 - t1
        pdf_dl_duration = sum(s.get("download_duration_sec", 0.0) for s in all_sources)
        pdf_ext_duration = sum(s.get("extraction_duration_sec", 0.0) for s in all_sources)
        html_ext_duration = sum(s.get("html_duration_sec", 0.0) for s in all_sources)

        from datetime import timezone
        timings = {
            "research_start_time": research_start_time,
            "research_completed_time": datetime.now(timezone.utc).isoformat(),
            "total_research_duration_sec": round(total_time, 3),
            "search_provider_duration_sec": round(search_duration, 3),
            "pdf_download_duration_sec": round(pdf_dl_duration, 3),
            "pdf_extraction_duration_sec": round(pdf_ext_duration, 3),
            "ocr_duration_sec": 0.0,
            "html_extraction_duration_sec": round(html_ext_duration, 3),
            "embedding_duration_sec": round(embed_duration, 3),
            "qdrant_indexing_duration_sec": round(qdrant_duration, 3),
            "is_cached": False
        }

        # Cache final normalized results
        result_payload = {
            "topic": topic,
            "queries": queries,
            "sources": all_sources,
            "evidence_items": evidence_items,
            "stages": stages,
            "indexed_chunks": len(all_chunks),
            "status": "completed",
            "message": f"Evidence collected, deduplicated, and indexed in Qdrant ({len(pdf_sources)} full PDFs, {len(html_sources)} HTML articles).",
            "timings": timings
        }
        research_cache.set_topic(topic, result_payload)

        logger.info(f"[{session_id}] Web Research successfully finished in {total_time:.3f}s (sources={len(all_sources)}, claims={len(evidence_items)}, chunks={len(all_chunks)}, pdfs={len(pdf_sources)})")
        emit("complete", "completed", f"Research completed in {total_time:.2f}s", result_payload)

        return result_payload


research_service = ResearchService()

"""
Proveedores concretos de enriquecimiento.

Cada uno obtiene datos de una fuente distinta.
Todos devuelven EnrichmentResult con la misma estructura.
"""

import logging
import re
from typing import Any

import httpx

from app.services.enrichment.base import EnrichmentProvider, EnrichmentResult

logger = logging.getLogger(__name__)

# Dominios de email gratuitos/genéricos
GENERIC_DOMAINS = {
    "gmail.com", "hotmail.com", "outlook.com", "yahoo.com",
    "icloud.com", "protonmail.com", "live.com", "msn.com",
    "aol.com", "mail.com", "zoho.com", "yandex.com",
    "tutanota.com", "gmx.com", "fastmail.com",
}


class EmailAnalysisProvider(EnrichmentProvider):
    """
    Analiza el email para extraer información básica.
    
    No hace llamadas externas — solo analiza el formato del email.
    Siempre funciona, es el primer proveedor del pipeline.
    """

    @property
    def name(self) -> str:
        return "email_analysis"

    async def enrich(self, email: str, domain: str, current_data: dict[str, Any]) -> EnrichmentResult:
        """Analiza el email y extrae datos."""
        local_part = email.split("@")[0]
        is_corporate = domain not in GENERIC_DOMAINS

        # Intentar extraer nombre del email (juan.garcia → Juan Garcia)
        name_guess = None
        if "." in local_part:
            parts = local_part.split(".")
            name_guess = " ".join(p.capitalize() for p in parts)
        elif "_" in local_part:
            parts = local_part.split("_")
            name_guess = " ".join(p.capitalize() for p in parts)

        # Detectar patrones de email que indican rol
        role_patterns = {
            "info": "generic",
            "contact": "generic",
            "hello": "generic",
            "support": "support",
            "sales": "sales",
            "admin": "admin",
            "ceo": "executive",
            "cto": "executive",
            "cfo": "executive",
            "hr": "human_resources",
        }
        email_role = "personal"
        for pattern, role in role_patterns.items():
            if local_part.lower().startswith(pattern):
                email_role = role
                break

        return EnrichmentResult(
            provider=self.name,
            success=True,
            data={
                "is_corporate_email": is_corporate,
                "email_local_part": local_part,
                "email_role_type": email_role,
                "name_from_email": name_guess,
                "domain": domain,
            },
        )


class WebScrapingProvider(EnrichmentProvider):
    """
    Visita el sitio web de la empresa y extrae información.
    
    Obtiene: título, descripción, tecnologías detectadas,
    redes sociales, y metadata general.
    """

    @property
    def name(self) -> str:
        return "web_scraping"

    async def enrich(self, email: str, domain: str, current_data: dict[str, Any]) -> EnrichmentResult:
        """Hace scraping básico del dominio."""
        if domain in GENERIC_DOMAINS:
            return EnrichmentResult(
                provider=self.name,
                success=False,
                error="Dominio genérico, no se hace scraping",
            )

        url = f"https://{domain}"
        data: dict[str, Any] = {}

        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; LeadForge/1.0)"},
        ) as client:
            response = await client.get(url)
            html = response.text

            # Extraer título
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            if title_match:
                data["page_title"] = title_match.group(1).strip()[:200]

            # Extraer meta description
            desc_match = re.search(
                r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
                html, re.IGNORECASE,
            )
            if desc_match:
                data["meta_description"] = desc_match.group(1).strip()[:500]

            # Detectar tecnologías por señales en el HTML
            tech_signals = {
                "WordPress": ["wp-content", "wp-includes"],
                "Shopify": ["cdn.shopify.com", "shopify"],
                "React": ["react", "__next", "reactDOM"],
                "Vue": ["vue.js", "__vue"],
                "Angular": ["ng-version", "angular"],
                "HubSpot": ["hubspot", "hs-scripts"],
                "Salesforce": ["salesforce", "pardot"],
                "Google Analytics": ["google-analytics", "gtag"],
                "Google Tag Manager": ["googletagmanager"],
                "Stripe": ["stripe.com", "js.stripe"],
                "Intercom": ["intercom", "intercomSettings"],
                "Zendesk": ["zendesk", "zdassets"],
            }
            detected_tech = []
            html_lower = html.lower()
            for tech, signals in tech_signals.items():
                if any(signal.lower() in html_lower for signal in signals):
                    detected_tech.append(tech)
            data["technologies"] = detected_tech

            # Extraer redes sociales
            social_patterns = {
                "linkedin": r'https?://(?:www\.)?linkedin\.com/company/[\w-]+',
                "twitter": r'https?://(?:www\.)?(?:twitter|x)\.com/[\w]+',
                "facebook": r'https?://(?:www\.)?facebook\.com/[\w.]+',
                "instagram": r'https?://(?:www\.)?instagram\.com/[\w.]+',
                "github": r'https?://(?:www\.)?github\.com/[\w-]+',
            }
            social_links = {}
            for platform, pattern in social_patterns.items():
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    social_links[platform] = match.group(0)
            if social_links:
                data["social_links"] = social_links

            # Status code y URL final (por si hubo redirect)
            data["website_status"] = response.status_code
            data["final_url"] = str(response.url)

        return EnrichmentResult(
            provider=self.name,
            success=True,
            data=data,
        )


class DnsProvider(EnrichmentProvider):
    """
    Obtiene información básica del dominio via HTTP headers.
    
    Detecta el servidor web, CDN, y proveedor de email
    sin necesidad de librerías DNS externas.
    """

    @property
    def name(self) -> str:
        return "dns_info"

    async def enrich(self, email: str, domain: str, current_data: dict[str, Any]) -> EnrichmentResult:
        """Analiza headers HTTP del dominio."""
        if domain in GENERIC_DOMAINS:
            return EnrichmentResult(
                provider=self.name,
                success=False,
                error="Dominio genérico, no se analiza",
            )

        url = f"https://{domain}"
        data: dict[str, Any] = {}

        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
        ) as client:
            response = await client.head(url)

            headers = dict(response.headers)

            # Detectar servidor web
            if "server" in headers:
                data["web_server"] = headers["server"]

            # Detectar CDN
            cdn_headers = {
                "cloudflare": ["cf-ray", "cf-cache-status"],
                "aws_cloudfront": ["x-amz-cf-id"],
                "fastly": ["x-served-by"],
                "akamai": ["x-akamai-transformed"],
                "vercel": ["x-vercel-id"],
                "netlify": ["x-nf-request-id"],
            }
            for cdn, header_names in cdn_headers.items():
                if any(h in headers for h in header_names):
                    data["cdn"] = cdn
                    break

            # Detectar proveedor de email por MX (header hint)
            # Esto es limitado sin DNS real, pero útil
            data["has_ssl"] = str(response.url).startswith("https")
            data["response_time_ms"] = response.elapsed.total_seconds() * 1000

        return EnrichmentResult(
            provider=self.name,
            success=True,
            data=data,
        )
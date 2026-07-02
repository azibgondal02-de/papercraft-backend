from fastapi import APIRouter, Request
from fastapi.responses import Response
from lib_blog.blog import get_sitemap_urls
from web import get_context

router = APIRouter(tags=["Sitemap"])

@router.get("/sitemap.xml", include_in_schema=False)
def generate_sitemap(request: Request):
    context = get_context(request)
    urls = get_sitemap_urls(conn=context.conn)

    base = "https://papercraft.pk"

    # Static pages
    static_urls = [
        {"loc": base, "priority": "1.0", "changefreq": "weekly"},
        {"loc": f"{base}/blog", "priority": "0.8", "changefreq": "daily"},
    ]

    # Blog post URLs
    post_urls = [
        {
            "loc": f"{base}/blog/{u.slug}",
            "lastmod": u.published_at.strftime("%Y-%m-%d") if u.published_at else "2026-06-26",
            "priority": "0.7",
            "changefreq": "monthly",
        }
        for u in urls
    ]

    all_urls = static_urls + post_urls

    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_parts.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    for url in all_urls:
        xml_parts.append("  <url>")
        xml_parts.append(f"    <loc>{url['loc']}</loc>")
        if "lastmod" in url:
            xml_parts.append(f"    <lastmod>{url['lastmod']}</lastmod>")
        xml_parts.append(f"    <changefreq>{url['changefreq']}</changefreq>")
        xml_parts.append(f"    <priority>{url['priority']}</priority>")
        xml_parts.append("  </url>")

    xml_parts.append("</urlset>")
    xml_content = "\n".join(xml_parts)

    return Response(content=xml_content, media_type="application/xml")
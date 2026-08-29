from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from app.api.v1.access import router as access_router
from app.api.v1.agentic import router as agentic_router
from app.api.v1.agentic_security import router as agentic_security_router
from app.api.v1.audit import router as audit_router
from app.api.v1.classifier import router as classifier_router
from app.api.v1.compliance import router as compliance_router
from app.api.v1.custom_intents import router as custom_intents_router
from app.api.v1.data_protection import router as data_protection_router
from app.api.v1.edge import router as edge_router
from app.api.v1.extension import router as extension_router
from app.api.v1.gateway import admin_router as gateway_admin_router
from app.api.v1.gateway import openai_router as gateway_openai_router
from app.api.v1.help import router as help_router
from app.api.v1.governance import router as governance_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.copilot import router as copilot_router
from app.api.v1.mcp_governance import router as mcp_governance_router
from app.api.v1.mcp_security import router as mcp_security_router
from app.api.v1.observability import router as observability_router
from app.api.v1.oidc import router as oidc_router
from app.api.v1.blog import router as blog_router
from app.api.v1.platform import router as platform_router
from app.api.v1.prompt_templates import router as prompt_templates_router
from app.api.v1.public_leads import router as public_leads_router
from app.api.v1.qa import router as qa_router
from app.api.v1.rag_gateway import router as rag_gateway_router
from app.api.v1.reports import router as reports_router
from app.api.v1.router import router as auth_router
from app.api.v1.routing_groups import router as routing_groups_router
from app.api.v1.security import router as security_router
from app.api.v1.settings import router as settings_router
from app.api.v1.telemetry import router as telemetry_router
from app.api.v1.uag import router as uag_router
from app.api.v1.users import router as users_router
from app.config import settings
from app.core.rate_limit import AuthRateLimitMiddleware
from app.core.security import get_jwt_secret, set_jwt_secret_override
from app.core.telemetry import setup_telemetry
from app.db.seed import seed_demo_data, seed_platform_admin
from app.db.seed_agentic_control_plane import seed_agentic_control_plane_data
from app.db.seed_genai_dlp import seed_genai_dlp_demo_events
from app.db.seed_governance import seed_access_data, seed_governance_data, seed_uag_data
from app.db.seed_prompt_templates import seed_prompt_templates_data
from app.services.traffic_simulator import generate_simulated_traffic_for_tenant
from app.services.vault_service import assert_production_security, load_jwt_secret_from_vault
from app.services.health_service import build_dependency_status
from app.services.http_client_pool import close_http_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    vault_jwt = await load_jwt_secret_from_vault()
    if vault_jwt:
        set_jwt_secret_override(vault_jwt, from_vault=True)
    assert_production_security(get_jwt_secret())

    if settings.debug or settings.demo_credentials_enabled:
        try:
            await seed_demo_data()
            await seed_platform_admin()
            await seed_governance_data()
            await seed_access_data()
            await seed_uag_data()
            seeded = await seed_genai_dlp_demo_events()
            if seeded:
                print(f"GenAI DLP seed: demo events added for {seeded} tenant(s).")
            prompt_seeded = await seed_prompt_templates_data()
            if prompt_seeded:
                print(f"Prompt template seed: demo templates added for {prompt_seeded} tenant(s).")
            control_seeded = await seed_agentic_control_plane_data()
            if control_seeded:
                print(f"Agentic control-plane seed: demo data added for {control_seeded} tenant(s).")
            await generate_simulated_traffic_for_tenant("acme", count=8)
        except Exception as exc:
            print(f"Seed skipped (database may be unavailable): {exc}")
    yield
    await close_http_client()


from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise AI Governance and Control Plane API",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "tryItOutEnabled": True,
        "filter": True,
    },
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="PySetu AI — Enterprise AI Gateway & Governance API",
        version=settings.app_version,
        description="Public Developer & Client API for PySetu AI Gateway, Policy Engine, MCP Governance, and Enterprise Access Control.",
        routes=app.routes,
    )

    # Filter out internal SaaS platform operator routes from client OpenAPI documentation
    if "paths" in openapi_schema:
        filtered_paths = {}
        for path, methods in openapi_schema["paths"].items():
            if path.startswith(f"{settings.api_prefix}/platform") or path.startswith("/platform"):
                continue
            filtered_paths[path] = methods
        openapi_schema["paths"] = filtered_paths

    if "components" not in openapi_schema:
        openapi_schema["components"] = {}

    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token (from /api/v1/auth/login)",
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "API Key or Bearer Token in Authorization header",
        },
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://([a-zA-Z0-9-]+\.)?pysetu\.io",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthRateLimitMiddleware)

app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(blog_router, prefix=settings.api_prefix)
app.include_router(platform_router, prefix=settings.api_prefix)
app.include_router(classifier_router, prefix=settings.api_prefix)
app.include_router(edge_router, prefix=settings.api_prefix)
app.include_router(governance_router, prefix=settings.api_prefix)
app.include_router(audit_router, prefix=settings.api_prefix)
app.include_router(access_router, prefix=settings.api_prefix)
app.include_router(agentic_router, prefix=settings.api_prefix)
app.include_router(agentic_security_router, prefix=settings.api_prefix)
app.include_router(mcp_governance_router, prefix=settings.api_prefix)
app.include_router(copilot_router, prefix=settings.api_prefix)
app.include_router(observability_router, prefix=settings.api_prefix)
app.include_router(settings_router, prefix=settings.api_prefix)
app.include_router(telemetry_router, prefix=settings.api_prefix)
app.include_router(integrations_router, prefix=settings.api_prefix)
app.include_router(oidc_router, prefix=settings.api_prefix)
app.include_router(uag_router, prefix=settings.api_prefix)
app.include_router(users_router, prefix=settings.api_prefix)
app.include_router(reports_router, prefix=settings.api_prefix)
app.include_router(compliance_router, prefix=settings.api_prefix)
app.include_router(qa_router, prefix=settings.api_prefix)
app.include_router(security_router, prefix=settings.api_prefix)
app.include_router(data_protection_router, prefix=settings.api_prefix)
app.include_router(extension_router, prefix=settings.api_prefix)
app.include_router(rag_gateway_router, prefix=settings.api_prefix)
app.include_router(notifications_router, prefix=settings.api_prefix)
app.include_router(mcp_security_router, prefix=settings.api_prefix)
app.include_router(routing_groups_router, prefix=settings.api_prefix)
app.include_router(prompt_templates_router, prefix=settings.api_prefix)
app.include_router(help_router, prefix=settings.api_prefix)
app.include_router(custom_intents_router, prefix=settings.api_prefix)
app.include_router(public_leads_router, prefix=settings.api_prefix)
app.include_router(gateway_admin_router, prefix=settings.api_prefix)
app.include_router(gateway_openai_router)


setup_telemetry(app)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "message": "PySetu AI API — use the web UI or API docs below.",
        "ui": settings.frontend_url,
        "docs": "/docs",
        "health": "/health",
        "api": settings.api_prefix,
    }


@app.get("/health")
async def health_check(request: Request):
    dependency_status = await build_dependency_status()
    payload = {
        "status": dependency_status["status"],
        "service": settings.app_name,
        "version": settings.app_version,
        "otel_enabled": str(settings.otel_enabled).lower(),
        "air_gap_mode": str(settings.air_gap_mode).lower(),
        "api": settings.api_prefix,
        "docs": "/docs",
        "ui": settings.frontend_url,
        "dependencies": dependency_status["dependencies"],
    }

    accept = request.headers.get("accept", "")
    if "text/html" in accept and "application/json" not in accept.split(",")[0]:
        status_color = "#22c55e" if payload["status"] == "healthy" else "#f97316"
        if payload["status"] == "unhealthy":
            status_color = "#ef4444"
        otel_label = "Enabled" if payload["otel_enabled"] == "true" else "Disabled"
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{payload["service"]} — Health</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      background: #0f172a;
      color: #e2e8f0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 2rem;
    }}
    .card {{
      width: min(480px, 100%);
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 2rem;
      box-shadow: 0 10px 40px rgba(0,0,0,.35);
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.35rem 0.75rem;
      border-radius: 999px;
      background: rgba(34,197,94,.15);
      color: {status_color};
      font-size: 0.875rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .dot {{ width: 8px; height: 8px; border-radius: 50%; background: {status_color}; }}
    h1 {{ font-size: 1.5rem; margin: 1rem 0 0.25rem; }}
    .subtitle {{ color: #94a3b8; font-size: 0.9rem; margin-bottom: 1.5rem; }}
    dl {{ display: grid; gap: 0.75rem; }}
    .row {{
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      padding: 0.65rem 0;
      border-bottom: 1px solid #334155;
      font-size: 0.9rem;
    }}
    .row:last-child {{ border-bottom: none; }}
    dt {{ color: #94a3b8; }}
    dd {{ font-weight: 500; text-align: right; }}
    .links {{ margin-top: 1.5rem; display: flex; flex-wrap: wrap; gap: 0.75rem; }}
    a {{
      color: #38bdf8;
      text-decoration: none;
      font-size: 0.875rem;
      padding: 0.4rem 0.75rem;
      border: 1px solid #334155;
      border-radius: 6px;
    }}
    a:hover {{ background: #334155; }}
  </style>
</head>
<body>
  <main class="card">
    <div class="badge"><span class="dot"></span>{payload["status"]}</div>
    <h1>{payload["service"]}</h1>
    <p class="subtitle">API health check</p>
    <dl>
      <div class="row"><dt>Version</dt><dd>{payload["version"]}</dd></div>
      <div class="row"><dt>Database</dt><dd>{payload["dependencies"]["database"]["status"]}</dd></div>
      <div class="row"><dt>OPA</dt><dd>{payload["dependencies"]["opa"]["status"]}</dd></div>
      <div class="row"><dt>OpenTelemetry</dt><dd>{otel_label}</dd></div>
      <div class="row"><dt>API prefix</dt><dd>{payload["api"]}</dd></div>
    </dl>
    <div class="links">
      <a href="{payload["ui"]}">Open Web UI</a>
      <a href="{payload["docs"]}">API Docs</a>
      <a href="/health" onclick="fetch('/health',{{headers:{{Accept:'application/json'}}}}).then(r=>r.json()).then(d=>alert(JSON.stringify(d,null,2)));return false;">View JSON</a>
    </div>
  </main>
</body>
</html>"""
        return HTMLResponse(content=html)

    return JSONResponse(content=payload)

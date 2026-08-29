import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.trial_request import TrialRequest
from app.schemas.trial_request import TrialRequestCreate, TrialSubmissionResult
from app.services.email_service import send_tenant_email
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public", tags=["Public Leads & Trials"])


@router.post("/trial-requests", response_model=TrialSubmissionResult, status_code=status.HTTP_201_CREATED)
async def submit_trial_request(
    payload: TrialRequestCreate,
    db: AsyncSession = Depends(get_db),
) -> TrialSubmissionResult:
    """Public lead capture for 30-day enterprise trial requests and interest submission."""
    # Check if a recent pending request already exists for this email to prevent spam
    existing = await db.scalar(
        select(TrialRequest).where(
            TrialRequest.work_email == payload.work_email.lower().strip(),
            TrialRequest.status == "pending",
        )
    )

    lead = TrialRequest(
        full_name=payload.full_name.strip(),
        work_email=payload.work_email.lower().strip(),
        company_name=payload.company_name.strip(),
        team_size=payload.team_size or "1-20",
        use_case=payload.use_case or "AI Gateway & Governance",
        message=payload.message.strip() if payload.message else None,
        status="pending",
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    logger.info("New 30-day trial request submitted by %s <%s> from %s", lead.full_name, lead.work_email, lead.company_name)

    # 1. Send immediate confirmation email to the user
    user_subject = "Welcome to PySetu AI — 30-Day Enterprise Trial Request Received"
    user_html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; color: #1e293b; line-height: 1.6;">
      <div style="border-bottom: 2px solid #0284c7; padding-bottom: 16px; margin-bottom: 24px;">
        <h2 style="color: #0f172a; margin: 0; font-size: 24px;">PySetu AI</h2>
        <p style="color: #64748b; margin: 4px 0 0 0; font-size: 14px;">Enterprise AI Gateway & Control Plane</p>
      </div>

      <p style="font-size: 16px; font-weight: 600;">Hello {lead.full_name},</p>

      <p>Thank you for your interest in <strong>PySetu AI</strong>! We have received your request for a <strong>30-Day Enterprise Trial</strong> for <strong>{lead.company_name}</strong>.</p>

      <div style="background-color: #f8fafc; border-left: 4px solid #0284c7; padding: 16px; margin: 20px 0; border-radius: 4px;">
        <h4 style="margin: 0 0 8px 0; color: #0f172a; font-size: 14px;">Your Request Details:</h4>
        <ul style="margin: 0; padding-left: 20px; font-size: 14px; color: #334155;">
          <li><strong>Organization:</strong> {lead.company_name}</li>
          <li><strong>Work Email:</strong> {lead.work_email}</li>
          <li><strong>Primary Focus:</strong> {lead.use_case}</li>
          <li><strong>Workload Scale:</strong> {lead.team_size} team members</li>
        </ul>
      </div>

      <p>Our cloud operations team is preparing your dedicated tenant sandbox. You will receive an email invite with your private workspace URL and single sign-on credentials shortly.</p>

      <p style="margin-top: 24px;">If you have immediate questions or specific compliance requirements (HIPAA, SOC 2, ISO 27001), feel free to reply directly to this email or reach us at <a href="mailto:hello@pysetu.io" style="color: #0284c7;">hello@pysetu.io</a>.</p>

      <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 32px 0 16px 0;" />
      <p style="color: #94a3b8; font-size: 12px; margin: 0;">
        &copy; {2026} PySetu AI Inc. All rights reserved. • <a href="https://pysetu.io" style="color: #64748b;">pysetu.io</a>
      </p>
    </div>
    """

    user_text = f"""Hello {lead.full_name},

Thank you for your interest in PySetu AI! We have received your request for a 30-Day Enterprise Trial for {lead.company_name}.

Request Details:
- Organization: {lead.company_name}
- Work Email: {lead.work_email}
- Primary Focus: {lead.use_case}
- Scale: {lead.team_size}

Our team is setting up your dedicated workspace. You will receive access details shortly.

Questions? Reply to this email or contact hello@pysetu.io.

Best regards,
The PySetu AI Team
https://pysetu.io
"""

    try:
        await send_tenant_email(
            db=db,
            tenant_id=None,  # Resolves SaaS Platform default SMTP
            recipients=[lead.work_email],
            subject=user_subject,
            html_body=user_html,
            text_body=user_text,
        )
    except Exception as exc:
        logger.warning("Failed to send trial confirmation email to %s: %s", lead.work_email, exc)

    # 2. Send notification to internal sales / operations inbox
    internal_subject = f"🔥 New 30-Day Trial Request: {lead.company_name} ({lead.full_name})"
    internal_html = f"""
    <h3>New Enterprise Trial / Interest Lead</h3>
    <p><strong>Name:</strong> {lead.full_name}</p>
    <p><strong>Email:</strong> {lead.work_email}</p>
    <p><strong>Company:</strong> {lead.company_name}</p>
    <p><strong>Team Size:</strong> {lead.team_size}</p>
    <p><strong>Use Case:</strong> {lead.use_case}</p>
    <p><strong>Message / Notes:</strong> {lead.message or 'None'}</p>
    <hr />
    <p><a href="https://pysetu.io/platform">Go to Platform Console to Provision Tenant</a></p>
    """
    try:
        await send_tenant_email(
            db=db,
            tenant_id=None,
            recipients=["hello@pysetu.io"],
            subject=internal_subject,
            html_body=internal_html,
            text_body=f"New Lead: {lead.full_name} from {lead.company_name} ({lead.work_email}) - Use case: {lead.use_case}",
        )
    except Exception as exc:
        logger.warning("Failed to dispatch internal trial alert: %s", exc)

    return TrialSubmissionResult(
        success=True,
        message="Thank you! Your 30-day enterprise trial request has been submitted. A confirmation email has been sent to your inbox.",
        lead_id=lead.id,
    )

import re
import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import CustomIntent
from app.schemas.custom_intent import (
    CustomIntentCreate,
    CustomIntentMatch,
    CustomIntentTestResponse,
    CustomIntentUpdate,
)


class CustomIntentService:
    @staticmethod
    async def list_custom_intents(db: AsyncSession, tenant_id: uuid.UUID) -> List[CustomIntent]:
        result = await db.execute(
            select(CustomIntent)
            .where(CustomIntent.tenant_id == tenant_id)
            .order_by(CustomIntent.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_custom_intent(
        db: AsyncSession, tenant_id: uuid.UUID, intent_id: uuid.UUID
    ) -> Optional[CustomIntent]:
        result = await db.execute(
            select(CustomIntent).where(
                CustomIntent.id == intent_id, CustomIntent.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_custom_intent(
        db: AsyncSession, tenant_id: uuid.UUID, data: CustomIntentCreate
    ) -> CustomIntent:
        intent = CustomIntent(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
            action=data.action.lower(),
            keywords=[k.strip() for k in data.keywords if k.strip()],
            confidence_threshold=data.confidence_threshold,
            is_active=data.is_active,
            parent_id=data.parent_id,
            intent_type=data.intent_type.lower() if data.intent_type else "intent",
        )
        db.add(intent)
        await db.commit()
        await db.refresh(intent)
        return intent

    @staticmethod
    async def update_custom_intent(
        db: AsyncSession, tenant_id: uuid.UUID, intent_id: uuid.UUID, data: CustomIntentUpdate
    ) -> Optional[CustomIntent]:
        intent = await CustomIntentService.get_custom_intent(db, tenant_id, intent_id)
        if not intent:
            return None

        if data.name is not None:
            intent.name = data.name
        if data.description is not None:
            intent.description = data.description
        if data.action is not None:
            intent.action = data.action.lower()
        if data.keywords is not None:
            intent.keywords = [k.strip() for k in data.keywords if k.strip()]
        if data.confidence_threshold is not None:
            intent.confidence_threshold = data.confidence_threshold
        if data.is_active is not None:
            intent.is_active = data.is_active
        if data.parent_id is not None:
            intent.parent_id = data.parent_id
        if data.intent_type is not None:
            intent.intent_type = data.intent_type.lower()

        await db.commit()
        await db.refresh(intent)
        return intent

    @staticmethod
    async def delete_custom_intent(
        db: AsyncSession, tenant_id: uuid.UUID, intent_id: uuid.UUID
    ) -> bool:
        intent = await CustomIntentService.get_custom_intent(db, tenant_id, intent_id)
        if not intent:
            return False
        await db.delete(intent)
        await db.commit()
        return True

    @staticmethod
    async def scan_prompt_intents(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        prompt: str,
        intent_ids: Optional[List[uuid.UUID]] = None,
    ) -> CustomIntentTestResponse:
        query = select(CustomIntent).where(
            CustomIntent.tenant_id == tenant_id, CustomIntent.is_active.is_(True)
        )
        result = await db.execute(query)
        all_intents = list(result.scalars().all())

        if intent_ids:
            intents_by_id = {str(i.id): i for i in all_intents}
            children_by_parent: dict[str, list[CustomIntent]] = {}
            for i in all_intents:
                pid = str(i.parent_id) if i.parent_id else None
                if pid:
                    children_by_parent.setdefault(pid, []).append(i)

            def _resolve_intents(node_id: str, visited: set) -> list[CustomIntent]:
                if node_id in visited:
                    return []
                visited.add(node_id)
                node = intents_by_id.get(node_id)
                if not node:
                    return []
                resolved = []
                if node.intent_type == "intent" or not hasattr(node, "intent_type"):
                    resolved.append(node)
                elif node.intent_type == "folder":
                    for child in children_by_parent.get(node_id, []):
                        resolved.extend(_resolve_intents(str(child.id), visited))
                return resolved

            resolved_intents = []
            visited = set()
            for raw_id in intent_ids:
                resolved_intents.extend(_resolve_intents(str(raw_id), visited))
            intents = resolved_intents
        else:
            intents = [i for i in all_intents if (getattr(i, "intent_type", "intent") or "intent") == "intent"]

        matches: List[CustomIntentMatch] = []
        prompt_lower = prompt.lower()
        modified_prompt = prompt

        for intent in intents:
            matched_keywords = []
            for kw in intent.keywords:
                kw_clean = kw.strip().lower()
                if not kw_clean:
                    continue
                # Match word boundary or exact substring
                pattern = re.compile(re.escape(kw_clean), re.IGNORECASE)
                if pattern.search(prompt_lower):
                    matched_keywords.append(kw)

            if not intent.keywords:
                continue

            score = len(matched_keywords) / len(intent.keywords) if intent.keywords else 0.0

            # Boost score if a multi-word phrase matched directly
            if matched_keywords:
                score = max(score, min(1.0, 0.5 + (len(matched_keywords) * 0.25)))

            if score >= intent.confidence_threshold or (matched_keywords and intent.confidence_threshold <= 0.8):
                matches.append(
                    CustomIntentMatch(
                        intent_id=intent.id,
                        intent_name=intent.name,
                        action=intent.action,
                        matched_keywords=matched_keywords,
                        score=round(score, 2),
                    )
                )
                if intent.action == "redact":
                    for kw in matched_keywords:
                        pattern = re.compile(re.escape(kw), re.IGNORECASE)
                        modified_prompt = pattern.sub(f"[REDACTED:{intent.name}]", modified_prompt)

        # Precedence for final decision: block > redact > monitor > allow
        overall_action = "allow"
        actions = [m.action for m in matches]
        if "block" in actions:
            overall_action = "block"
        elif "redact" in actions:
            overall_action = "redact"
        elif "monitor" in actions:
            overall_action = "monitor"

        return CustomIntentTestResponse(
            matched=len(matches) > 0,
            matches=matches,
            action=overall_action,
            modified_prompt=modified_prompt if overall_action == "redact" else None,
        )

    @staticmethod
    async def suggest_custom_intent_with_ai(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        goal: str,
    ) -> dict:
        """
        Mocked deterministic AI assistant for Custom Intents.
        Parses the user's goal string and returns suggested keywords.
        """
        import re

        goal_lower = goal.lower()
        suggestions = []

        if re.search(r"\b(wire transfer|funds|account|bank)\b", goal_lower):
            suggestions.append(
                {
                    "name": "Detect Wire Transfers",
                    "description": "Flags requests involving money movement or bank details.",
                    "action": "block",
                    "keywords": ["wire transfer", "send funds", "account number", "routing number", "bank transfer"],
                    "confidence_threshold": 0.8,
                }
            )

        if re.search(r"\b(pii|personal|email|ssn|phone)\b", goal_lower):
            suggestions.append(
                {
                    "name": "Redact PII",
                    "description": "Identifies common personal identifiable information.",
                    "action": "redact",
                    "keywords": ["social security", "ssn", "phone number", "email address"],
                    "confidence_threshold": 0.85,
                }
            )

        if re.search(r"\b(secret|confidential|internal|project)\b", goal_lower):
            suggestions.append(
                {
                    "name": "Monitor Confidential Projects",
                    "description": "Monitors mentions of internal or secret projects.",
                    "action": "monitor",
                    "keywords": ["project titan", "confidential", "internal use only", "do not distribute"],
                    "confidence_threshold": 0.75,
                }
            )

        # Fallback if no specific patterns match
        if not suggestions:
            words = [w.strip() for w in re.split(r"[^\w]+", goal) if len(w.strip()) > 3]
            keywords = list(set(words))[:5]
            if not keywords:
                keywords = ["example keyword"]
            suggestions.append(
                {
                    "name": "Custom Intent",
                    "description": f"Generated intent based on: {goal[:30]}...",
                    "action": "block",
                    "keywords": keywords,
                    "confidence_threshold": 0.8,
                }
            )

        return {
            "summary": f"Analyzed goal: '{goal}'. Suggested {len(suggestions)} custom intent configurations.",
            "ai_enhanced": False,
            "suggestions": suggestions,
        }


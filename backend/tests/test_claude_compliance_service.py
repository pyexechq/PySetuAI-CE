from app.schemas.claude_compliance import ClaudeComplianceRecord
from app.services.claude_compliance_service import classify_sync_records


def test_classify_claude_records_aggregates_dlp_findings() -> None:
    result = classify_sync_records(
        [
            ClaudeComplianceRecord(
                organization_id="org-1",
                user_id="user-1",
                chat_id="chat-1",
                content="Patient diagnosis: asthma.",
            ),
            ClaudeComplianceRecord(
                organization_id="org-1",
                user_id="user-2",
                chat_id="chat-2",
                content="Card 4111 1111 1111 1111 and bank account number.",
            ),
        ]
    )

    assert result["dlp_matches"] >= 3
    assert result["classifications"] == {"Financial Account": 1, "PCI Card": 1, "PHI": 1}


def test_classify_claude_records_keeps_clean_chats_empty() -> None:
    result = classify_sync_records(
        [
            ClaudeComplianceRecord(
                organization_id="org-1",
                user_id="user-1",
                chat_id="chat-1",
                content="Summarize the project status.",
            )
        ]
    )

    assert result == {"dlp_matches": 0, "classifications": {}}
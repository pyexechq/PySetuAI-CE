from app.services.policy_assist_service import list_condition_help_examples, suggest_policy_rules


def test_condition_help_includes_core_patterns() -> None:
    examples = list_condition_help_examples()
    titles = {item["title"] for item in examples}
    assert "Prompt substring match" in titles
    assert "EU residency gate" in titles


def test_suggest_injection_rules_from_goal() -> None:
    result = suggest_policy_rules(goal="block prompt injection and ignore previous instructions")
    names = {item["name"] for item in result["suggestions"]}
    assert "Block instruction override" in names
    assert result["summary"]


def test_suggest_respects_existing_rule_names() -> None:
    result = suggest_policy_rules(
        goal="block jailbreak dan mode",
        existing_rule_names=["Block DAN jailbreak"],
    )
    names = {item["name"] for item in result["suggestions"]}
    assert "Block DAN jailbreak" not in names


def test_suggest_from_policy_name_without_goal() -> None:
    result = suggest_policy_rules(policy_name="Jailbreak Prevention")
    assert len(result["suggestions"]) >= 2
    assert "jailbreak" in result["summary"].lower() or "starter" in result["summary"].lower()


def test_custom_goal_fallback_contains_phrase() -> None:
    result = suggest_policy_rules(goal="block requests about internal api keys")
    assert len(result["suggestions"]) == 1
    assert "prompt.contains" in result["suggestions"][0]["condition"]

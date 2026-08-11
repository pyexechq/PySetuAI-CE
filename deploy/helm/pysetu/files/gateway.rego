package pysetu.gateway

default decision = {"allow": true, "violations": [], "engine": "opa"}

decision = {"allow": true, "violations": [], "engine": "opa"} {
	count(violations) == 0
}

decision = {"allow": false, "violations": violations, "engine": "opa"} {
	count(violations) > 0
}

violations[v] {
	input.content.has_pii
	input.environment.region != "EU"
	input.resource.bundle == "Strict Security"
	v := {
		"rule": "ABAC Strict Bundle EU Residency",
		"message": "Strict Security bundle requires EU region when PII is present",
		"severity": "critical",
	}
}

violations[v] {
	input.subject.role == "developer"
	premium_model[input.request.routed_model]
	v := {
		"rule": "ABAC Developer Model Restriction",
		"message": sprintf("Developers cannot route to premium model %s", [input.request.routed_model]),
		"severity": "medium",
	}
}

violations[v] {
	input.subject.auth_type == "client_key"
	input.content.risk == "critical"
	input.resource.bundle != "Strict Security"
	v := {
		"rule": "ABAC Client Key Risk Cap",
		"message": "Client API keys cannot process critical-risk content unless bound to Strict Security bundle",
		"severity": "high",
	}
}

violations[v] {
	input.subject.auth_type == "client_key"
	input.resource.bundle == "Standard Support"
	input.content.risk == "high"
	hour := input.environment.hour_utc
	hour < 8
	v := {
		"rule": "ABAC Support Key Quiet Hours",
		"message": "High-risk support-agent traffic blocked outside UTC business hours (08:00-22:00)",
		"severity": "medium",
	}
}

violations[v] {
	input.subject.auth_type == "client_key"
	input.resource.bundle == "Standard Support"
	input.content.risk == "high"
	hour := input.environment.hour_utc
	hour > 22
	v := {
		"rule": "ABAC Support Key Quiet Hours",
		"message": "High-risk support-agent traffic blocked outside UTC business hours (08:00-22:00)",
		"severity": "medium",
	}
}

premium_model = {
	"GPT-4o": true,
	"Claude 3.5 Sonnet": true,
	"Gemini 1.5 Pro": true,
}

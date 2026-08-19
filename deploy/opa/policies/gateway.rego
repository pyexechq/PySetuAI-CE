package pysetu.gateway

default decision = {"allow": true, "violations": [], "engine": "opa"}

decision = {"allow": true, "violations": [], "engine": "opa"} {
	count(violations) == 0
}

decision = {"allow": false, "violations": violations, "engine": "opa"} {
	count(violations) > 0
}

# Strict Security bundle: PII must stay in EU region.
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

# Developers cannot route to premium models.
violations[v] {
	input.subject.role == "developer"
	premium_model[input.request.routed_model]
	v := {
		"rule": "ABAC Developer Model Restriction",
		"message": sprintf("Developers cannot route to premium model %s", [input.request.routed_model]),
		"severity": "medium",
	}
}

# Client API keys cannot process critical-risk content unless on Strict Security bundle.
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

# Support-agent keys: block high-risk traffic outside UTC business hours.
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

# Data-movement: restricted sensitivity labels cannot reach vector stores or embedding pipelines.
restricted_data_movement = {
	"RESTRICTED_PII": true,
	"RESTRICTED_PHI": true,
	"RESTRICTED_PCI": true,
}

vector_destinations = {
	"pinecone": true,
	"vector_store": true,
	"embedding": true,
}

never_exempt_labels = {
	"RESTRICTED_PHI": true,
	"RESTRICTED_PCI": true,
}

tenant_policy_active {
	input.tenant_policy.customized == true
}

effective_restricted[label] {
	tenant_policy_active
	label := input.tenant_policy.restricted_labels[_]
}

effective_restricted[label] {
	not tenant_policy_active
	restricted_data_movement[label]
}

effective_vector_destinations[dest] {
	tenant_policy_active
	dest := input.tenant_policy.vector_destinations[_]
}

effective_vector_destinations[dest] {
	not tenant_policy_active
	vector_destinations[dest]
}

effective_never_exempt[label] {
	tenant_policy_active
	label := input.tenant_policy.never_exempt_labels[_]
}

effective_never_exempt[label] {
	not tenant_policy_active
	never_exempt_labels[label]
}

exemption_covers_movement {
	input.exemption.valid == true
	input.exemption.allowed_destinations[input.movement.to]
	count(blocked_exempt_labels) == 0
}

blocked_exempt_labels[label] {
	label := input.data.sensitivity_labels[_]
	effective_never_exempt[label]
}

blocked_exempt_labels[label] {
	label := input.data.sensitivity_labels[_]
	label == "RESTRICTED_PII"
	vector_store_destinations[input.movement.to]
}

vector_store_destinations = {
	"pinecone": true,
	"vector_store": true,
}

violations[v] {
	input.movement.to == dest
	effective_vector_destinations[dest]
	label := input.data.sensitivity_labels[_]
	effective_restricted[label]
	not exemption_covers_movement
	v := {
		"rule": "ABAC Data Movement Restriction",
		"message": sprintf("Sensitivity label %s cannot be sent to %s (%s)", [label, input.movement.to, input.movement.operation]),
		"severity": "critical",
	}
}

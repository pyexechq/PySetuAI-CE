"""Pydantic schemas for the Homegrown Intent & Risk Classifier."""

from __future__ import annotations

import uuid
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class ClassifierRuleCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128, description="Rule name")
    description: Optional[str] = None
    scope: str = Field("global", description="'global' (1-to-many all tenants) or 'tenant' (1-to-1 specific tenant)")
    tenant_id: Optional[uuid.UUID] = Field(None, description="Target tenant ID if scope is 'tenant'")
    action: str = Field("block", description="'block', 'redact', 'monitor', 'request_approval'")
    risk_level: str = Field("high", description="'low', 'medium', 'high', 'critical'")
    pattern_type: str = Field("composite", description="'keyword', 'regex', 'ast_syntax', 'composite'")
    keywords: List[str] = Field(default_factory=list)
    regex_pattern: Optional[str] = None
    syntax_rules: Optional[dict[str, Any]] = None
    confidence_threshold: float = Field(0.75, ge=0.0, le=1.0)
    is_active: bool = True
    explanation_template: Optional[str] = None


class ClassifierRuleUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[str] = None
    action: Optional[str] = None
    risk_level: Optional[str] = None
    pattern_type: Optional[str] = None
    keywords: Optional[List[str]] = None
    regex_pattern: Optional[str] = None
    syntax_rules: Optional[dict[str, Any]] = None
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_active: Optional[bool] = None
    explanation_template: Optional[str] = None


class ClassifierRuleResponse(BaseModel):
    id: str
    tenant_id: Optional[str] = None
    scope: str = "global"
    name: str
    description: Optional[str] = None
    action: str = "block"
    risk_level: str = "high"
    pattern_type: str = "composite"
    keywords: List[str] = Field(default_factory=list)
    regex_pattern: Optional[str] = None
    syntax_rules: Optional[dict[str, Any]] = None
    confidence_threshold: float = 0.75
    is_active: bool = True
    is_system: bool = False
    explanation_template: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ClassifierTestRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Payload text or prompt to test against classifier")
    tenant_id: Optional[uuid.UUID] = Field(None, description="Optional tenant context for testing 1-to-1 rules")
    tool_name: Optional[str] = Field(None, description="Optional MCP tool name")
    tool_arguments: Optional[dict[str, Any]] = Field(None, description="Optional MCP tool arguments")


class ClassifierMatchItem(BaseModel):
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    scope: str = "global"
    category: str
    action: str
    risk_level: str
    score: int
    matched_tokens: Optional[List[str]] = None
    matched_token: Optional[str] = None
    start: Optional[int] = None
    end: Optional[int] = None
    explanation: str


class ClassifierTestResponse(BaseModel):
    verdict: str
    risk_score: int
    risk_tier: str
    execution_time_micros: float
    latency_ms: float
    engine: str = "pysetu-deterministic-classifier-v2"
    deobfuscated: bool = False
    is_blocked: bool
    is_redacted: bool
    matches: List[ClassifierMatchItem]
    modified_text: Optional[str] = None


class ClassifierEfficiencyMetricsResponse(BaseModel):
    total_scans: int
    blocked_count: int
    redacted_count: int
    block_rate_percent: float
    avg_latency_micros: float
    avg_latency_ms: float
    engine_efficiency: str = "100% Deterministic (Zero-AI Overhead)"
    category_distribution: dict[str, int]
    recent_trend: List[dict[str, Any]]


class ClassifierAiAssistRequest(BaseModel):
    goal: str = Field(..., min_length=3, description="Natural language description of intent/risk to block or monitor")
    target_scope: str = Field("global", description="'global' (1-to-many) or 'tenant' (1-to-1)")


class ClassifierAiAssistResponse(BaseModel):
    name: str
    description: str
    scope: str = "global"
    action: str = "block"
    risk_level: str = "high"
    pattern_type: str = "composite"
    keywords: List[str]
    regex_pattern: str
    confidence_threshold: float = 0.75
    explanation_template: str
    test_phrases: Optional[dict[str, List[str]]] = None


class ClassifierBenchmarkRequest(BaseModel):
    file_content: Optional[str] = Field(None, description="Raw CSV or JSONL text if uploading custom dataset")
    file_format: str = Field("jsonl", description="'jsonl' or 'csv'")
    sample_limit: Optional[int] = Field(None, description="Optional cap on rows to evaluate (e.g. 1000, 5000, 10000)")


class ClassifierBenchmarkResponse(BaseModel):
    total_rows_evaluated: int
    total_time_ms: float
    scan_rate_per_sec: float
    accuracy_percent: float
    precision_percent: float
    recall_percent: float
    f1_score_percent: float
    false_positive_rate_percent: float
    latency_profile: dict[str, Any]
    confusion_matrix: dict[str, int]
    scenario_breakdown: List[dict[str, Any]]
    missed_samples: List[dict[str, Any]]


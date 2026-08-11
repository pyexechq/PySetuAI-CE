{{/*
Expand the name of the chart.
*/}}
{{- define "pysetu.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "pysetu.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "pysetu.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "pysetu.labels" -}}
helm.sh/chart: {{ include "pysetu.chart" . }}
{{ include "pysetu.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "pysetu.selectorLabels" -}}
app.kubernetes.io/name: {{ include "pysetu.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "pysetu.componentLabels" -}}
{{ include "pysetu.labels" . }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{- define "pysetu.componentSelectorLabels" -}}
{{ include "pysetu.selectorLabels" . }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{- define "pysetu.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "pysetu.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "pysetu.postgresql.host" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" (include "pysetu.fullname" .) }}
{{- else }}
{{- required "postgresql.external.host is required when postgresql.enabled=false" .Values.postgresql.external.host }}
{{- end }}
{{- end }}

{{- define "pysetu.postgresql.port" -}}
{{- if .Values.postgresql.enabled }}
5432
{{- else }}
{{- .Values.postgresql.external.port }}
{{- end }}
{{- end }}

{{- define "pysetu.databaseUrl" -}}
{{- $user := .Values.postgresql.auth.username -}}
{{- $pass := .Values.postgresql.auth.password -}}
{{- $db := .Values.postgresql.auth.database -}}
{{- $host := include "pysetu.postgresql.host" . -}}
{{- $port := include "pysetu.postgresql.port" . -}}
{{- printf "postgresql+asyncpg://%s:%s@%s:%s/%s" $user $pass $host $port $db -}}
{{- end }}

{{- define "pysetu.redisUrl" -}}
{{- if .Values.redis.enabled }}
{{- printf "redis://%s-redis:6379/0" (include "pysetu.fullname" .) -}}
{{- else }}
{{- required "redis.external.url is required when redis.enabled=false" .Values.redis.external.url -}}
{{- end }}
{{- end }}

{{- define "pysetu.opaUrl" -}}
{{- if .Values.opa.enabled }}
{{- printf "http://%s-opa:8181" (include "pysetu.fullname" .) -}}
{{- else }}
http://localhost:8181
{{- end }}
{{- end }}

{{- define "pysetu.backendEnv" -}}
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "pysetu.secretName" . }}
      key: database-url
- name: REDIS_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "pysetu.secretName" . }}
      key: redis-url
- name: JWT_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "pysetu.secretName" . }}
      key: jwt-secret-key
- name: OPENAI_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "pysetu.secretName" . }}
      key: openai-api-key
      optional: true
- name: GEMINI_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "pysetu.secretName" . }}
      key: gemini-api-key
      optional: true
- name: VAULT_TOKEN
  valueFrom:
    secretKeyRef:
      name: {{ include "pysetu.secretName" . }}
      key: vault-token
      optional: true
- name: DEBUG
  value: {{ .Values.config.debug | quote }}
- name: CORS_ORIGINS
  value: {{ .Values.config.corsOrigins | quote }}
- name: FRONTEND_URL
  value: {{ .Values.config.frontendUrl | quote }}
- name: GATEWAY_MOCK_MODE
  value: {{ .Values.config.gatewayMockMode | quote }}
- name: OLLAMA_ENABLED
  value: {{ .Values.config.ollamaEnabled | quote }}
- name: OLLAMA_BASE_URL
  value: {{ .Values.config.ollamaBaseUrl | quote }}
- name: OLLAMA_DEFAULT_MODEL
  value: {{ .Values.config.ollamaDefaultModel | quote }}
- name: GEMINI_DEFAULT_MODEL
  value: {{ .Values.config.geminiDefaultModel | quote }}
- name: OPA_ENABLED
  value: {{ .Values.config.opaEnabled | quote }}
- name: OPA_BASE_URL
  value: {{ include "pysetu.opaUrl" . | quote }}
- name: OPA_FAIL_OPEN
  value: {{ .Values.config.opaFailOpen | quote }}
- name: OPA_POLICY_PATH
  value: {{ .Values.config.opaPolicyPath | quote }}
- name: OTEL_ENABLED
  value: {{ .Values.config.otelEnabled | quote }}
- name: SMTP_ENABLED
  value: {{ .Values.config.smtpEnabled | quote }}
- name: SMTP_HOST
  value: {{ .Values.config.smtpHost | quote }}
- name: SMTP_PORT
  value: {{ .Values.config.smtpPort | quote }}
- name: SMTP_FROM
  value: {{ .Values.config.smtpFrom | quote }}
- name: SMTP_USE_TLS
  value: {{ .Values.config.smtpUseTls | quote }}
- name: VAULT_ENABLED
  value: {{ .Values.config.vaultEnabled | quote }}
- name: VAULT_ADDR
  value: {{ .Values.config.vaultAddr | quote }}
- name: LLM_REBALANCE_SCHEDULE_ENABLED
  value: {{ .Values.config.llmRebalanceScheduleEnabled | quote }}
- name: LLM_REBALANCE_CRON_HOUR
  value: {{ .Values.config.llmRebalanceCronHour | quote }}
- name: LLM_REBALANCE_CRON_MINUTE
  value: {{ .Values.config.llmRebalanceCronMinute | quote }}
- name: AIR_GAP_MODE
  value: {{ .Values.config.airGapMode | quote }}
{{- end }}

{{- define "pysetu.secretName" -}}
{{- if .Values.secrets.existingSecret }}
{{- .Values.secrets.existingSecret }}
{{- else }}
{{- printf "%s-secrets" (include "pysetu.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Expand the name of the chart.
*/}}
{{- define "helixguard.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "helixguard.fullname" -}}
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

{{- define "helixguard.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "helixguard.labels" -}}
helm.sh/chart: {{ include "helixguard.chart" . }}
{{ include "helixguard.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "helixguard.selectorLabels" -}}
app.kubernetes.io/name: {{ include "helixguard.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "helixguard.componentLabels" -}}
{{ include "helixguard.labels" . }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{- define "helixguard.componentSelectorLabels" -}}
{{ include "helixguard.selectorLabels" . }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{- define "helixguard.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "helixguard.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "helixguard.postgresql.host" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "%s-postgresql" (include "helixguard.fullname" .) }}
{{- else }}
{{- required "postgresql.external.host is required when postgresql.enabled=false" .Values.postgresql.external.host }}
{{- end }}
{{- end }}

{{- define "helixguard.postgresql.port" -}}
{{- if .Values.postgresql.enabled }}
5432
{{- else }}
{{- .Values.postgresql.external.port }}
{{- end }}
{{- end }}

{{- define "helixguard.databaseUrl" -}}
{{- $user := .Values.postgresql.auth.username -}}
{{- $pass := .Values.postgresql.auth.password -}}
{{- $db := .Values.postgresql.auth.database -}}
{{- $host := include "helixguard.postgresql.host" . -}}
{{- $port := include "helixguard.postgresql.port" . -}}
{{- printf "postgresql+asyncpg://%s:%s@%s:%s/%s" $user $pass $host $port $db -}}
{{- end }}

{{- define "helixguard.redisUrl" -}}
{{- if .Values.redis.enabled }}
{{- printf "redis://%s-redis:6379/0" (include "helixguard.fullname" .) -}}
{{- else }}
{{- required "redis.external.url is required when redis.enabled=false" .Values.redis.external.url -}}
{{- end }}
{{- end }}

{{- define "helixguard.opaUrl" -}}
{{- if .Values.opa.enabled }}
{{- printf "http://%s-opa:8181" (include "helixguard.fullname" .) -}}
{{- else }}
http://localhost:8181
{{- end }}
{{- end }}

{{- define "helixguard.backendEnv" -}}
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "helixguard.secretName" . }}
      key: database-url
- name: REDIS_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "helixguard.secretName" . }}
      key: redis-url
- name: JWT_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "helixguard.secretName" . }}
      key: jwt-secret-key
- name: OPENAI_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "helixguard.secretName" . }}
      key: openai-api-key
      optional: true
- name: GEMINI_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "helixguard.secretName" . }}
      key: gemini-api-key
      optional: true
- name: VAULT_TOKEN
  valueFrom:
    secretKeyRef:
      name: {{ include "helixguard.secretName" . }}
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
  value: {{ include "helixguard.opaUrl" . | quote }}
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

{{- define "helixguard.secretName" -}}
{{- if .Values.secrets.existingSecret }}
{{- .Values.secrets.existingSecret }}
{{- else }}
{{- printf "%s-secrets" (include "helixguard.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Expand the name of the chart.
*/}}
{{- define "dsa5.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified app name.
*/}}
{{- define "dsa5.fullname" -}}
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

{{/*
Chart label value.
*/}}
{{- define "dsa5.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "dsa5.labels" -}}
helm.sh/chart: {{ include "dsa5.chart" . }}
{{ include "dsa5.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "dsa5.selectorLabels" -}}
app.kubernetes.io/name: {{ include "dsa5.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Service account name.
*/}}
{{- define "dsa5.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "dsa5.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Name of the secret holding service credentials.
*/}}
{{- define "dsa5.secretName" -}}
{{- if .Values.existingSecret }}
{{- .Values.existingSecret }}
{{- else }}
{{- include "dsa5.fullname" . }}
{{- end }}
{{- end }}

{{/*
MongoDB connection URI.
*/}}
{{- define "dsa5.mongoUri" -}}
{{- if .Values.mongodb.externalUri }}
{{- .Values.mongodb.externalUri }}
{{- else }}
{{- printf "mongodb://%s-mongodb:27017/girder?socketTimeoutMS=3600000" (include "dsa5.fullname" .) }}
{{- end }}
{{- end }}

{{/*
RabbitMQ host.
*/}}
{{- define "dsa5.rabbitmqHost" -}}
{{- if .Values.rabbitmq.externalHost }}
{{- .Values.rabbitmq.externalHost }}
{{- else }}
{{- printf "%s-rabbitmq" (include "dsa5.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Redis host (Girder 5 uses Redis for notification and large-image caching).
*/}}
{{- define "dsa5.redisHost" -}}
{{- if .Values.redis.externalHost }}
{{- .Values.redis.externalHost }}
{{- else }}
{{- printf "%s-redis" (include "dsa5.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Girder web image.
*/}}
{{- define "dsa5.girderImage" -}}
{{- printf "%s:%s" .Values.girder.image.repository .Values.girder.image.tag }}
{{- end }}

{{/*
Worker image.
*/}}
{{- define "dsa5.workerImage" -}}
{{- printf "%s:%s" .Values.worker.image.repository .Values.worker.image.tag }}
{{- end }}

{{/*
Environment shared by the Girder and worker containers.
*/}}
{{- define "dsa5.commonEnv" -}}
- name: DSA_USER
  value: {{ .Values.girder.dsaUser | quote }}
- name: GIRDER_MONGO_URI
  value: {{ include "dsa5.mongoUri" . | quote }}
- name: CELERY_BROKER_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "dsa5.secretName" . }}
      key: celery-broker-url
- name: CELERY_RESULT_BACKEND
  valueFrom:
    secretKeyRef:
      name: {{ include "dsa5.secretName" . }}
      key: celery-result-backend
- name: GIRDER_NOTIFICATION_REDIS_URL
  value: {{ printf "redis://%s:6379" (include "dsa5.redisHost" .) | quote }}
- name: LARGE_IMAGE_CACHE_BACKEND
  value: redis
- name: LARGE_IMAGE_CACHE_REDIS_URL
  value: {{ printf "%s:6379" (include "dsa5.redisHost" .) | quote }}
{{- if and .Values.girder.dockerSocket.enabled (eq .Values.girder.dockerSocket.mode "dind") }}
- name: DOCKER_HOST
  value: unix:///var/run/docker.sock
{{- end }}
{{- end }}

{{/*
Environment for the Girder container.
*/}}
{{- define "dsa5.girderEnv" -}}
{{- include "dsa5.commonEnv" . | nindent 0 }}
- name: DSA_PROVISION_YAML
  value: /provision/provision.yaml
- name: GIRDER_SERVER_MODE
  value: production
- name: GIRDER_SETTING_CORE_CACHE_ENABLED
  value: "true"
- name: GIRDER_SETTING_CORE_HTTP_ONLY_COOKIES
  value: "false"
- name: HISTOMICSUI_RESTRICT_DOWNLOADS
  value: "100000"
- name: LARGE_IMAGE_CACHE_TILESOURCE_MAXIMUM
  value: "64"
{{- with .Values.girder.extraEnv }}
{{- toYaml . | nindent 0 }}
{{- end }}
{{- end }}

{{/*
Volume mounts for the Girder container.  Girder 5 uses the ver5 start script.
*/}}
{{- define "dsa5.girderVolumeMounts" -}}
- name: assetstore
  mountPath: /assetstore
- name: provision
  mountPath: /provision
- name: provision-script
  mountPath: /opt/digital_slide_archive/devops/dsa/provision.py
  subPath: provision.py
{{- if .Values.girder.dockerSocket.enabled }}
{{- if eq .Values.girder.dockerSocket.mode "dind" }}
- name: docker-socket
  mountPath: /var/run
- name: tmp
  mountPath: /tmp
{{- else }}
- name: docker-socket
  mountPath: /var/run/docker.sock
{{- end }}
{{- end }}
{{- end }}

{{/*
Environment for the worker container.
*/}}
{{- define "dsa5.workerEnv" -}}
{{- include "dsa5.commonEnv" . | nindent 0 }}
- name: DSA_PROVISION_YAML
  value: /provision/provision.yaml
- name: DSA_WORKER_CONCURRENCY
  value: {{ .Values.worker.concurrency | quote }}
- name: RABBITMQ_USER
  valueFrom:
    secretKeyRef:
      name: {{ include "dsa5.secretName" . }}
      key: rabbitmq-user
- name: RABBITMQ_PASS
  valueFrom:
    secretKeyRef:
      name: {{ include "dsa5.secretName" . }}
      key: rabbitmq-password
- name: DSA_RABBITMQ_HOST
  value: {{ include "dsa5.rabbitmqHost" . | quote }}
- name: TMPDIR
  value: /tmp
{{- with .Values.worker.extraEnv }}
{{- toYaml . | nindent 0 }}
{{- end }}
{{- end }}

{{/*
Volume mounts for the worker container.
*/}}
{{- define "dsa5.workerVolumeMounts" -}}
- name: assetstore
  mountPath: /assetstore
- name: provision
  mountPath: /provision
- name: provision-script
  mountPath: /opt/digital_slide_archive/devops/dsa/provision.py
  subPath: provision.py
- name: tmp
  mountPath: /tmp
{{- if .Values.worker.dockerSocket.enabled }}
{{- if eq .Values.worker.dockerSocket.mode "dind" }}
- name: docker-socket
  mountPath: /var/run
{{- else }}
- name: docker-socket
  mountPath: /var/run/docker.sock
{{- end }}
{{- end }}
{{- end }}

variable "resource_group_name" {
  description = "Name of the main resource group"
  type        = string
  default     = "shopflow-rg"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "canadacentral"
}

variable "project_name" {
  description = "Project name used as a prefix for resources"
  type        = string
  default     = "shopflow"
}

variable "github_actions_app_id" {
  description = "App ID of the GitHub Actions service principal"
  type        = string
}

variable "grafana_password" {
  description = "Grafana admin password"
  type        = string
  sensitive   = true
}
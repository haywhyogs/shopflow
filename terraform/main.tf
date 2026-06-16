resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
}
data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                       = "shopflow-kv"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  sku_name                    = "standard"
  enable_rbac_authorization   = true
}

resource "azurerm_key_vault_secret" "grafana_password" {
  name         = "grafana-admin-password"
  value        = "placeholder"
  key_vault_id = azurerm_key_vault.main.id

  tags = {
    "file-encoding" = "utf-8"
  }

  lifecycle {
    ignore_changes = [value, tags]
  }
}

resource "azurerm_container_registry" "main" {
  name                = "shopflowacr"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = false
}
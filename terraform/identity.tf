resource "azurerm_user_assigned_identity" "main" {
  name                = "shopflow-identity"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.main.principal_id
}

resource "azurerm_role_assignment" "kv_secrets_user" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.main.principal_id
}

resource "azurerm_role_assignment" "kv_reader" {
  scope                = azurerm_resource_group.main.id
  role_definition_name = "Key Vault Reader"
  principal_id         = azurerm_user_assigned_identity.main.principal_id
}

resource "azurerm_role_assignment" "terraform_kv_access" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

data "azuread_service_principal" "github_actions" {
  client_id = var.github_actions_app_id
}

resource "azurerm_role_assignment" "github_actions_reader" {
  scope                = "/subscriptions/${data.azurerm_client_config.current.subscription_id}"
  role_definition_name = "Reader"
  principal_id         = data.azuread_service_principal.github_actions.object_id
}

resource "azurerm_role_assignment" "github_actions_acr_push" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPush"
  principal_id         = data.azuread_service_principal.github_actions.object_id
}

resource "azurerm_role_definition" "vm_run_command" {
  name        = "ShopFlow VM Run Command"
  scope       = "/subscriptions/${data.azurerm_client_config.current.subscription_id}"
  description = "Allows GitHub Actions to execute run-command on ShopFlow VM only"

  permissions {
    actions = [
      "Microsoft.Compute/virtualMachines/runCommand/action",
      "Microsoft.Compute/virtualMachines/read"
    ]
    not_actions = []
  }

  assignable_scopes = [
    "/subscriptions/${data.azurerm_client_config.current.subscription_id}"
  ]
}

resource "azurerm_role_assignment" "github_actions_run_command" {
  scope              = azurerm_linux_virtual_machine.main.id
  role_definition_id = azurerm_role_definition.vm_run_command.role_definition_resource_id
  principal_id       = data.azuread_service_principal.github_actions.object_id
}
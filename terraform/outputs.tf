output "public_ip" {
  value = azurerm_public_ip.main.ip_address
}

output "vm_name" {
  value = azurerm_linux_virtual_machine.main.name
}

output "acr_login_server" {
  value = azurerm_container_registry.main.login_server
}
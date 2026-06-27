terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "shopflow-tfstate-rg"
    storage_account_name = "shopflowtfstate"
    container_name        = "tfstate"
    key                   = "shopflow.terraform.tfstate"
  }
}

provider "azurerm" {
  features {}
}

provider "azuread" {}
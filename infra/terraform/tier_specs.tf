# Wiki-aligned sizing: infra/wiki.md Tier tables (Veho terraform-modules on GitHub).
locals {
  tier_specs_wiki_environment = (
    lower(var.env_suffix) == "prod" ? "prod" :
    contains(["stg", "staging"], lower(var.env_suffix)) ? "stg" :
    "dev"
  )
}

module "tier_specs" {
  source = "git::https://github.com/TeckVeho/terraform-modules.git//modules/tier_specs?ref=develop"

  tier        = lower(trimspace(var.resource_tier != "" ? var.resource_tier : "tier4"))
  environment = local.tier_specs_wiki_environment
}

locals {
  tier_api = module.tier_specs.api
  tier_web = module.tier_specs.web

  cloud_run_api_min_instances_effective = coalesce(var.cloud_run_api_min_instances, local.tier_api.min_instances)
  cloud_run_api_max_instances_effective = coalesce(var.cloud_run_api_max_instances, local.tier_api.max_instances)
  cloud_run_api_cpu_effective           = coalesce(var.cloud_run_api_cpu, local.tier_api.cpu)
  cloud_run_api_memory_effective        = coalesce(var.cloud_run_api_memory, local.tier_api.memory)
  cloud_run_api_timeout_effective       = coalesce(var.cloud_run_api_timeout, local.tier_api.timeout)
  cloud_run_api_concurrency_effective   = coalesce(var.cloud_run_api_concurrency, local.tier_api.concurrency)
  cloud_run_web_min_instances_effective = coalesce(var.cloud_run_web_min_instances, local.tier_web.min_instances)
  cloud_run_web_max_instances_effective = coalesce(var.cloud_run_web_max_instances, local.tier_web.max_instances)
  cloud_run_web_cpu_effective           = coalesce(var.cloud_run_web_cpu, local.tier_web.cpu)
  cloud_run_web_memory_effective        = coalesce(var.cloud_run_web_memory, local.tier_web.memory)
  cloud_run_web_timeout_effective       = coalesce(var.cloud_run_web_timeout, local.tier_web.timeout)
  cloud_run_web_concurrency_effective   = coalesce(var.cloud_run_web_concurrency, local.tier_web.concurrency)

  sql_tier_effective         = coalesce(var.sql_tier, module.tier_specs.sql_instance_tier)
  sql_disk_size_gb_effective = coalesce(var.sql_disk_size_gb, module.tier_specs.sql_disk_size_gb)
  sql_disk_type_effective    = coalesce(var.sql_disk_type, module.tier_specs.sql_disk_type)
}

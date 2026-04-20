# Terraform — VPC (separate stack)

This stack creates a **custom VPC + subnet + Private Service Access** (Service Networking) so Cloud SQL can use **private IP** (satisfies `constraints/sql.restrictPublicIp`). The app stack attaches Cloud Run with **Direct VPC egress** (`PRIVATE_RANGES_ONLY`) to reach SQL over the private path — **not** the legacy Serverless VPC Access Connector.

**Cloud NAT** is **not** required for that pattern (no private-only workload in the VPC needs outbound Internet via NAT). Add NAT only if you later route all egress through the VPC or run VMs without public IPs that need the Internet.

## Workflow

1. Create the GCS state bucket if needed (see [`../bootstrap/`](../bootstrap/)). Backend là **partial** (`backend.tf`): chọn state bằng `terraform init -reconfigure -backend-config=backend.tf.dev` hoặc `…=backend.tf.prod` (bucket/prefix trong các file đó). Prefix **khác nhau** theo môi trường, ví dụ `network/dev`, `network/prod`.
2. In this directory: `terraform init -reconfigure -backend-config=backend.tf.<env>` → `terraform apply -var-file=terraform.tfvars.<env>` (cùng `project_id` / `region` / `env_suffix` với stack app).
3. Go to [`../`](../): set `network_remote_state_bucket` and `network_remote_state_prefix` to **match** step 1, then `terraform apply` the app.

**Destroy:** destroy the **app** stack first (Cloud SQL, connector, Cloud Run), then destroy the network stack.

## Outputs consumed by the app stack

- `network_self_link` — attached to Cloud SQL `private_network`.
- `connector_subnet_name` — subnet used for Cloud Run **Direct VPC** network interface (same subnet id; not a separate connector resource).

## CIDR notes

- `connector_subnet_cidr` (default `10.8.0.0/28`) and `private_service_peering_cidr` (default `10.247.0.0/16`) must **not** overlap each other or other subnets in the VPC.

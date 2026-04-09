# Terraform — VPC (stack riêng)

Stack này tạo **VPC + subnet cho Serverless VPC Access + Private Service Access** (Service Networking) để Cloud SQL dùng **private IP** (tuân `constraints/sql.restrictPublicIp`).

## Thứ tự làm việc

1. Tạo bucket GCS cho state (nếu chưa có) và cấu hình `backend.tf` (xem `backend.tf.example`).
2. Trong thư mục này: `terraform init` → `terraform apply` (cùng `tfvars` với `project_id` / `region` / `env_suffix` khớp app).
3. Chuyển sang [`../`](../): đặt `network_remote_state_bucket` và `network_remote_state_prefix` **trùng** backend ở bước 1, rồi `terraform apply` app.

**Destroy:** destroy stack app (Cloud SQL, connector, Cloud Run) **trước**, sau đó mới destroy stack network.

## Outputs dùng bởi stack app

- `network_self_link` — gắn vào Cloud SQL `private_network`.
- `connector_subnet_name` — subnet cho `google_vpc_access_connector` trên Cloud Run.

## Ghi chú CIDR

- `connector_subnet_cidr` (mặc định `10.8.0.0/28`) và `private_service_peering_cidr` (mặc định `10.247.0.0/16`) **không được trùng** nhau hoặc trùng subnet khác trong VPC.

# TERRAFORM OVERVIEW
([back to deployment README](README.md))
([back to supplemental info](supplemental_info.md))

This repository contains Terraform modules to deploy the T2X application and supporting resources in Google Cloud. This overview document provides general instructions to initialize a Terraform workspace/environment, set up a backend configuration and bucket for storing Terraform state, and lists some known issues.


- [Terraform command alias](#terraform-command-alias)
- [Initialize](#initialize)
- [Workspaces](#workspaces)
- [Terraform Backends](#terraform-backends)
- [Flexible Backends - Partial Configuration](#flexible-backends---partial-configuration)
- [Reconfiguring a Backend](#reconfiguring-a-backend)
- [Plan and Apply](#plan-and-apply)
- [Known issues](#known-issues)


## Terraform command alias
([return to top](#terraform-overview))
Commands in this repository assume `tf` is an [alias](https://cloud.google.com/docs/terraform/best-practices-for-terraform#aliases) for `terraform` in your shell.

## Initialize
([return to top](#terraform-overview))
The Terraform working directory must be [initialized](https://developer.hashicorp.com/terraform/cli/init) to set up configuration files and download provider plugins.
```sh
# Initialize the working directory.
tf init
```

## Workspaces
([return to top](#terraform-overview))
[Terraform workspaces](https://developer.hashicorp.com/terraform/cli/workspaces) allow separation of environments so each is managed in a unique state file.

```sh
# View the active and available workspaces (Terraform starts with only the 'default' workspace).
tf workspace list

# Set an environment variable for the deployment environment/workspace name.
export ENVIRONMENT='sandbox'

# Create an environment-specific workspace.
tf workspace new $ENVIRONMENT

# Choose a workspace.
tf workspace select default

# Select a workspace or create it if it doesn't exist.
tf workspace select -or-create nonprod
```

## Terraform Backends
([return to top](#terraform-overview))
Using a local backend doesn't require additional configuration. A [Cloud Storage backend](https://developer.hashicorp.com/terraform/language/settings/backends/configuration) requires these prerequisites:
- The GCS backend bucket must already exist - Terraform will not create it at `init`.
Example (edit with your actual project and bucket name):
```sh
gcloud storage buckets create gs://my-terraform-bucket --project=my-project --uniform-bucket-level-access
```
- The caller or impersonated service account needs permission to read and write to the bucket.
- Define a GCS backend in the `terraform.backend` block.

```terraform
terraform {
  backend "gcs" {
    bucket = "my-terraform-bucket"
    prefix = "terraform_state/"
  }
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "5.25.0"
    }
  }
  required_version = ">= 0.13"
}
```

## Flexible Backends - Partial Configuration
([return to top](#terraform-overview))
- Backend declaration can't accept input variables or use expansion/interpolation because Terraform loads the backend config before anything else.
- A 'partial configuration' in the `terraform.backend` block allows flexible backend definition for multiple environments.
- Options for supplying backend configuration arguments include a file, command-line key/value arguments, [environment variables](https://developer.hashicorp.com/terraform/cli/config/environment-variables), or interactive prompts.
- Define the remaining backend details in a dedicated `*.gcs.tfbackend` file, i.e. `backend_sandbox.gcs.tfbackend` and pass it's path as a command-line argument to separate backends per environment. (Hashicorp docs recommend a `*.backendname.tfbackend` naming convention, but Terraform will accept any correctly-formatted file. IDE syntax highlighting and linting might not pick up `.tfbackend` files.)

Example 1 - environment-specific backend configuration file:
```sh
# Create a workspace-specific backend configuration file for the Google Cloud Storage backend.
cat << EOF > backend_$ENVIRONMENT.gcs.tfbackend
bucket = "my-terraform-bucket"
prefix = "terraform_state/"
EOF

# Initialize the remote state
tf init -backend-config="backend_$ENVIRONMENT.gcs.tfbackend"
```

Partial configurations allow you to include some attributes in the `terraform.backend` block and pass the rest from another source.

Example 2 - define a common file path/prefix in the `terraform.backend` block and choose the GCS bucket and service account to impersonate using configuration options.

`backend.tf`:
```terraform
terraform {
  backend "gcs" {
    prefix = "terraform_state/core_resources"
  }
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "5.25.0"
    }
  }
  required_version = ">= 0.13"
}
```

`.tfbackend` file:
```sh
cat << EOF > backend_$ENVIRONMENT.gcs.tfbackend
bucket                      = "my-terraform-bucket"
impersonate_service_account = "terraform-sa@my-project.iam.gserviceaccount.com"
EOF
```

## Reconfiguring a Backend
([return to top](#terraform-overview))
To force Terraform to use a new backend without [migrating](https://spacelift.io/blog/terraform-migrate-state) state data from an existing backend, [initialize](https://developer.hashicorp.com/terraform/cli/commands/init#backend-initialization) with the `-reconfigure` flag. The existing state in the old backend is left unchanged and not copied to the new backend.
```sh
tf init -reconfigure -backend-config="backend_$ENVIRONMENT.gcs.tfbackend
```

## Plan and Apply
([return to top](#terraform-overview))
Terraform requires declared or default values for [input variables](https://developer.hashicorp.com/terraform/language/values/variables#assigning-values-to-root-module-variables). For example, variables defined in `.tfvars` files to separate environments.

```sh
# Define environment-specific variables in a .tfvars file
cat << EOF > vars_$ENVIRONMENT.tfvars
project_id                = "my-project"
terraform_service_account = "terraform-sa@my-project.iam.gserviceaccount.com"
terraform_bucket_name     = "my-terraform-bucket"
region                    = "us-central1"
zone                      = "us-central1-a"
EOF

# View the Terraform plan.
tf plan -var-file="vars_$ENVIRONMENT.tfvars"

# Apply changes.
tf apply -var-file="vars_$ENVIRONMENT.tfvars"

```

## Known issues
([return to top](#terraform-overview))
The Terraform Google provider sometimes returns an inconsistent plan during `apply` operations. You can usually ignore the error messages because the resources get successfully created or updated.

Example:
```
│ Error: Provider produced inconsistent final plan
│ 
│ When expanding the plan for google_compute_region_backend_service.t2x_backend_api to include new values learned so far during apply, provider "registry.terraform.io/hashicorp/google" produced an invalid new value for
│ .backend: planned set element cty.ObjectVal(map[string]cty.Value{"balancing_mode":cty.StringVal("UTILIZATION"), "capacity_scaler":cty.NumberIntVal(1), "description":cty.StringVal(""), "failover":cty.UnknownVal(cty.Bool),
│ "group":cty.UnknownVal(cty.String), "max_connections":cty.NullVal(cty.Number), "max_connections_per_endpoint":cty.NullVal(cty.Number), "max_connections_per_instance":cty.NullVal(cty.Number),
│ "max_rate":cty.NullVal(cty.Number), "max_rate_per_endpoint":cty.NullVal(cty.Number), "max_rate_per_instance":cty.NullVal(cty.Number), "max_utilization":cty.MustParseNumberVal("0.8")}) does not correlate with any element
│ in actual.
│ 
│ This is a bug in the provider, which should be reported in the provider's own issue tracker.
```

Intermittent connectivity issues (for example, while using a VPN) can cause unresponsiveness during `plan` or `apply` operations. Retry the operation to clear the error.

Example:
```
│ Error: Error when reading or editing RedisInstance "projects/my-project/locations/us-central1/instances/my-redis-instance": Get "https://redis.googleapis.com/v1/projects/my-project/locations/us-central1/instances/my-redis-instance?alt=json": write tcp [fe80::ca4b:d6ff:fec7:8a11%utun1]:59235->[2607:f8b0:4009:809::200a]:443: write: socket is not connected
│ 
│   with google_redis_instance.default,
│   on redis.tf line 79, in resource "google_redis_instance" "default":
│   79: resource "google_redis_instance" "default" {
│ 
╵
```

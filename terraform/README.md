# TALK TO DOCS APPLICATION DEPLOYMENT WITH TERRAFORM
([back to Terraform overview](terraform_overview.md))
([back to supplemental info](supplemental_info.md))

## Overview
Terraform modules to stage and deploy the application components. The `bootstrap` module provisions the Cloud Build service account, IAM roles, and staging bucket for the main modules. The `main` module provisions all other components. 

- [Architecture](#architecture)
    - [T2X Application build process](#t2x-application-build-process)
    - [T2X Application Service details](#t2x-application-service-details)
- [Directory Structure](#directory-structure)
- [Prerequisites](#prerequisites)
    - [Initialize](#1-initialize)
    - [Create a service account for Terraform provisioning](#2-create-a-service-account-for-terraform-provisioning)
    - [Grant the required IAM roles to the service account](#3-grant-the-required-iam-roles-to-the-service-account)
    - [Use Service Account Impersonation](#4-use-service-account-impersonation)
    - [Terraform remote state](#5-terraform-remote-state)
    - [Bootstrap](#6-bootstrap)
    - [Stage document extractions](#7-stage-document-extractions)
- [Automate Deployments with Cloud Build](#automate-deployments-with-cloud-build)
    - [Set environment variables](#1-set-environment-variables)
    - [Build the docker image for the `discoveryengine-tools` service](#2-build--push-the-docker-images-and-apply-the-terraform-configuration)

### REFERENCE INFO
- [Rollbacks](#rollbacks)
- [Security](#security)
- [Observability](#observability)


&nbsp;
# Architecture

## T2X Application build process: 
([return to top](#talk-to-docs-application-deployment-with-terraform))

1. Bootstrap the project.
    - Enable APIs.
    - Create a Cloud Build service account with required IAM roles.
    - Create a document staging bucket.
    - Create an Artifact Registry repository.
2. Create a Docker image of the application using Cloud Build.
3. Push the Docker image to Artifact Registry.
4. Apply the Terraform configuration to deploy the T2X application components.
    - Cloud Run services for the T2X API and UI.
    - Agent Builder Data Store and Search engine for [RAG](https://cloud.google.com/use-cases/retrieval-augmented-generation?hl=en).
    - Memorystore Redis for session management.
    - BigQuery for log data storage.
    - Cloud Load Balancer for HTTPS traffic routing and TLS encryption.
    - DNS Managed Zone for private DNS resolution.
    - VPC network and subnet for private communication between Cloud Run and Memorystore Redis.


## T2X Application Service details:
([return to top](#talk-to-docs-application-deployment-with-terraform))\

- Queries reach the T2X application through the [Cloud Load Balancer](https://cloud.google.com/load-balancing/docs/https) URL.
- The T2X [backend service](https://cloud.google.com/load-balancing/docs/backend-service) is the interface for regional Cloud Run backends.
    - Regional failover: Cloud Run services [replicate](https://cloud.google.com/run/docs/resource-model#services) across more than one Compute zone to prevent outages for a single zonal failure.
    - Autoscaling: add/remove group instances to match demand and maintain a minimum number of instances for high availability.
- The application asynchronously writes log data to BigQuery for offline analysis.
- It uses a [private DNS](https://cloud.google.com/dns/docs/zones#create-private-zone) hostname to connect and communicate with Memorystore Redis to support multi-turn conversations.

&nbsp;
# Directory Structure
([return to top](#talk-to-docs-application-deployment-with-terraform))
```sh
terraform/ # this directory
├── README.md # this file
├── supplemental_info.md # details on service account impersonation to move GCS objects and managing git submodules
├── terraform_overview.md # enable project APIs, provision a load balancer, VPC network, and subnet
├── assets/ # architecture diagrams
├── bootstrap/ # provision project APIs, Cloud Build service account, IAM roles, and staging bucket
├── main/ # provision the T2X service components
└── modules/ # reusable Terraform modules called from the `main` module
```

&nbsp;
# Prerequisites
([return to top](#talk-to-docs-application-deployment-with-terraform))\
**A project Owner completes these steps to prepare the environment for Terraform provisioning.**

## 1. Initialize
- Install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install).
- Authenticate.
- Set the default project.
- Create [Application Default Credentials]()
```sh
export PROJECT='my-project-id'
gcloud auth login
gcloud config set project $PROJECT
gcloud auth application-default login
```


## 2. Create a service account for Terraform provisioning.
```sh
gcloud iam service-accounts create terraform-service-account --display-name="Terraform Provisioning Service Account" --project=$PROJECT
```


## 3. Grant the required [IAM roles](https://cloud.google.com/iam/docs/understanding-roles) to the service account.
```sh
roles=(
  "roles/ml.admin"
  "roles/artifactregistry.admin"
  "roles/bigquery.admin"
  "roles/redis.admin"
  "roles/compute.admin"
  "roles/discoveryengine.admin"
  "roles/dns.admin"
  "roles/resourcemanager.projectIamAdmin"
  "roles/run.admin"
  "roles/iam.securityAdmin"
  "roles/iam.serviceAccountAdmin"
  "roles/iam.serviceAccountUser"
  "roles/serviceusage.serviceUsageAdmin"
  "roles/storage.admin"
  "roles/workflows.admin"
)

for role in "${roles[@]}"; do
  gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:terraform-service-account@${PROJECT}.iam.gserviceaccount.com" --role=$role
done

```

- AI Platform Admin (`roles/ml.admin`)
- Artifact Registry Administrator (`roles/artifactregistry.admin`)
- BigQuery Admin (`roles/bigquery.admin`)
- Cloud Memorystore Redis Admin (`roles/redis.admin`)
- Cloud Run Admin (`roles/run.admin`)
- Compute Admin (`roles/compute.admin`)
- Discovery Engine Admin (`roles/discoveryengine.admin`)
- DNS Admin (`roles/dns.admin`)
- Project IAM Admin (`roles/resourcemanager.projectIamAdmin`)
- Security Admin (`roles/iam.securityAdmin`) - required to [set IAM policies on DNS Managed Zones](https://cloud.google.com/dns/docs/zones/iam-per-resource-zones#expandable-1)
- Service Account Admin (`roles/iam.serviceAccountAdmin`)
- Service Account User (`roles/iam.serviceAccountUser`) - required to [attach service accounts to resources](https://cloud.google.com/iam/docs/attach-service-accounts)
- Service Usage Admin (`roles/serviceusage.serviceUsageAdmin`)
- Storage Admin (`roles/storage.admin`)
- Workflows Admin (`roles/workflows.admin`)




## 4. Use [Service Account Impersonation](https://cloud.google.com/iam/docs/service-account-impersonation).
Instead of creating and managing Service Account keys for authentication, this code uses an [impersonation pattern for Terraform](https://cloud.google.com/blog/topics/developers-practitioners/using-google-cloud-service-account-impersonation-your-terraform-code) to fetch access tokens on behalf of a Google Cloud IAM Service Account.
- Enable the Service Usage, IAM, and Service Account Credentials APIs.
```sh
gcloud services enable serviceusage.googleapis.com iam.googleapis.com iamcredentials.googleapis.com
```

- Grant the caller (a Google user account or group address) permission to generate [short-lived access tokens](https://cloud.google.com/iam/docs/create-short-lived-credentials-direct) on behalf of the targeted service account.
    - The caller needs the Account Token Creator role (`roles/iam.serviceAccountTokenCreator`) or a custom role with the `iam.serviceAccounts.getAccessToken` permission.
    - Create a role binding on the Service Account resource to minimize the scope of the permission.
    - Use group membership to manage the role assignment as a best practice.
    - Perhaps counterintuitively, the primitive Owner role (`roles/owner`) does NOT include this permission.
```sh
export MEMBER='group:devops@example.com' # or to add a user -> export MEMBER='user:user@example.com'
gcloud iam service-accounts add-iam-policy-binding "terraform-service-account@${PROJECT}.iam.gserviceaccount.com" --member=$MEMBER --role="roles/iam.serviceAccountTokenCreator"
```


## 5. Terraform remote state
- Create a GCS bucket for the remote Terraform state.
```sh
gcloud storage buckets create "gs://terraform-state-${PROJECT}" --project=$PROJECT
```


## 6. Bootstrap
The `bootstrap` module is a one-time setup to provision resources required for the main module.
- Project APIs.
- Cloud Build service account.
- Artifact Registry repository.
- Staging bucket for document extractions.
- IAM roles for the Cloud Build service account.
    - Project IAM policy: Cloud Build Service Account (`roles/cloudbuild.builds.builder`) role.
    - Terraform service account IAM policy: Service Account Token Creator (`roles/iam.serviceAccountTokenCreator`) role.
- IAM role for the optional Data Mover service account.
    - **The service account must already exist and have permission to read the source documents.**
    - Staging bucket IAM policy: Storage Object User (`roles/storage.objectUser`) role.

### 6a. Set project-specific values in `terraform/bootstrap/backend.tf`.
- `bucket` - the remote state bucket name created in step 5, not the full `gs://` URL. i.e., `terraform-state-my-project-id`.
- `impersonate_service_account` - the Terraform service account email created in Prerequisites step 2. i.e., `terraform-service-account@$my-project-id.iam.gserviceaccount.com`.

### 6b. Set project-specific [input variable](https://developer.hashicorp.com/terraform/language/values/variables#assigning-values-to-root-module-variablesvalues) values in `terraform/bootstrap/vars.auto.tfvars`.
- `project_id` - the target deployment GCP project ID. i.e., `my-project-id`.
- `terraform_service_account` - the Terraform service account email created in Prerequisites step 2.
- `data_mover_service_account` - the optional Data Mover service account email. This service account must already exist and have permission to read the source documents.

### 6c. Provision with Terraform
```sh
export REPO_ROOT=$(git rev-parse --show-toplevel)
cd $REPO_ROOT/terraform/bootstrap
tf init
tf apply
```


## 7. Stage document extractions
- Copying document extractions to the staging bucket is currently a manual process not included in the Terraform configuration.
- The `t2x-api` service later imports the document extractions from the staging bucket to the Agent Builder (Discovery Engine) data store.
&nbsp;
### **Migrate vector data across projects to the staging bucket**
1. Create a Data Mover service account with permission to read from the **source extractions** bucket in the source project.
2. Grant the Data Mover service account the Storage Object User role on the **staging bucket** in the destination project.
    - **Option 1:** Use the `bootstrap` module to grant the Data Mover service account the required permissions.
        - Add the Data Mover service account email address as the value of the `data_mover_service_account` input variable to the `bootstrap` module.
        - The `bootstrap` module grants the Data Mover service account the Storage Object User role on the staging bucket IAM policy.
    - **Option 2:** Manually grant the Data Mover service account the Storage Object User role on the staging bucket or project level IAM policy.
3. Use `gcloud` with service account impersonation to copy vector extractions to the staging bucket.
    - Your `gcloud` authenticated user account must have the Service Account Token Creator (`roles/iam.serviceAccountTokenCreator`) role on the Data Mover service account IAM policy.

```sh
export STAGING_BUCKET='{staging_bucket_name}'
export EXTRACTION_BUCKET='{source_extractions_bucket_name}'
export EXTRACTION_PATH='{source_extractions_folder_path}'
export SERVICE_ACCOUNT='{data_mover_service_account_email}'
gcloud storage cp -r "gs://$EXTRACTION_BUCKET/$EXTRACTION_PATH/*" "gs://$STAGING_BUCKET/source-data/$EXTRACTION_PATH" --impersonate-service-account=$SERVICE_ACCOUNT
```



&nbsp;
# Automate Deployments with Cloud Build
([return to top](#talk-to-docs-application-deployment-with-terraform))

- Use the [`gcloud CLI`](https://cloud.google.com/build/docs/running-builds/submit-build-via-cli-api) with [build config files](https://cloud.google.com/build/docs/configuring-builds/create-basic-configuration) to plan and deploy project resources.
Execute commands in each module.

## 1. Configure `gen_ai/llm.yaml`.
- `dataset_name` - the BigQuery dataset that will store T2X logs.
- `memory_store_ip` - the Memorystore Redis host - should always be `redis.t2xservice.internal`.
- `customer_name` - the company name used in the Agent Builder Search Engine.
- `vais_data_store` - the Agent Builder Data Store ID.
- `vais_engine_id` - the Agent Builder Search Engine ID.

## 2. Configure the Terraform backend, input variables, and main module.

#### Set project-specific values in `terraform/main/backend.tf`.
- `bucket` - the remote state bucket name created in step 5, not the full `gs://` URL. i.e., `terraform-state-my-project-id`.
- `impersonate_service_account` - the Terraform service account email created in Prerequisites step 2. i.e., `terraform-service-account@$my-project-id.iam.gserviceaccount.com`.

#### Set project-specific [input variable](https://developer.hashicorp.com/terraform/language/values/variables#assigning-values-to-root-module-variablesvalues) values in `terraform/main/vars.auto.tfvars`.
- `project_id` - the target deployment GCP project ID. i.e., `my-project-id`.
- `terraform_service_account` - the Terraform service account email created in Prerequisites step 2.
- `global_lb_domain` - the domain name for the Cloud Load Balancer. If left unset, Terraform will default to using nip.io with the load balancer IP address.
- `cloud_run_invoker_service_account` - the email address of a service account to grant the `roles/run.invoker` role on the Cloud Run services. It can be any service account you can use to generate ID tokens. You can choose to use the Terraform service account as a default.

#### Choose whether to deploy the UI service.
- The T2X gradio app gets deployed as the `t2x-ui` service.
- To remove or not deploy the UI service:
    1. Comment out or remove the `backend_services` object referring to the UI service in the `loadbalancer` module in the main Terraform module: `main/main.tf`.
        - **If the UI service is already deployed and part of the load balancer**: apply the changes in step 1 first (remove the UI service from the LB path matcher) before proceeding, then apply the remaining changes.
    2. Comment out or remove the `cloud_run_ui` module block in the main Terraform module: `main/main.tf`.
    3. Comment out or remove the `docker_image_ui` and `backend_id_ui` output blocks in the main Terraform module: `main/outputs.tf`.
    3. Comment out or remove the `_UI_DOCKER_IMAGE` substitution variable in `cloudbuild.yaml` found in the repo root.
    4. Comment out or remove the `build_ui` and `push_ui` build steps in `cloudbuild.yaml`.
    5. Comment out or remove the `TF_VAR_docker_image_ui` environment variable assignment in the `plan` step of `cloudbuild.yaml`.

## 3. Set environment variables
```sh
export REPO_ROOT=$(git rev-parse --show-toplevel)
export PROJECT='my-project-id'
export REGION='us-central1'
```

## 4. Build & push the docker images and apply the Terraform configuration

- Submit the build from the root directory as the build context.
- [OPTIONAL] Omit the `_RUN_TYPE=apply` substitution to run a plan-only build and review the Terraform changes before applying.
```sh
cd $REPO_ROOT
gcloud builds submit . --config=cloudbuild.yaml --project=$PROJECT --region=$REGION --substitutions="_RUN_TYPE=apply"
```


&nbsp;
# Add an A record to the DNS Managed Zone
([return to top](#talk-to-docs-application-deployment-with-terraform))

- Use the public IP address created by Terraform as the A record in your DNS host.
- **NOTE** A newly-created managed TLS certificate may take anywhere from 10-15 minutes up to 24 hours for the CA to sign after DNS propagates.
- The Certificate [Managed status](https://cloud.google.com/load-balancing/docs/ssl-certificates/troubleshooting#certificate-managed-status) will change from PROVISIONING to ACTIVE when it's ready to use.
- It may take some more time after reaching ACTIVE Managed status before the endpoint responds with success. It may throw an SSLError due to mismatched client and server protocols until changes propagate.


&nbsp;
# Prepare the Discovery Engine Data Store
([return to top](#talk-to-docs-application-deployment-with-terraform))

## 1. Create metadata
- Call the `create-metadata` endpoint on the `t2x-api` service to create a `metadata.jsonl` file in the staging bucket.
- `AUDIENCE` is the Cloud Run Custom Audience configured by the Terraform `main` module.
- `SERVICE_ACCOUNT` is any service account with the `roles/run.invoker` IAM role on the `t2x-api` Cloud Run service.
- The caller must have the `roles/iam.serviceAccountTokenCreator` role on `SERVICE_ACCOUNT`.
- Edit the `data.json` file with the required values for the target project/environment.
    - `branch` - the Agent Builder Data Store branch name. Typically `default_branch`.
    - `bucket_name` - the staging bucket name. i.e., `t2x-staging-my-project-id`.
    - `collection` - the Data Store collection name. Typically `default_collection`.
    - `company_name` - the company name used in the Agent Builder Search Engine.
    - `data_store_id` - the Data Store ID. **Must match the `vais_data_store` value in `llm.yaml`**.
    - `dataset_name` - the dataset name of the document extractions. i.e., `extractions20240715`.
    - `engine_id` - the Search Engine ID. **Must match the `vais_engine_id` value in `llm.yaml`**.
    - `location` - the discoveryengine API location. Must be one of `us`, `eu`, or `global`.
    - `metadata_filename` - the metadata file name.
    - `metadata_folder` - the name of the staging bucket folder to receive the metadata JSONL file.
    - `source_folder` - the name of the staging bucket folder containing document extraction files.

```sh
export PROJECT='my-project-id'
export AUDIENCE='https://demoapp.example.com/t2x-api'
export SERVICE_ACCOUNT="terraform-service-account@${PROJECT}.iam.gserviceaccount.com"
export TOKEN=$(gcloud auth print-identity-token --impersonate-service-account=$SERVICE_ACCOUNT  --audiences=$AUDIENCE)

# Edit the values in data.json - below is an example only
cat << EOF > data.json
{
    "branch": "default_branch",
    "bucket_name": "t2x-staging-$PROJECT",
    "collection": "default_collection",
    "company_name": "Medicare",
    "data_store_id": "data-store-medicare-docs",
    "dataset_name": "extractions20240801",
    "engine_id": "search-engine-medicare-docs",
    "location": "global",
    "metadata_filename": "metadata.jsonl",
    "metadata_folder": "data-store-metadata",
    "source_folder": "source-data"
}
EOF

curl -X POST -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" -d @data.json "${AUDIENCE}/create-metadata"
```

## 2a. [OPTIONAL] Purge documents
- Call the `purge-documents` endpoint on the `t2x-api` service to clear the Discovery Engine data store before importing new documents.
```sh
curl -X POST -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" -d @data.json "${AUDIENCE}/purge-documents"
```

## 2b. Import documents
- Call the `import-documents` endpoint on the `t2x-api` service to import document extractions from the staging bucket to the Discovery Engine data store.
```sh
curl -X POST -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" -d @data.json "${AUDIENCE}/import-documents"
```

- Store the long-running operation name from the `import-documents` response in the environment. (The following is a generic example.)
```sh
export LRO_NAME='projects/{project_number}/locations/{location}/collections/{collection}/dataStores/{data_store_id}/branches/{branch}/operations/import-documents-12345678901234567890'
```

## 3. Verify the operation
- Call the `get-operation` endpoint to check the document import progress.
- The response includes `"done": "true"` when the operation completes.
```sh
export LOCATION='global'
curl -X GET -H "Authorization: Bearer ${TOKEN}" "${AUDIENCE}/get-operation?location=${LOCATION}&operation_name=${LRO_NAME}"
```

&nbsp;
# Configure Identity-Aware Proxy
- Ref - [Enable IAP for Cloud Run](https://cloud.google.com/iap/docs/enabling-cloud-run)
- Ref - [Setting up your OAuth consent screen](https://support.google.com/cloud/answer/10311615)
## Follow these steps
- [Enable Identity-Aware Proxy for a Cloud Run backend service](supplemental_info.md#enable-identity-aware-proxy)


&nbsp;
# REFERENCE INFORMATION


&nbsp;
# Rollbacks
([return to top](#talk-to-docs-application-deployment-with-terraform))

## Option 1: Switch Cloud Run service traffic to a previous revision
### **THIS WILL CHANGE STATE OUTSIDE OF TERRAFORM CONTROL**
- Navigate to the Cloud Run service in the Cloud Console.
- Click the 'Revisions' tab.
- Click 'MANAGE TRAFFIC'.
- Select the target revision and traffic percentage (100% to rollback completely to another revision).
- Click 'SAVE'.

## Option 2: Rollback to a previous Docker image using Terraform
- Identify the rollback target Docker image.
- Pass the target image name and tag to the `docker_image` [input variable](https://developer.hashicorp.com/terraform/language/values/variables#assigning-values-to-root-module-variables) in the `t2x-app/main` root module.
    - Use a `.tfvars` file, the `-var` command line argument, or the `TF_VAR_` [environment variable](https://developer.hashicorp.com/terraform/language/values/variables#environment-variables).
- Apply the Terraform configuration to update the Cloud Run service to the rollback target.

#### Example: select an image by digest or tag from Artifact Registry.
```sh
export TF_VAR_docker_image="us-central1-docker.pkg.dev/my-project-id/talk-to-docs/t2x-api@sha256:4f2092b926b7e9dc30813e819bb86cfa7d664eede575539460b4a68bbd4981e1"
export TF_VAR_docker_image_ui="us-central1-docker.pkg.dev/my-project-id/talk-to-docs/t2x-ui:latest"
```

#### Example: get the deployed image names from terraform output to apply only infrastructure changes.
```sh
export TF_VAR_docker_image=$(tf output -raw docker_image) && export TF_VAR_docker_image_ui=$(tf output -raw docker_image_ui)
```

#### Init, plan, and apply the Terraform configuration.
```sh
cd $REPO_ROOT/terraform/main
tf init
tf plan
tf apply
```


&nbsp;
# Security
([return to top](#talk-to-docs-application-deployment-with-terraform))
### The `t2x-app` Terraform modules follow security best practices for deploying resources in Google Cloud.
- **Least privilege**: Assign the [minimum required permissions](https://cloud.google.com/iam/docs/using-iam-securely#least_privilege) to the T2X service account using these IAM roles:
    - `roles/aiplatform.user`
    - `roles/bigquery.dataEditor`
    - `roles/bigquery.user`
    - `roles/gkemulticloud.telemetryWriter`
    - `roles/storage.objectUser`
- **[Service account impersonation](https://cloud.google.com/iam/docs/service-account-impersonation)**: Use the `google_service_account_access_token` Terraform data source to generate short-lived credentials [instead of service account keys](https://cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys#alternatives).
- **Data encryption**:
    - [Default encryption at rest](https://cloud.google.com/docs/security/encryption/default-encryption) for storage buckets and disk images.
    - [Default encryption in transit](https://cloud.google.com/docs/security/encryption-in-transit#connectivity_to_google_apis_and_services) for GCE connections to Cloud Storage and other Google APIs. 


&nbsp;
# Observability
([return to top](#talk-to-docs-application-deployment-with-terraform))
## Monitor and troubleshoot the T2X application deployment with Cloud Logging and Cloud Monitoring.
- Log filters to view T2X application logs
```
resource.type = "cloud_run_revision"
resource.labels.service_name = "t2x-api"
resource.labels.location = "us-central1"
 severity>=DEFAULT
```


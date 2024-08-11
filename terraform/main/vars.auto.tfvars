region           = "us-central1"
zone             = "us-central1-a"
vpc_network_name = "t2x-network"
vpc_subnet_name  = "t2x-subnet"
vpc_subnet_cidr  = "10.0.0.0/24"
nat_router_name  = "t2x-nat-router"
nat_gateway_name = "t2x-nat-gateway"

# README step Automate Deployments with Cloud Build - step 2:
# Set the domain to a name under control, or leave unset to default to using nip.io with the load balancer IP.
# If set, update the DNS records for the domain to point to the load balancer IP after creating it.

# global_lb_domain = "demoapp.example.com" # example only


# README step Automate Deployments with Cloud Build - step 2:
# Optional service account to use for invoking Cloud Run services.
# The service account email value set here will be granted the roles/run.invoker IAM role directly on the Cloud Run services (not at the project level).
# If not set, no additional service account principals will be granted access to invoke the Cloud Run services.
# and you'll need to use another service account with the appropriate permissions to authenticate calls to Cloud Run.
# For example, the Terraform provisioning service account created in README Prerequsites steps 2 and 3 get granted 
# the Cloud Run Admin role on the project IAM policy, wich is sufficent to invoke authenticated Cloud Run services.
# Ref: https://cloud.google.com/run/docs/authenticating/service-to-service

# cloud_run_invoker_service_account = "run-invoker@my-project-id.iam.gserviceaccount.com" # example only

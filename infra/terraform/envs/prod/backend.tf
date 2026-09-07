# Remote state in GCS. Create the bucket once, out of band:
#   gsutil mb -l us-central1 gs://<project>-tfstate
#   gsutil versioning set on gs://<project>-tfstate
# then `terraform init`. Fill in the bucket below (or pass -backend-config).
terraform {
  backend "gcs" {
    # bucket = "my-project-tfstate"
    prefix = "rag-platform/prod"
  }
}

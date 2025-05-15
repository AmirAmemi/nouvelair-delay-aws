import boto3
import os

bucket_name = "nouvelairdata"
prefix = "raw/"
local_dir = "local_data"

# Ensure the local folder exists
os.makedirs(local_dir, exist_ok=True)

# AWS S3 client (assumes credentials are set via aws configure)
s3 = boto3.client("s3")

# List JSON files in the S3 'raw/' folder
response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

for obj in response.get("Contents", []):
    key = obj["Key"]
    if key.endswith(".json"):
        file_name = key.split("/")[-1]
        local_path = os.path.join(local_dir, file_name)

        if not os.path.exists(local_path):
            print(f"Downloading {file_name}...")
            s3.download_file(bucket_name, key, local_path)
        else:
            print(f"{file_name} already exists — skipped.")

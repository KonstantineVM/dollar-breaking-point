#!/bin/bash

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
BASE_URL="https://www.sec.gov/files/dera/data/form-n-port-data-sets"

# Accept arguments from NPORT_Master.do
BASE_DIR=$1
EMAIL=$2
QUARTERS=$3
ZIP_DIR="$BASE_DIR/nport_zips"

echo "Using BASE_DIR: $BASE_DIR"
echo "Using EMAIL: $EMAIL"
echo "Processing quarters: $QUARTERS"

mkdir -p "$ZIP_DIR"

# ---------------------------------------------------------
# Function: Download and unzip SEC N-PORT files
# ---------------------------------------------------------
download_and_unzip() {
  local quarter=$1
  local zip_name="${quarter}_nport.zip"
  local zip_path="$ZIP_DIR/$zip_name"
  local unzip_dir="$BASE_DIR/${quarter}"

  # Skip if already unzipped
  if [[ -d "$unzip_dir" && -n "$(ls -A "$unzip_dir" 2>/dev/null)" ]]; then
    echo "Already unzipped: $quarter"
    return
  fi

  mkdir -p "$unzip_dir"

  echo "Downloading $zip_name ..."
  curl -fL \
    -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 ($EMAIL)" \
    -H "From: $EMAIL" \
    "$BASE_URL/$zip_name" \
    -o "$zip_path"

  if [[ $? -ne 0 || $(stat -f%z "$zip_path") -lt 10000 ]]; then
    echo "Failed to download or too small: $quarter"
    rm -f "$zip_path"
    rm -rf "$unzip_dir"
    return
  fi

  echo "Unzipping to $unzip_dir ..."
  unzip -q "$zip_path" -d "$unzip_dir"

  if [[ $? -eq 0 ]]; then
    echo "Successfully unzipped $quarter."
  else
    echo "Unzipping failed: $quarter"
    rm -rf "$unzip_dir"
  fi
}

# ---------------------------------------------------------
# Execute main loop: process each quarter
# ---------------------------------------------------------
for quarter in $QUARTERS; do
  download_and_unzip "$quarter"
done

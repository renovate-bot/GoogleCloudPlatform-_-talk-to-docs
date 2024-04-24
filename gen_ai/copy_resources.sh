#!/bin/bash

# Create resource directory and copy resource files from GCS.

sudo mkdir -p /mnt/resources/
sudo chmod 777 /mnt/resources/
rm -rf /mnt/resources/uhg/
mkdir -p /mnt/resources/uhg
mkdir -p /mnt/resources/uhg/main_folder/
gsutil -m cp -r "gs://uhg_data/extractions_20240417/*" /mnt/resources/uhg/main_folder/
# Extraction Pipeline

## Overview
The extraction pipeline can work in two modes: *Batch* or *Continuous*. In Batch mode all the files in given directory or gs bucket are processed at once. 
In Continuous mode the pipeline processes files in given bucket and then checks the bucket every ten minutes if new files were added. If so, the files are processed and copied into given output bucket.
There are four parameters you need to pass to run the pipeline:
- **mode** - it can be either `batch` or `continuous` (Required argument)
- **input_dir** - input directory or gs bucket directory where input files are located (Required argument)
- **output_dir** - output directory in local system where to extract documents (Eg. /mnt/resources/dataset/main_folder) (Optional argument)
- **gs_bucket** - GCS bucket where to copy extracted document chunks


## Batch mode
Batch mode can process both local directories and GCS buckets. And the result can be uploaded to the GCS bucket automatically if necessary. Arguments you need to pass are `mode` and `input_dir`. If no `output_dir` is provided, default value is "output_dir" which is created automatically. Input directory can be local directory or GCS bucket directory.

Example:  

*Local directory*
```sh
python gen_ai/extraction_pipeline/processor.py batch -i /mnt/resources/dataset/main_folder -o output_dir
```

*Bucket input and output*
```sh
python gen_ai/extraction_pipeline/processor.py batch -i gs://dataset_raw_data/20240417_docx -gs gs://dataset_clean_data
```

*Bucket input local default output*
```sh
python gen_ai/extraction_pipeline/processor.py batch -i gs://dataset_raw_data/20240417_docx
```


## Continuous mode
Continuous mode processes GCS buckets only, it first processes all the files in the input directory. Afterwards it checks the bucket every 10 minutes if new files were added. If so, it processes new files and transfer them to the destination GCS bucket. Arguments you need to pass are `mode`, `input_dir` (bucket address) and `gs_bucket` where processed files will be uploaded.

Example:  

```sh
python gen_ai/extraction_pipeline/processor.py continuous -i gs://dataset_raw_data/20240417_docx -gs gs://dataset_clean_data
```

## Config file

The configuration file of which type of extraction to use for each file type is in `config.yaml`, inside *'extraction_pipeline'* directory. For each type of file there are two parameters: `Extraction` and `Chunking`. If no value is given in config file, "default" is used as the value.
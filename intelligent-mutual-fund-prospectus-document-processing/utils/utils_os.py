import os
import boto3
import json
import glob, shutil
from typing import List


# Function to read a JSONL file and return its contents
def read_jsonl(path):
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            data.append(json.loads(line))
    return data


# Function to write a list of dictionaries to a JSONL file
def write_jsonl(path, jl: List[dict]):
    os.makedirs(os.path.dirname(os.path.realpath(path)), exist_ok=True)
    with open(path, "w") as f:
        for j in jl:
            json.dump(j, f, ensure_ascii=False)
            f.write("\n")


# Function to write a dictionary to a JSON file
def write_json(path, j):
    os.makedirs(os.path.dirname(os.path.realpath(path)), exist_ok=True)
    with open(path, "w") as f:
        json.dump(j, f, ensure_ascii=False)


# Function to read a JSON file and return its content
def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.loads(f.read())


# Function to read the content of a text file
def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# Function to write text to a file, creating directories if they don't exist
def write_text(path, text):
    os.makedirs(os.path.dirname(os.path.realpath(path)), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


# Function to copy files matching a glob pattern to a destination directory
def copy_glob(prefix, dest_dir):
    for file in glob.iglob(prefix):
        shutil.copy2(file, dest_dir)


# Function to count the number of files in a directory with a given extension
def dir_size(directory, ext):
    return sum(1 for x in os.listdir(directory) if x.endswith(ext))


# Function to iterate over files in an S3 bucket, optionally filtering by extension
def iterate_bucket(s3_path, extension=None):
    assert s3_path.startswith("s3")

    bucket_name = s3_path.split("/")[2]
    directory = "/".join(s3_path.split("/")[3:])

    s3_bucket = boto3.resource("s3").Bucket(bucket_name)

    for file in s3_bucket.objects.filter(Prefix=directory):
        if extension is not None and not file.key.endswith(extension):
            continue
        yield file.key


# Function to upload a file to S3, with optional verbose logging
def s3_upload(local_file, s3_dst, verbose=False):
    assert s3_dst.startswith("s3")

    bucket = s3_dst.split("/")[2]
    s3_dir = "/".join(s3_dst.split("/")[3:])

    if s3_dir[-1] == "/":
        s3_dir = s3_dir + local_file.split("/")[-1]

    if verbose:
        print(f"s3_upload {bucket}/{s3_dir}")

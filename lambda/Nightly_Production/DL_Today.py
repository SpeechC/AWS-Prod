# -*- coding: utf-8 -*-
import boto3
import json
from datetime import datetime

sagemaker_client = boto3.client('sagemaker')

def lambda_handler(event, context):
    """
    Lambda function to start a SageMaker processing job.
    CloudWatch will trigger the next Lambda (Production_MP3_WAV) when it completes.
    """
    try:
        # Generate a unique job name
        job_name = f"processing-job-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
        print(f"🚀 Starting SageMaker Processing Job: {job_name}")

        # Create the processing job
        response = sagemaker_client.create_processing_job(
            ProcessingJobName=job_name,
            ProcessingResources={
                "ClusterConfig": {
                    "InstanceType": "ml.m5.large",
                    "InstanceCount": 1,
                    "VolumeSizeInGB": 20
                }
            },
            AppSpecification={
                "ImageUri": "179311716247.dkr.ecr.us-east-1.amazonaws.com/sca_parallel_multinode_wtorch:latest",
                "ContainerEntrypoint": ["python", "/opt/ml/processing/input/code/DL_Today_Feb25.py"]
            },
            RoleArn="arn:aws:iam::179311716247:role/SCA_Lambda",
            ProcessingInputs=[
                {
                    "InputName": "script",
                    "S3Input": {
                        "S3Uri": "s3://speechcraft/SP/scripts/DL_Today_Feb25.py",
                        "LocalPath": "/opt/ml/processing/input/code",
                        "S3DataType": "S3Prefix",
                        "S3InputMode": "File"
                    }
                }
            ],
            ProcessingOutputConfig={
                "Outputs": [
                    {
                        "OutputName": "output-data",
                        "S3Output": {
                            "S3Uri": "s3://speechcraft/SP/Production/MP3s/",
                            "LocalPath": "/opt/ml/processing/output",
                            "S3UploadMode": "EndOfJob"
                        }
                    }
                ]
            },
            StoppingCondition={"MaxRuntimeInSeconds": 12600}  # 3.5-hour limit
        )

        print(f"✅ SageMaker Processing Job {job_name} started successfully.")

        return {
            "statusCode": 200,
            "body": f"SageMaker Processing Job {job_name} started successfully!"
        }

    except Exception as e:
        print(f"❌ Error starting SageMaker Processing Job: {e}")

        return {
            "statusCode": 500,
            "body": f"Error: {str(e)}"
        }


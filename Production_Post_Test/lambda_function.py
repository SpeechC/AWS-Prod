# -*- coding: utf-8 -*-
import boto3
import json
from datetime import datetime
from botocore.config import Config

# Create a default config
AWS_REGION = "us-east-1"
aws_config = Config(region_name=AWS_REGION)

# AWS Clients
eventbridge_client = boto3.client('events', config=aws_config)
sagemaker_client = boto3.client('sagemaker', config=aws_config)

def emit_event(detail_type, detail):
    """
    Emit a custom event to EventBridge.
    """
    try:
        eventbridge_client.put_events(
            Entries=[
                {
                    'Source': 'production.pipeline',
                    'DetailType': detail_type,
                    'Detail': json.dumps(detail),
                    'EventBusName': 'default'
                }
            ]
        )
        print(f"✅ Event emitted: {detail_type} - {detail}")
    except Exception as e:
        print(f"❌ Failed to emit event: {e}")

def lambda_handler(event, context):
    """
    Lambda function to start a SageMaker processing job.
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
                    "InstanceType": "ml.r5.4xlarge",
                    "InstanceCount": 1,
                    "VolumeSizeInGB": 50
                }
            },
            AppSpecification={
                "ImageUri": "179311716247.dkr.ecr.us-east-1.amazonaws.com/sca_parallel_multinode_wtorch:latest",
                "ContainerEntrypoint": ["python", "/opt/ml/processing/input/code/post.py"]
            },
            RoleArn="arn:aws:iam::179311716247:role/SCA_Lambda",
            ProcessingInputs=[
                {
                    "InputName": "script",
                    "S3Input": {
                        "S3Uri": "s3://speechcraft/SP/scripts/post.py",
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
                            "S3Uri": "s3://speechcraft/SP/Production/Output/Post/",
                            "LocalPath": "/opt/ml/processing/output",
                            "S3UploadMode": "Continuous"
                        }
                    }
                ]
            },
            StoppingCondition={"MaxRuntimeInSeconds": 14400}  # 4-hour limit
        )

        print(f"✅ SageMaker Processing Job {job_name} started successfully.")

        # Emit event so EventBridge can trigger the next process
        emit_event(
            detail_type="SageMakerJobStarted",
            detail={"job_name": job_name, "status": "Started"}
        )

        return {
            "statusCode": 200,
            "body": f"SageMaker Processing Job {job_name} started successfully!"
        }

    except Exception as e:
        print(f"❌ Error starting SageMaker Processing Job: {e}")

        emit_event(
            detail_type="SageMakerJobFailed",
            detail={"status": "Failure", "error": str(e)}
        )

        return {
            "statusCode": 500,
            "body": f"Error: {str(e)}"
        }

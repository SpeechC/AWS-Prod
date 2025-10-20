import boto3
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    AWS Lambda function to move all files from MP3/ and WAV/ to MP3_Final/ and WAV_Final/ in an S3 bucket,
    and delete the original files.
    """
    try:
        # Specify the bucket name
        bucket_name = "speechcraft"
        
        # Prefixes for source and destination directories
        source_prefixes = ["SP/Production/MP3s/", "SP/Production/WAV/","SP/Production/Output/Sentence/"]
        final_prefixes = ["SP/Production/MP3s_Final/", "SP/Production/WAV_Final/","SP/Production/Output/Sentence_Final/"]
        
        s3_client = boto3.client("s3")
        
        for source_prefix, final_prefix in zip(source_prefixes, final_prefixes):
            logger.info(f"Processing files from {source_prefix} to {final_prefix}")
            
            # List objects in the source prefix
            response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=source_prefix)
            
            if "Contents" not in response:
                logger.info(f"No files found in {source_prefix}")
                continue
            
            # Process each file
            for obj in response["Contents"]:
                source_key = obj["Key"]
                # Skip the directory placeholder keys (if any)
                if source_key.endswith("/"):
                    continue
                
                final_key = source_key.replace(source_prefix, final_prefix, 1)
                
                # Copy file to the final location
                logger.info(f"Copying {source_key} to {final_key}")
                s3_client.copy_object(
                    Bucket=bucket_name,
                    CopySource={"Bucket": bucket_name, "Key": source_key},
                    Key=final_key
                )
                
                # Delete the original file
                logger.info(f"Deleting {source_key}")
                s3_client.delete_object(Bucket=bucket_name, Key=source_key)
        
        return {
            "statusCode": 200,
            "body": "Files moved and deleted successfully."
        }
    
    except Exception as e:
        logger.error(f"Error in Lambda handler: {e}")
        return {
            "statusCode": 500,
            "body": f"Error processing files: {e}"
        }


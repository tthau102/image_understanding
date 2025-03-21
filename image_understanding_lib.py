import boto3
from io import BytesIO
import imghdr
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_bytesio_from_bytes(image_bytes):
    """Convert binary image data to BytesIO object."""
    return BytesIO(image_bytes)

def get_bytes_from_file(file_path):
    """Read binary data from image file."""
    with open(file_path, "rb") as image_file:
        return image_file.read()

def detect_image_format(image_bytes):
    """Detect image format from binary data."""
    format = imghdr.what(None, h=image_bytes)
    return format or "jpeg"  # Default to jpeg if detection fails

def get_response_from_model(prompt_content, image_bytes, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", 
                           temperature=0.0, top_p=0.9, max_tokens=2000):
    """Process image and text input using Bedrock model."""
    try:
        session = boto3.Session()
        bedrock = session.client(service_name='bedrock-runtime')
        
        # Detect image format
        image_format = detect_image_format(image_bytes)
        
        # Prepare message with image
        image_message = {
            "role": "user",
            "content": [
                {"text": "Image 1:"},
                {
                    "image": {
                        "format": image_format,
                        "source": {
                            "bytes": image_bytes
                        }
                    }
                },
                {"text": prompt_content}
            ],
        }
        
        # Call model
        response = bedrock.converse(
            modelId=model_id,
            messages=[image_message],
            inferenceConfig={
                "maxTokens": max_tokens,
                "temperature": temperature,
                "topP": top_p
            },
        )
        
        return response['output']['message']['content'][0]['text']
    except Exception as e:
        logger.error(f"Error processing image with model: {str(e)}")
        raise

def get_text_response(prompt_content, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", 
                     temperature=0.0, top_p=0.9, max_tokens=2000):
    """Process text-only input using Bedrock model."""
    try:
        session = boto3.Session()
        bedrock = session.client(service_name='bedrock-runtime')
        
        # Prepare text message
        message = {
            "role": "user",
            "content": [
                {"text": prompt_content}
            ],
        }
        
        # Call model
        response = bedrock.converse(
            modelId=model_id,
            messages=[message],
            inferenceConfig={
                "maxTokens": max_tokens,
                "temperature": temperature,
                "topP": top_p
            },
        )
        
        return response['output']['message']['content'][0]['text']
    except Exception as e:
        logger.error(f"Error processing text with model: {str(e)}")
        raise
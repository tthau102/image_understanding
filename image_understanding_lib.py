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

def get_kb_response(prompt_content, kb_id, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", 
                  temperature=0.0, top_p=0.9, max_tokens=2000, retrieval_config=None):
    try:
        session = boto3.Session()
        bedrock_agent_runtime = session.client(service_name='bedrock-agent-runtime')
        
        # Chuẩn bị input
        input_data = {
            "text": prompt_content
        }
        
        # Cấu hình KB
        kb_config = {
            "knowledgeBaseId": kb_id,
            "modelArn": model_id,
            "generationConfiguration": {
                "inferenceConfig": {
                    "textInferenceConfig": {
                        "temperature": temperature,
                        "topP": top_p,
                        "maxTokens": max_tokens
                    }
                }
            }
        }
        
        # Thêm retrieval config nếu có
        if retrieval_config:
            kb_config["retrievalConfiguration"] = {
                "vectorSearchConfiguration": retrieval_config
            }
        
        # Gọi API đúng
        response = bedrock_agent_runtime.retrieve_and_generate(
            input=input_data,
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": kb_config
            }
        )
        
        return response['output']['text'], response.get('citations', [])
    except Exception as e:
        logger.error(f"Error processing KB request: {str(e)}")
        raise

def get_kb_response_with_image(prompt_content, kb_id, image_bytes, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", 
                             temperature=0.0, top_p=0.9, max_tokens=2000, retrieval_config=None):
    """
    Process image and text input using Bedrock Knowledge Base.
    Note: Since Knowledge Base does not directly support image input,
    we first analyze the image with the model, then use that analysis to query the KB.
    """
    try:
        session = boto3.Session()
        bedrock = session.client(service_name='bedrock-runtime')
        
        # Step 1: Analyze image first
        image_format = detect_image_format(image_bytes)
        
        image_message = {
            "role": "user",
            "content": [
                {"text": "Describe this image in detail:"},
                {
                    "image": {
                        "format": image_format,
                        "source": {
                            "bytes": image_bytes
                        }
                    }
                }
            ],
        }
        
        image_analysis_response = bedrock.converse(
            modelId=model_id,
            messages=[image_message],
            inferenceConfig={
                "maxTokens": 1000,
                "temperature": 0.0,
                "topP": 0.9
            },
        )
        
        image_description = image_analysis_response['output']['message']['content'][0]['text']
        
        # Step 2: Create combined query with image description and original prompt
        combined_prompt = f"""
Image description: {image_description}

User query: {prompt_content}

Please answer the user query using the image description and any relevant information from the knowledge base.
        """.strip()
        
        # Step 3: Query Knowledge Base with combined prompt
        input_data = {
            "text": combined_prompt
        }
        
        kb_config = {
            "knowledgeBaseId": kb_id,
            "modelArn": model_id,
            "generationConfiguration": {
                "inferenceConfig": {
                    "textInferenceConfig": {
                        "temperature": temperature,
                        "topP": top_p,
                        "maxTokens": max_tokens
                    }
                }
            }
        }
        
        if retrieval_config:
            kb_config["retrievalConfiguration"] = {
                "vectorSearchConfiguration": retrieval_config
            }
        
        kb_response = bedrock.retrieve_and_generate(
            input=input_data,
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": kb_config
            }
        )
        
        return kb_response['output']['text'], kb_response.get('citations', [])
    except Exception as e:
        logger.error(f"Error processing KB request with image: {str(e)}")
        raise
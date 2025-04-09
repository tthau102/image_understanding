import boto3
from io import BytesIO
import imghdr
import logging
import json
import base64

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

def process_input(prompt_content, model_id, system_prompt=None, image_bytes=None, 
                 temperature=0.0, top_p=0.9, max_tokens=2000):
    """
    Xử lý input (text và/hoặc image) với model Bedrock.
    
    Args:
        prompt_content: Nội dung prompt từ user
        model_id: ID của model Bedrock
        system_prompt: System prompt (optional)
        image_bytes: Binary image data (optional)
        temperature, top_p, max_tokens: Parameters cho model
    
    Returns:
        Phản hồi từ model
    """
    try:
        session = boto3.Session()
        bedrock = session.client(service_name='bedrock-runtime')
        
        # Xác định loại model
        is_anthropic_model = "anthropic" in model_id.lower()
        
        if is_anthropic_model:
            # Cấu trúc cho Anthropic Claude models - sử dụng invoke_model
            image_format = detect_image_format(image_bytes) if image_bytes else None
            
            if image_bytes:
                # Prepare message with image
                content = [
                    {"type": "text", "text": "Image 1:"},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": f"image/{image_format}",
                            "data": base64.b64encode(image_bytes).decode('utf-8')
                        }
                    },
                    {"type": "text", "text": prompt_content}
                ]
            else:
                # Text only content
                content = prompt_content
            
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            # Call invoke_model API
            response = bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps(payload)
            )
            response_body = json.loads(response['body'].read().decode('utf-8'))
            return response_body['content'][0]['text']
            
        else:
            # Cấu trúc cho Amazon models (Nova) - sử dụng converse API
            if image_bytes:
                # Prepare message with image
                image_format = detect_image_format(image_bytes)
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
                        {"text": prompt_content if not system_prompt else f"System instructions: {system_prompt}\n\nUser: {prompt_content}"}
                    ],
                }
            else:
                # Prepare text message
                message = {
                    "role": "user",
                    "content": [
                        {"text": prompt_content if not system_prompt else f"System instructions: {system_prompt}\n\nUser: {prompt_content}"}
                    ],
                }
            
            # Call converse API
            response = bedrock.converse(
                modelId=model_id,
                messages=[image_message if image_bytes else message],
                inferenceConfig={
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                    "topP": top_p
                },
            )
            
            return response['output']['message']['content'][0]['text']
    
    except Exception as e:
        logger.error(f"Error processing input: {str(e)}")
        raise

# Xử lý Knowledge Base
def process_kb_input(prompt_content, kb_id, model_id, image_bytes=None, 
                   system_prompt=None, temperature=0.0, top_p=0.9, max_tokens=2000, 
                   retrieval_config=None, num_results=5):
    """
    Xử lý input với Bedrock Knowledge Base.
    """
    try:
        session = boto3.Session()
        bedrock_agent_runtime = session.client(service_name='bedrock-agent-runtime')
        
        # Xử lý image nếu có
        if image_bytes:
            # Phân tích hình ảnh bằng model thông thường
            bedrock = session.client(service_name='bedrock-runtime')
            image_format = detect_image_format(image_bytes)
            
            # Tạo image message
            if "anthropic" in model_id.lower():
                # Anthropic models
                payload = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "temperature": 0.0,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Describe this image in detail:"},
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": f"image/{image_format}",
                                        "data": base64.b64encode(image_bytes).decode('utf-8')
                                    }
                                }
                            ]
                        }
                    ]
                }
                
                response = bedrock.invoke_model(
                    modelId=model_id,
                    body=json.dumps(payload)
                )
                response_body = json.loads(response['body'].read().decode('utf-8'))
                image_description = response_body['content'][0]['text']
            else:
                # Amazon models
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
                
                response = bedrock.converse(
                    modelId=model_id,
                    messages=[image_message],
                    inferenceConfig={
                        "maxTokens": 1000,
                        "temperature": 0.0,
                        "topP": 0.9
                    },
                )
                
                image_description = response['output']['message']['content'][0]['text']
            
            # Kết hợp prompt với mô tả hình ảnh
            combined_prompt = f"""
Image description: {image_description}

User query: {prompt_content}

Please answer the user query using the image description and any relevant information from the knowledge base.
            """.strip()
            
            # Cập nhật prompt_content
            prompt_content = combined_prompt
        
        # Thêm system prompt nếu có
        if system_prompt:
            prompt_content = f"System: {system_prompt}\n\n{prompt_content}"
        
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
        retrieval_config = retrieval_config or {"numberOfResults": num_results}
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

# Legacy wrapper functions for backwards compatibility
def get_response_from_model(prompt_content, image_bytes, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", 
                           temperature=0.0, top_p=0.9, max_tokens=2000):
    """Process image and text input using Bedrock model (Legacy wrapper)."""
    return process_input(prompt_content, model_id, image_bytes=image_bytes,
                        temperature=temperature, top_p=top_p, max_tokens=max_tokens)

def get_response_from_model_with_system(prompt_content, image_bytes, system_prompt, 
                                       model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", 
                                       temperature=0.0, top_p=0.9, max_tokens=2000):
    """Process image and text input with system prompt (Legacy wrapper)."""
    return process_input(prompt_content, model_id, system_prompt=system_prompt, 
                        image_bytes=image_bytes, temperature=temperature, 
                        top_p=top_p, max_tokens=max_tokens)

def get_text_response(prompt_content, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", 
                     temperature=0.0, top_p=0.9, max_tokens=2000):
    """Process text-only input (Legacy wrapper)."""
    return process_input(prompt_content, model_id, temperature=temperature, 
                        top_p=top_p, max_tokens=max_tokens)

def get_text_response_with_system(prompt_content, system_prompt, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", 
                                temperature=0.0, top_p=0.9, max_tokens=2000):
    """Process text input with system prompt (Legacy wrapper)."""
    return process_input(prompt_content, model_id, system_prompt=system_prompt,
                        temperature=temperature, top_p=top_p, max_tokens=max_tokens)

def get_kb_response(prompt_content, kb_id, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", 
                  temperature=0.0, top_p=0.9, max_tokens=2000, retrieval_config=None):
    """Process text input with Knowledge Base (Legacy wrapper)."""
    return process_kb_input(prompt_content, kb_id, model_id, temperature=temperature, 
                          top_p=top_p, max_tokens=max_tokens, retrieval_config=retrieval_config)

def get_kb_response_with_image(prompt_content, kb_id, image_bytes, model_id, 
                              temperature=0.0, top_p=0.9, max_tokens=2000, retrieval_config=None):
    """Process image and text input with Knowledge Base (Legacy wrapper)."""
    return process_kb_input(prompt_content, kb_id, model_id, image_bytes=image_bytes,
                          temperature=temperature, top_p=top_p, max_tokens=max_tokens, 
                          retrieval_config=retrieval_config)
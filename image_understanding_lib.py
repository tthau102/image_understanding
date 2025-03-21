import boto3
from io import BytesIO
import imghdr
import logging
import json

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_bytesio_from_bytes(image_bytes):
    """Chuyển binary image data thành BytesIO object."""
    return BytesIO(image_bytes)

def get_bytes_from_file(file_path):
    """Đọc binary data từ file."""
    with open(file_path, "rb") as image_file:
        return image_file.read()

def detect_image_format(image_bytes):
    """Phát hiện định dạng hình ảnh từ binary data."""
    format = imghdr.what(None, h=image_bytes)
    return format or "jpeg"  # Default là jpeg nếu không phát hiện được

def get_response_from_model(prompt_content, image_bytes, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", 
                           temperature=0.0, top_p=0.9, max_tokens=2000):
    """Xử lý image và text input bằng Bedrock model."""
    try:
        session = boto3.Session()
        bedrock = session.client(service_name='bedrock-runtime')
        
        # Phát hiện định dạng hình ảnh
        image_format = detect_image_format(image_bytes)
        
        # Chuẩn bị message có hình ảnh
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
        
        # Gọi model
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
    """Xử lý text-only input bằng Bedrock model."""
    try:
        session = boto3.Session()
        bedrock = session.client(service_name='bedrock-runtime')
        
        # Chuẩn bị text message
        message = {
            "role": "user",
            "content": [
                {"text": prompt_content}
            ],
        }
        
        # Gọi model
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

def analyze_image(image_bytes, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0"):
    """Phân tích hình ảnh và trả về mô tả."""
    try:
        session = boto3.Session()
        bedrock = session.client(service_name='bedrock-runtime')
        
        # Phát hiện định dạng hình ảnh
        image_format = detect_image_format(image_bytes)
        
        # Chuẩn bị message để phân tích hình ảnh
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
        
        # Gọi model
        response = bedrock.converse(
            modelId=model_id,
            messages=[image_message],
            inferenceConfig={
                "maxTokens": 1000,
                "temperature": 0.0,
                "topP": 0.9
            },
        )
        
        return response['output']['message']['content'][0]['text']
    except Exception as e:
        logger.error(f"Error analyzing image: {str(e)}")
        raise

def query_knowledge_base(prompt_content, kb_id, model_id, temperature=0.0, top_p=0.9, max_tokens=2000, retrieval_config=None):
    try:
        session = boto3.Session()
        bedrock_agent_runtime = session.client(service_name='bedrock-agent-runtime')
        region = session.region_name
        account_id = session.client('sts').get_caller_identity().get('Account')

        
        # Chuyển đổi model_id thành ARN
        if not model_id.startswith('arn:'):
            model_arn = f"arn:aws:bedrock:{region}:{account_id}:foundation-model/{model_id}"
        else:
            # Kiểm tra format ARN
            parts = model_id.split(':')
            if len(parts) >= 7 and parts[5] == '':
                # Thêm account ID vào ARN khi thiếu
                model_arn = f"arn:aws:bedrock:{parts[3]}:{account_id}:foundation-model/{parts[6]}"
            else:
                model_arn = model_id
            
        # Định nghĩa input_data (thiếu dòng này)
        input_data = {
            "text": prompt_content
        }
        
        # Cấu hình Knowledge Base
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
        
        # Log cấu hình
        logger.info(f"KB Config: {json.dumps(kb_config, default=str)}")
        
        # Gọi API
        response = bedrock_agent_runtime.retrieve_and_generate(
            input=input_data,
            retrieveAndGenerateConfiguration={
                "type": "KNOWLEDGE_BASE",
                "knowledgeBaseConfiguration": kb_config
            }
        )
        
        return response['output']['text'], response.get('citations', [])
    except Exception as e:
        logger.error(f"Error querying knowledge base: {str(e)}")
        raise
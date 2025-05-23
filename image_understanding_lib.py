import boto3
from io import BytesIO
import imghdr
import logging
import json
import base64
from PIL import Image, ExifTags
import io

import psycopg2
from typing import List, Tuple
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants từ .env
RAG_EMBEDDING_REGION = os.getenv("RAG_EMBEDDING_REGION")
RAG_TABLE_NAME = os.getenv("RAG_TABLE_NAME")
RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL")

# Update function get_image_embedding
def get_image_embedding(image_bytes, region=None):
    """Generate embedding for image using Titan"""
    # Sử dụng region từ env nếu không truyền vào
    if region is None:
        region = RAG_EMBEDDING_REGION
        
    client = boto3.client("bedrock-runtime", region_name=region)
    
    base_image = base64.b64encode(image_bytes).decode("utf-8")
    response = client.invoke_model(
        body=json.dumps({
            "inputImage": base_image,
            "embeddingConfig": {"outputEmbeddingLength": 1024}
        }),
        modelId=RAG_EMBEDDING_MODEL,
        accept="application/json",
        contentType="application/json"
    )
    
    response_body = json.loads(response.get("body").read())
    return response_body.get("embedding"), base_image

# Update function query_similar_images
def query_similar_images(embedding, db_config, limit=3):
    """Query PostgreSQL for similar images"""
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    table_name = RAG_TABLE_NAME
    query = f"""
        SELECT description, base64, inventory, 
               embedding <=> %s::vector AS distance
        FROM {table_name}
        ORDER BY distance
        LIMIT %s;
    """
    
    cursor.execute(query, (list(embedding), limit))
    results = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return results


# Thêm hàm xác định region từ model ID
def get_region_from_model_id(model_id):
    """Xác định region dựa vào prefix của model ID"""
    if model_id.startswith("us."):
        return "us-east-1"  # Region US cho US models
    elif model_id.startswith("apac."):
        return "ap-southeast-1"  # Region Singapore cho APAC models
    else:
        # Default region
        return "ap-southeast-1"

# Default parameters cho các model
# Nova models
NOVA_DEFAULT_TEMPERATURE = 0.1
NOVA_DEFAULT_TOP_P = 0.9
NOVA_DEFAULT_TOP_K = 128  
NOVA_DEFAULT_MAX_TOKENS = 2000

# Claude models
CLAUDE_DEFAULT_TEMPERATURE = 0.1
CLAUDE_DEFAULT_TOP_P = 0.999
CLAUDE_DEFAULT_TOP_K = 500
CLAUDE_DEFAULT_MAX_TOKENS = 2000

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# def get_bytesio_from_bytes(image_bytes):
#     """Convert binary image data to BytesIO object."""
#     return BytesIO(image_bytes)

def get_bytesio_from_bytes(image_bytes):
    """Convert binary image data to BytesIO object with correct orientation."""
    image = Image.open(BytesIO(image_bytes))
    
    # Xử lý metadata EXIF để xoay ảnh đúng hướng
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break
                
        exif = dict(image._getexif().items())
        
        if exif[orientation] == 3:
            image = image.rotate(180, expand=True)
        elif exif[orientation] == 6:
            image = image.rotate(270, expand=True)
        elif exif[orientation] == 8:
            image = image.rotate(90, expand=True)
    except (AttributeError, KeyError, IndexError):
        # Ảnh không có metadata EXIF hoặc không cần xoay
        pass
    
    # Chuyển ảnh đã xoay về BytesIO
    output = BytesIO()
    image.save(output, format=image.format if image.format else 'JPEG')
    output.seek(0)
    
    return output

def get_bytes_from_file(file_path):
    """Read binary data from image file."""
    with open(file_path, "rb") as image_file:
        return image_file.read()

def detect_image_format(image_bytes):
    """Detect image format from binary data."""
    format = imghdr.what(None, h=image_bytes)
    return format or "jpeg"  # Default to jpeg if detection fails

def process_conversation(messages, model_id, system_prompt=None, 
                        temperature=None, top_p=None, top_k=None, max_tokens=None):
    """
    Xử lý hội thoại với nhiều message với format giống API
    
    Args:
        messages: List of message objects with role and content array
        model_id: ID của model Bedrock
        system_prompt: System prompt (optional)
        temperature, top_p, top_k, max_tokens: Parameters cho model (nếu None sẽ dùng giá trị mặc định)
    
    Returns:
        Phản hồi từ model
    """
    try:
        # Validate messages first
        if not messages or len(messages) == 0:
            raise ValueError("Không có messages để xử lý")
        
        # Log before processing
        logger.info(f"Processing with model: {model_id}")
        logger.info(f"Number of messages: {len(messages)}")
        
        # Xác định region từ model_id
        region = get_region_from_model_id(model_id)
        logger.info(f"Using region: {region} for model {model_id}")
        
        # Tạo session và client với region tương ứng
        session = boto3.Session(region_name=region)
        bedrock = session.client(service_name='bedrock-runtime')
        
        # Xác định loại model
        is_anthropic_model = "anthropic" in model_id.lower()
                
        # Sử dụng giá trị mặc định dựa vào loại model nếu không có giá trị truyền vào
        if temperature is None:
            temperature = CLAUDE_DEFAULT_TEMPERATURE if is_anthropic_model else NOVA_DEFAULT_TEMPERATURE
        
        if top_p is None:
            top_p = CLAUDE_DEFAULT_TOP_P if is_anthropic_model else NOVA_DEFAULT_TOP_P
        
        if top_k is None:
            top_k = CLAUDE_DEFAULT_TOP_K if is_anthropic_model else NOVA_DEFAULT_TOP_K
            
        if max_tokens is None:
            max_tokens = CLAUDE_DEFAULT_MAX_TOKENS if is_anthropic_model else NOVA_DEFAULT_MAX_TOKENS
        
        if is_anthropic_model:
            # Cấu trúc cho Anthropic Claude models
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "messages": messages
            }
            
            # Thêm system prompt nếu có
            if system_prompt and system_prompt.strip():
                payload["system"] = system_prompt
            
            # Log details for debugging
            logger.info(f"Claude payload structure - messages count: {len(payload['messages'])}")
            for msg in payload['messages']:
                logger.info(f"Message role: {msg['role']}, content items: {len(msg['content'])}")
            
            # Call invoke_model API 
            response = bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps(payload)
            )

            # Parse response
            response_body = json.loads(response['body'].read().decode('utf-8'))
            #-----------------------------------------------
            logger.info(f"Messages['content']['type']")
            for i in range(len(payload['messages'])):
                for j in range(len(payload['messages'][i]['content'])):
                    print(payload['messages'][i]['content'][j]['type'])
            #-----------------------------------------------
            logger.info(f"Claude response usage: {response_body.get('usage', {})}")
            print('*********************************************************************************************************************')

            # Validate và extract response text
            if 'content' in response_body and len(response_body['content']) > 0:
                if 'text' in response_body['content'][0]:
                    return response_body['content'][0]['text']
                else:
                    logger.warning("Unexpected Claude response format: missing 'text' in content")
                    return str(response_body['content'][0])
            else:
                logger.warning("Unexpected Claude response format: missing or empty 'content'")
                return str(response_body)
            
        else:
            # Cấu trúc cho Amazon Nova models
            # Chuẩn bị messages - cần xử lý System Prompt đặc biệt cho Nova
            nova_messages = []
            
            # Xử lý System Prompt cho Nova - thêm vào nội dung của message đầu tiên
            for i, msg in enumerate(messages):
                msg_copy = msg.copy()
                
                # Nếu là message đầu tiên của user và có system prompt, thêm vào đầu content
                if i == 0 and msg['role'] == 'user' and system_prompt and system_prompt.strip():
                    if 'content' not in msg_copy or not isinstance(msg_copy['content'], list):
                        msg_copy['content'] = []
                    
                    # Thêm System Prompt vào đầu content
                    msg_copy['content'].insert(0, {"text": f"System instructions: {system_prompt}"})
                
                nova_messages.append(msg_copy)
            
            payload = {
                "inferenceConfig": {
                    "max_new_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                },
                "messages": nova_messages
            }
            
            # Log Nova payload structure for debugging
            logger.info(f"Nova payload structure - messages count: {len(payload['messages'])}")
            for msg in payload['messages']:
                logger.info(f"Message role: {msg['role']}, content items: {len(msg.get('content', []))}")
            
            # Call invoke_model API
            response = bedrock.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(payload)
            )

            # Parse response
            response_body = json.loads(response.get('body').read())
            logger.info(f"Nova response structure: {response_body.keys()}")
            
            # Validate và extract response text
            if ('output' in response_body and 'message' in response_body['output'] and 
                'content' in response_body['output']['message'] and 
                len(response_body['output']['message']['content']) > 0):
                return response_body['output']['message']['content'][0]['text']
            else:
                logger.warning("Unexpected Nova response format")
                return str(response_body)
    
    except Exception as e:
        logger.error(f"Error processing conversation: {str(e)}")
        raise

def process_input_multi_image_prompt(image_bytes_list, prompt_list, model_id, system_prompt=None, 
                             temperature=None, top_p=None, top_k=None, max_tokens=None):
    """
    Xử lý input với nhiều cặp ảnh-prompt theo thứ tự xen kẽ image1, prompt1, image2, prompt2
    
    Args:
        image_bytes_list: List of binary image data (có thể chứa None)
        prompt_list: List of prompt texts corresponding to images
        model_id: ID của model Bedrock
        system_prompt: System prompt (optional)
        temperature, top_p, top_k, max_tokens: Parameters cho model (nếu None sẽ dùng giá trị mặc định)
    
    Returns:
        Phản hồi từ model
    """
    try:
        # Xác định region từ model_id
        region = get_region_from_model_id(model_id)
        logger.info(f"Using region: {region} for model {model_id}")
        
        # Tạo session và client với region tương ứng
        session = boto3.Session(region_name=region)
        bedrock = session.client(service_name='bedrock-runtime')
        
        # Xác định loại model
        is_anthropic_model = "anthropic" in model_id.lower()
        
        # Sử dụng giá trị mặc định dựa vào loại model nếu không có giá trị truyền vào
        if temperature is None:
            temperature = CLAUDE_DEFAULT_TEMPERATURE if is_anthropic_model else NOVA_DEFAULT_TEMPERATURE
        
        if top_p is None:
            top_p = CLAUDE_DEFAULT_TOP_P if is_anthropic_model else NOVA_DEFAULT_TOP_P
        
        if top_k is None:
            top_k = CLAUDE_DEFAULT_TOP_K if is_anthropic_model else NOVA_DEFAULT_TOP_K
            
        if max_tokens is None:
            max_tokens = CLAUDE_DEFAULT_MAX_TOKENS if is_anthropic_model else NOVA_DEFAULT_MAX_TOKENS
        
        if is_anthropic_model:
            # Cấu trúc cho Anthropic Claude models
            content = []
            
            # Thêm ảnh và prompt theo cặp
            for i in range(len(prompt_list)):
                # Chỉ thêm ảnh nếu có và không phải None
                if i < len(image_bytes_list) and image_bytes_list[i] is not None:
                    image_format = detect_image_format(image_bytes_list[i])
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": f"image/{image_format}",
                            "data": base64.b64encode(image_bytes_list[i]).decode('utf-8')
                        }
                    })
                
                # Luôn thêm prompt nếu có
                if i < len(prompt_list) and prompt_list[i] is not None and prompt_list[i].strip():
                    content.append({"type": "text", "text": prompt_list[i]})
            
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            }
            
            if system_prompt and system_prompt.strip():
                payload["system"] = system_prompt
            
            # Call invoke_model API
            response = bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps(payload)
            )

            response_body = json.loads(response['body'].read().decode('utf-8'))
            
            logger.info(f"Claude response usage: {response_body.get('usage', {})}")

            # Validate và extract response text
            if 'content' in response_body and len(response_body['content']) > 0:
                if 'text' in response_body['content'][0]:
                    return response_body['content'][0]['text']
                else:
                    logger.warning("Unexpected Claude response format")
                    return str(response_body['content'][0])
            else:
                logger.warning("Unexpected Claude response format")
                return str(response_body)
            
        else:
            # Keep your existing content preparation
            content = []

            # Add system prompt if provided
            if system_prompt and system_prompt.strip():
                content.append({"text": f"System instructions: {system_prompt}"})

            # Add images and prompts in pairs
            for i in range(len(prompt_list)):
                if i < len(image_bytes_list) and image_bytes_list[i] is not None:
                    image_format = detect_image_format(image_bytes_list[i])
                    content.append({
                        "image": {
                            "format": image_format,
                            "source": {
                                "bytes": base64.b64encode(image_bytes_list[i]).decode('utf-8')
                            }
                        }
                    })
                
                if i < len(prompt_list) and prompt_list[i] is not None and prompt_list[i].strip():
                    content.append({"text": prompt_list[i]})

            # Nova specific invoke structure
            response = bedrock.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "inferenceConfig": {
                        "max_new_tokens": max_tokens,
                        "temperature": temperature,
                        "top_p": top_p,
                    },
                    "messages": [
                        {
                            "role": "user",
                            "content": content
                        }
                    ]
                })
            )

            # Get the response
            response_body = json.loads(response.get('body').read())
            
            # Validate và extract response text
            if ('output' in response_body and 'message' in response_body['output'] and 
                'content' in response_body['output']['message'] and 
                len(response_body['output']['message']['content']) > 0):
                return response_body['output']['message']['content'][0]['text']
            else:
                logger.warning("Unexpected Nova response format")
                return str(response_body)
    
    except Exception as e:
        logger.error(f"Error processing input: {str(e)}")
        raise

# Original process_input function kept for backward compatibility
def process_input(prompt_content, model_id, system_prompt=None, image_bytes_list=None, 
                 temperature=None, top_p=None, top_k=None, max_tokens=None):
    """
    Xử lý input (text và/hoặc nhiều images) với model Bedrock.
    
    Args:
        prompt_content: Nội dung prompt từ user
        model_id: ID của model Bedrock
        system_prompt: System prompt (optional)
        image_bytes_list: List of binary image data (optional) - có thể là một ảnh hoặc list ảnh
        temperature, top_p, top_k, max_tokens: Parameters cho model (nếu None sẽ dùng giá trị mặc định)
    
    Returns:
        Phản hồi từ model
    """
    try:
        # Xác định region từ model_id
        region = get_region_from_model_id(model_id)
        logger.info(f"Using region: {region} for model {model_id}")
        
        # Tạo session và client với region tương ứng
        session = boto3.Session(region_name=region)
        bedrock = session.client(service_name='bedrock-runtime')
        
        # Đảm bảo image_bytes_list là một list để xử lý đồng nhất
        if image_bytes_list is not None and not isinstance(image_bytes_list, list):
            image_bytes_list = [image_bytes_list]  # Chuyển đổi ảnh đơn thành list
        
        # Xác định loại model
        is_anthropic_model = "anthropic" in model_id.lower()
        
        # Sử dụng giá trị mặc định dựa vào loại model nếu không có giá trị truyền vào
        if temperature is None:
            temperature = CLAUDE_DEFAULT_TEMPERATURE if is_anthropic_model else NOVA_DEFAULT_TEMPERATURE
        
        if top_p is None:
            top_p = CLAUDE_DEFAULT_TOP_P if is_anthropic_model else NOVA_DEFAULT_TOP_P
        
        if top_k is None:
            top_k = CLAUDE_DEFAULT_TOP_K if is_anthropic_model else NOVA_DEFAULT_TOP_K
            
        if max_tokens is None:
            max_tokens = CLAUDE_DEFAULT_MAX_TOKENS if is_anthropic_model else NOVA_DEFAULT_MAX_TOKENS
        
        if is_anthropic_model:
            # Cấu trúc cho Anthropic Claude models
            
            content = []
            # Kiểm tra xem prompt có nội dung không
            if prompt_content and prompt_content.strip():
                content.append({"type": "text", "text": prompt_content})
            
            # Thêm images nếu có
            if image_bytes_list:
                for idx, img_bytes in enumerate(image_bytes_list, 1):
                    if img_bytes is not None:  # Chỉ xử lý ảnh không phải None
                        image_format = detect_image_format(img_bytes)
                        # Thêm label cho ảnh
                        content.append({"type": "text", "text": f"Image {idx}:"})
                        content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": f"image/{image_format}",
                                "data": base64.b64encode(img_bytes).decode('utf-8')
                            }
                        })
            
            # Kiểm tra xem content có rỗng không
            if not content:
                raise ValueError("Empty content: both prompt and images are empty")
                
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            }
            
            if system_prompt and system_prompt.strip():
                payload["system"] = system_prompt

            # Call invoke_model API
            response = bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps(payload)
            )
            response_body = json.loads(response['body'].read().decode('utf-8'))
            
            # Validate và extract response text
            if 'content' in response_body and len(response_body['content']) > 0:
                if 'text' in response_body['content'][0]:
                    return response_body['content'][0]['text']
                else:
                    logger.warning("Unexpected Claude response format")
                    return str(response_body['content'][0])
            else:
                logger.warning("Unexpected Claude response format")
                return str(response_body)
            
        else:
            # Cấu trúc cho Amazon models (Nova)
            content = []
            
            # Thêm system prompt nếu có
            if system_prompt and system_prompt.strip():
                content.append({"text": f"System instructions: {system_prompt}"})
            
            # Thêm prompt content nếu có
            if prompt_content and prompt_content.strip():
                content.append({"text": prompt_content})
            
            # Thêm images nếu có
            if image_bytes_list:
                for idx, img_bytes in enumerate(image_bytes_list, 1):
                    if img_bytes is not None:  # Chỉ xử lý ảnh không phải None
                        image_format = detect_image_format(img_bytes)
                        content.append({"text": f"Image {idx}:"})
                        content.append({
                            "image": {
                                "format": image_format,
                                "source": {
                                    "bytes": base64.b64encode(img_bytes).decode('utf-8')
                                }
                            }
                        })
            
            # Kiểm tra xem content có rỗng không
            if not content:
                raise ValueError("Empty content: both prompt and images are empty")
                
            # Prepare message
            message = {
                "role": "user",
                "content": content
            }
            
            # Call invoke_model API
            response = bedrock.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "inferenceConfig": {
                        "max_new_tokens": max_tokens,
                        "temperature": temperature,
                        "top_p": top_p,
                    },
                    "messages": [message]
                })
            )
            
            # Get the response
            response_body = json.loads(response.get('body').read())
            
            # Validate và extract response text
            if ('output' in response_body and 'message' in response_body['output'] and 
                'content' in response_body['output']['message'] and 
                len(response_body['output']['message']['content']) > 0):
                return response_body['output']['message']['content'][0]['text']
            else:
                logger.warning("Unexpected Nova response format")
                return str(response_body)
    
    except Exception as e:
        logger.error(f"Error processing input: {str(e)}")
        raise

# Legacy wrapper functions for backward compatibility
def get_response_from_model(prompt_content, image_bytes, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", 
                           temperature=None, top_p=None, max_tokens=None):
    """Process image and text input using Bedrock model (Legacy wrapper)."""
    return process_input(prompt_content, model_id, image_bytes_list=image_bytes,
                        temperature=temperature, top_p=top_p, max_tokens=max_tokens)

def get_response_from_model_with_system(prompt_content, image_bytes, system_prompt, 
                                       model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", 
                                       temperature=None, top_p=None, max_tokens=None):
    """Process image and text input with system prompt (Legacy wrapper)."""
    return process_input(prompt_content, model_id, system_prompt=system_prompt, 
                        image_bytes_list=image_bytes, temperature=temperature, 
                        top_p=top_p, max_tokens=max_tokens)

def get_text_response(prompt_content, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", 
                     temperature=None, top_p=None, max_tokens=None):
    """Process text-only input (Legacy wrapper)."""
    return process_input(prompt_content, model_id, temperature=temperature, 
                        top_p=top_p, max_tokens=max_tokens)

def get_text_response_with_system(prompt_content, system_prompt, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", 
                                temperature=None, top_p=None, max_tokens=None):
    """Process text input with system prompt (Legacy wrapper)."""
    return process_input(prompt_content, model_id, system_prompt=system_prompt,
                        temperature=temperature, top_p=top_p, max_tokens=max_tokens)
import boto3
from io import BytesIO
import imghdr
import logging
import json
import base64
from PIL import Image, ExifTags
import io

def fix_image_orientation(image_bytes):
    """Sửa hướng ảnh dựa vào dữ liệu EXIF."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # Kiểm tra và xử lý orientation từ EXIF
        if hasattr(img, '_getexif') and img._getexif():
            exif = dict([(ExifTags.TAGS.get(k, k), v) for k, v in img._getexif().items()])
            if 'Orientation' in exif:
                orientation = exif['Orientation']
                
                if orientation == 2:
                    img = img.transpose(Image.FLIP_LEFT_RIGHT)
                elif orientation == 3:
                    img = img.rotate(180)
                elif orientation == 4:
                    img = img.transpose(Image.FLIP_TOP_BOTTOM)
                elif orientation == 5:
                    img = img.transpose(Image.FLIP_LEFT_RIGHT).rotate(90)
                elif orientation == 6:
                    img = img.rotate(270)
                elif orientation == 7:
                    img = img.transpose(Image.FLIP_LEFT_RIGHT).rotate(270)
                elif orientation == 8:
                    img = img.rotate(90)
        
        # Chuyển lại thành bytes
        buffer = io.BytesIO()
        img.save(buffer, format=img.format if img.format else 'JPEG')
        return buffer.getvalue()
    except Exception as e:
        logger.warning(f"Không thể sửa orientation của ảnh: {e}")
        return image_bytes  # Trả về ảnh gốc nếu có lỗi
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

def process_conversation(messages, model_id, system_prompt=None, 
                        temperature=0.0, top_p=0.9, top_k=45, max_tokens=2000):
    """
    Xử lý hội thoại với nhiều message với format giống API
    
    Args:
        messages: List of message objects with role and content array
        model_id: ID của model Bedrock
        system_prompt: System prompt (optional)
        temperature, top_p, max_tokens: Parameters cho model
    
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
        
        # Tạo session và client
        session = boto3.Session()
        bedrock = session.client(service_name='bedrock-runtime')
        
        # Xác định loại model
        is_anthropic_model = "anthropic" in model_id.lower()
        
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
                             temperature=0.0, top_p=0.9, top_k=45, max_tokens=2000):
    """
    Xử lý input với nhiều cặp ảnh-prompt theo thứ tự xen kẽ image1, prompt1, image2, prompt2
    
    Args:
        image_bytes_list: List of binary image data (có thể chứa None)
        prompt_list: List of prompt texts corresponding to images
        model_id: ID của model Bedrock
        system_prompt: System prompt (optional)
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
                 temperature=0.0, top_p=0.9, max_tokens=2000):
    """
    Xử lý input (text và/hoặc nhiều images) với model Bedrock.
    
    Args:
        prompt_content: Nội dung prompt từ user
        model_id: ID của model Bedrock
        system_prompt: System prompt (optional)
        image_bytes_list: List of binary image data (optional) - có thể là một ảnh hoặc list ảnh
        temperature, top_p, max_tokens: Parameters cho model
    
    Returns:
        Phản hồi từ model
    """
    try:
        session = boto3.Session()
        bedrock = session.client(service_name='bedrock-runtime')
        
        # Đảm bảo image_bytes_list là một list để xử lý đồng nhất
        if image_bytes_list is not None and not isinstance(image_bytes_list, list):
            image_bytes_list = [image_bytes_list]  # Chuyển đổi ảnh đơn thành list
        
        # Xác định loại model
        is_anthropic_model = "anthropic" in model_id.lower()
        
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
                           temperature=0.0, top_p=0.9, max_tokens=2000):
    """Process image and text input using Bedrock model (Legacy wrapper)."""
    return process_input(prompt_content, model_id, image_bytes_list=image_bytes,
                        temperature=temperature, top_p=top_p, max_tokens=max_tokens)

def get_response_from_model_with_system(prompt_content, image_bytes, system_prompt, 
                                       model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", 
                                       temperature=0.0, top_p=0.9, max_tokens=2000):
    """Process image and text input with system prompt (Legacy wrapper)."""
    return process_input(prompt_content, model_id, system_prompt=system_prompt, 
                        image_bytes_list=image_bytes, temperature=temperature, 
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
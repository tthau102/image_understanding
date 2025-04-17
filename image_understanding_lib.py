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

def process_input_multi_image_prompt(image_bytes_list, prompt_list, model_id, system_prompt=None, 
                             temperature=0.0, top_p=0.9, top_k=45, max_tokens=2000):
    """
    Xử lý input với nhiều cặp ảnh-prompt theo thứ tự xen kẽ image1, prompt1, image2, prompt2
    
    Args:
        image_bytes_list: List of binary image data
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
            # Cấu trúc cho Anthropic Claude models - sử dụng invoke_model
            content = []
            
            # Thêm ảnh và prompt theo cặp
            for i in range(len(image_bytes_list)):
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
                
                if i < len(prompt_list) and prompt_list[i] is not None:
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
            
            if system_prompt:
                payload["system"] = system_prompt
            
            # Call invoke_model API
            response = bedrock.invoke_model(
                modelId=model_id,
                body=json.dumps(payload)
            )


            response_body = json.loads(response['body'].read().decode('utf-8'))
            
            print("****************************************************************************************************************************************")
            for i in range(len(content)):
                print(content[i]['type'])
            print(response_body['usage'])
            print("****************************************************************************************************************************************")

            return response_body['content'][0]['text']
            
        else:
            # Cấu trúc cho Amazon models (Nova) - sử dụng converse API
            content = []
            
            # Add system prompt if provided
            if system_prompt:
                content.append({"text": f"System instructions: {system_prompt}"})
            
            # Thêm ảnh và prompt theo cặp
            for i in range(len(image_bytes_list)):
                if i < len(image_bytes_list) and image_bytes_list[i] is not None:
                    image_format = detect_image_format(image_bytes_list[i])
                    content.append({
                        "image": {
                            "format": image_format,
                            "source": {
                                "bytes": image_bytes_list[i]
                            }
                        }
                    })
                
                if i < len(prompt_list) and prompt_list[i] is not None:
                    content.append({"text": prompt_list[i]})
            
            # Prepare message
            message = {
                "role": "user",
                "content": content
            }
            
            # Call converse API
            response = bedrock.converse(
                modelId=model_id,
                messages=[message],
                inferenceConfig={
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                    "topP": top_p
                },
            )

            print("****************************************************************************************************************************************")
            for i in range(len(content)):
                if content[i].get('image'):
                    print('image')
                if content[i].get('text'):
                    print('text')
            print(response['usage'])
            print("****************************************************************************************************************************************")

            
            return response['output']['message']['content'][0]['text']
    
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
            # Cấu trúc cho Anthropic Claude models - sử dụng invoke_model
            
            if image_bytes_list:
                # Prepare message with multiple images
                content = []
                for idx, img_bytes in enumerate(image_bytes_list, 1):
                    image_format = detect_image_format(img_bytes)
                    content.append({"type": "text", "text": f"Image {idx}:"})
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": f"image/{image_format}",
                            "data": base64.b64encode(img_bytes).decode('utf-8')
                        }
                    })
                content.append({"type": "text", "text": prompt_content})
            else:
                # Text only content
                content = [{"type": "text", "text": prompt_content}]
            
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
            content = []
            
            if image_bytes_list:
                # Prepare message with multiple images
                content.append({"text": prompt_content if not system_prompt else f"System instructions: {system_prompt}\n\nUser: {prompt_content}"})
                
                for idx, img_bytes in enumerate(image_bytes_list, 1):
                    image_format = detect_image_format(img_bytes)
                    content.append({"text": f"Image {idx}:"})
                    content.append({
                        "image": {
                            "format": image_format,
                            "source": {
                                "bytes": img_bytes
                            }
                        }
                    })
            else:
                # Text only content
                content.append({"text": prompt_content if not system_prompt else f"System instructions: {system_prompt}\n\nUser: {prompt_content}"})
            
            # Prepare message
            message = {
                "role": "user",
                "content": content
            }
            
            # Call converse API
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
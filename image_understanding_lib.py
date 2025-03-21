import boto3
from io import BytesIO
import imghdr
import json
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

def query_knowledge_base(kb_id, prompt, max_results=5):
    """Query Knowledge Base using the correct Bedrock Agent Runtime API."""
    try:
        session = boto3.Session()
        # Sử dụng bedrock-agent-runtime thay vì bedrock-agent
        bedrock_agent = session.client(service_name='bedrock-agent-runtime')
        
        logger.info(f"Querying KB: {kb_id} with prompt: {prompt}")
        
        # Sử dụng retrieveAndGenerate API thay vì retrieve
        response = bedrock_agent.retrieve_and_generate(
            input={
                'text': prompt
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': kb_id,
                    # Cần thay <region> và <account> bằng giá trị thực
                    'modelArn': 'arn:aws:bedrock:<region>:<account>:model/anthropic.claude-3-5-sonnet-20240620-v1'
                }
            }
        )
        
        # Xử lý response theo cấu trúc mới
        results = []
        for citation in response.get('citations', []):
            if 'retrievedReferences' in citation:
                for ref in citation['retrievedReferences']:
                    if 'content' in ref and 'text' in ref['content']:
                        results.append(ref['content']['text'])
        
        context = "\n\n".join(results)
        logger.info(f"Retrieved context from KB (first 200 chars): {context[:200]}...")
        return context
    except Exception as e:
        logger.error(f"Error querying Knowledge Base: {str(e)}")
        return ""

def get_response_with_rag(prompt_content, image_bytes, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", 
                         collection_name="HYDL8ADSDN", temperature=0.0, top_p=0.9, max_tokens=2000):
    """Process image input with RAG from Knowledge Base."""
    try:
        session = boto3.Session()
        bedrock = session.client(service_name='bedrock-runtime')
        
        # Query Knowledge Base
        context = query_knowledge_base(collection_name, prompt_content)
        
        # Detect image format
        image_format = detect_image_format(image_bytes)
        
        # Create RAG prompt
        rag_prompt = f"""
Bạn là trợ lý phân tích hình ảnh và trả lời dựa trên dữ liệu.
Hãy phân tích hình ảnh và trả lời câu hỏi dưới đây.

ĐÂY LÀ THÔNG TIN QUAN TRỌNG TỪ KNOWLEDGE BASE CỦA TÔI, HÃY ƯU TIÊN SỬ DỤNG:
{context}

CÂU HỎI:
{prompt_content}
"""
        
        # Prepare message with image and enhanced prompt
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
                {"text": rag_prompt}
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
        logger.error(f"Error processing image with RAG: {str(e)}")
        raise

def get_text_response_with_rag(prompt_content, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", 
                              collection_name="HYDL8ADSDN", temperature=0.0, top_p=0.9, max_tokens=2000):
    """Process text-only input with RAG from Knowledge Base."""
    try:
        session = boto3.Session()
        bedrock = session.client(service_name='bedrock-runtime')
        
        # Query Knowledge Base
        context = query_knowledge_base(collection_name, prompt_content)
        
        # Create RAG prompt
        rag_prompt = f"""
Bạn là trợ lý trả lời dựa trên dữ liệu.
Hãy trả lời câu hỏi dựa trên thông tin được cung cấp.

ĐÂY LÀ THÔNG TIN QUAN TRỌNG TỪ KNOWLEDGE BASE CỦA TÔI, HÃY ƯU TIÊN SỬ DỤNG:
{context}

CÂU HỎI:
{prompt_content}
"""
        
        # Prepare message with enhanced prompt
        message = {
            "role": "user",
            "content": [
                {"text": rag_prompt}
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
        logger.error(f"Error processing text with RAG: {str(e)}")
        raise
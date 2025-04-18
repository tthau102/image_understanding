import streamlit as st
import image_understanding_lib as glib
import json
import re
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cấu hình trang
st.set_page_config(layout="wide", page_title="Image Understanding")
st.title("Image Understanding")

# Chia layout thành 4 cột
col1, col2, col3, col4 = st.columns([2,2.5,3.5,3.5])

# Dictionary chứa các model options
model_options_dict = {
    "Amazon Nova Pro": "apac.amazon.nova-pro-v1:0",
    "Amazon Nova Lite": "apac.amazon.nova-lite-v1:0",
    "Claude 3.5 Sonnet v2": "apac.anthropic.claude-3-5-sonnet-20241022-v2:0"
}

# Cột 1: Cấu hình model và parameters
with col1:
    st.subheader("Model Configuration")
    
    # Chọn model
    model_selection = st.selectbox(
        "Model:",
        options=list(model_options_dict.keys()),
        index=0,
    )
    selected_model_id = model_options_dict[model_selection]

    # Inference parameters
    st.subheader("Inference Parameters")
    
    temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.0, step=0.1, format='%.1f')
    top_p = st.slider("Top P", min_value=0.1, max_value=1.0, value=0.7, step=0.1, format='%.1f')
    top_k = st.slider("Top K", min_value=1, max_value=500, value=45, step=1)
    max_tokens = st.slider("Max Tokens", min_value=100, max_value=4000, value=3000, step=100)
    
    # System Prompt
    st.subheader("System Prompt")
    system_prompt = st.text_area(
        "Enter system instructions:",
        height=100,
        help="Instructions that guide the model's behavior.",
        placeholder="You are an expert at analyzing images. Be concise and detailed in your responses."
    )

# Initialize session state variables if they don't exist
if 'uploaded_files1' not in st.session_state:
    st.session_state.uploaded_files1 = None
if 'uploaded_files2' not in st.session_state:
    st.session_state.uploaded_files2 = None

# Cột 2: Upload hình ảnh 1 và prompt 1
with col2:
    # Phần trên: Upload hình ảnh 1
    st.subheader("First Image")
    uploaded_files1 = st.file_uploader("Upload first image", type=['png', 'jpg', 'jpeg'], key="image1")
    st.session_state.uploaded_files1 = uploaded_files1
    
    if uploaded_files1:
        # Hiển thị ảnh đã upload với kích thước nhỏ hơn (1/2 width của cột)
        uploaded_image_preview = glib.get_bytesio_from_bytes(uploaded_files1.getvalue())
        st.image(uploaded_image_preview, width=100)
    
    # Phần dưới: Nhập prompt 1
    st.subheader("First Prompt")
    prompt_text1 = st.text_area(
        "Enter your first prompt:",
        height=200,
        key="prompt1",
        help="Enter your question or prompt related to the first image.",
        placeholder="Look, describe and remember the item."
    )

# Cột 3: Upload hình ảnh 2 và prompt 2
with col3:
    # Phần trên: Upload hình ảnh 2
    st.subheader("Second Image")
    uploaded_files2 = st.file_uploader("Upload second image", type=['png', 'jpg', 'jpeg'], key="image2")
    st.session_state.uploaded_files2 = uploaded_files2
    
    if uploaded_files2:
        # Hiển thị ảnh đã upload với kích thước nhỏ hơn (1/2 width của cột)
        uploaded_image_preview = glib.get_bytesio_from_bytes(uploaded_files2.getvalue())
        st.image(uploaded_image_preview, use_column_width=True)
    
    # Phần dưới: Nhập prompt 2
    st.subheader("Second Prompt")
    prompt_text2 = st.text_area(
        "Enter your second prompt:",
        height=200,
        key="prompt2",
        help="Enter your question or prompt related to the second image.",
        placeholder="Count the remembered item in this fridge"
    )

# Function to process multi-image-prompt request
def process_multi_image_prompt_request(image_bytes_list, prompt_list, model_id, system_prompt=None,
                                     temperature=0.0, top_p=0.9, top_k=45, max_tokens=2000):
    """Process request with multiple image-prompt pairs."""
    
    try:
        # Determine if system prompt should be used
        has_system_prompt = system_prompt and system_prompt.strip() != ""
        system_prompt = system_prompt if has_system_prompt else None
        
        # Unified processing function for multiple image-prompt pairs
        response = glib.process_input_multi_image_prompt(
            image_bytes_list=image_bytes_list,
            prompt_list=prompt_list,
            model_id=model_id,
            system_prompt=system_prompt,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            max_tokens=max_tokens
        )
        return response
            
    except Exception as e:
        logger.error(f"Error during processing: {str(e)}")
        raise

# Cột 4: Hiển thị kết quả và nút "Go"
# Cột 4: Hiển thị kết quả và nút "Go"
with col4:
    st.subheader("Result")
    
    # Nút "Go" button
    go_button = st.button("Go", type="primary")

    if go_button:
        # Kiểm tra có bất kỳ input nào để xử lý
        has_any_input = (uploaded_files1 is not None or prompt_text1.strip() or 
                         uploaded_files2 is not None or prompt_text2.strip())
        
        if not has_any_input:
            st.error("Please provide at least one input (image or prompt)")
        else:
            with st.spinner("Processing..."):
                try:
                    # Chuẩn bị danh sách image bytes và prompts
                    image_bytes_list = []
                    prompt_list = []
                    
                    # Xử lý các trường hợp đầu vào cho phần 1
                    if uploaded_files1 is not None or prompt_text1.strip():
                        # Xử lý image 1
                        image_bytes = uploaded_files1.getvalue() if uploaded_files1 else None
                        image_bytes_list.append(image_bytes)
                        
                        # Xử lý prompt 1
                        prompt = prompt_text1.strip() if prompt_text1.strip() else "Describe this image"
                        prompt_list.append(prompt)
                    
                    # Xử lý các trường hợp đầu vào cho phần 2
                    if uploaded_files2 is not None or prompt_text2.strip():
                        # Xử lý image 2
                        image_bytes = uploaded_files2.getvalue() if uploaded_files2 else None
                        image_bytes_list.append(image_bytes)
                        
                        # Xử lý prompt 2
                        prompt = prompt_text2.strip() if prompt_text2.strip() else "Describe this image"
                        prompt_list.append(prompt)
                    
                    # Get system prompt if provided
                    sys_prompt = system_prompt.strip() if system_prompt.strip() else None
                    
                    # Process multi-image-prompt request
                    response = process_multi_image_prompt_request(
                        image_bytes_list=image_bytes_list,
                        prompt_list=prompt_list,
                        model_id=selected_model_id,
                        temperature=temperature,
                        top_p=top_p,
                        top_k=top_k,
                        max_tokens=max_tokens,
                        system_prompt=sys_prompt
                    )
                    
                    # Hiển thị kết quả
                    st.write(response)
                        
                except Exception as e:
                    logger.error(f"Error during processing: {str(e)}")
                    st.error(f"Đã xảy ra lỗi: {str(e)}")
                    if "AccessDeniedException" in str(e):
                        st.error("Kiểm tra IAM Role có đủ quyền truy cập vào Bedrock API")
                    else:
                        st.error("Kiểm tra IAM Role có đủ quyền truy cập vào Bedrock Model")






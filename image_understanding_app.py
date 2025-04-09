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

# Dictionary chứa các knowledge base options
kb_options_dict = {
    "None": None,
    # "tthau-test-kb-002": "PIGIMPRA55"
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
    
    help_temperature = "Controls randomness. Lower values are more deterministic, higher values more creative."
    help_top_p = "Controls token choices. Lower values focus on most likely tokens."
    help_max_tokens = "Maximum number of tokens to generate in the response."
    
    temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.0, step=0.1, 
                           help=help_temperature, format='%.1f')
    top_p = st.slider("Top P", min_value=0.1, max_value=1.0, value=1.0, step=0.1, 
                     help=help_top_p, format='%.1f')
    max_tokens = st.slider("Max Tokens", min_value=100, max_value=4000, value=2000, step=100, 
                          help=help_max_tokens)

    # Knowledge Base configuration
    st.subheader("Knowledge Base")
    enable_kb = st.checkbox("Enable Knowledge Base", value=False)
    
    kb_selection = st.selectbox(
        "Knowledge Base:",
        options=list(kb_options_dict.keys()),
        index=0,
        disabled=not enable_kb
    )
    selected_kb_id = kb_options_dict[kb_selection]
    
    # KB Retrieval settings nếu enable KB
    if enable_kb and selected_kb_id:
        num_results = st.slider("Number of Results", min_value=1, max_value=10, value=5, step=1,
                         help="Maximum number of retrieval results")

# Cột 2: Upload hình ảnh
with col2:
    st.subheader("Select an Image (Optional)")
    uploaded_file = st.file_uploader("Upload an image", type=['png', 'jpg', 'jpeg'])
    
    if uploaded_file:
        uploaded_image_preview = glib.get_bytesio_from_bytes(uploaded_file.getvalue())
        st.image(uploaded_image_preview)

# Cột 3: Nhập prompt
with col3:
    st.subheader("Prompt")
    
    with st.form(key="prompt_form"):
        with st.expander("System Prompt (Optional)", expanded=False):
            system_prompt = st.text_area(
                "Enter system instructions:",
                height=100,
                help="Instructions that guide the model's behavior but aren't shown as part of the main prompt.",
                placeholder="You are an expert at analyzing images. Be concise and detailed in your responses."
            )
        
        prompt_text = st.text_area(
            "Enter your User prompt:",
            height=400,
            help="Enter your question or prompt.",
        )
        
        go_button = st.form_submit_button("Go", type="primary")

# Function to process request based on parameters
def process_request(prompt_text, model_id, temperature, top_p, max_tokens, 
                   system_prompt=None, image_bytes=None, kb_id=None, num_results=5):
    """Process request với hàm phù hợp dựa trên tham số đầu vào."""
    
    try:
        # Determine if system prompt should be used
        has_system_prompt = system_prompt and system_prompt.strip() != ""
        system_prompt = system_prompt if has_system_prompt else None
        
        # KB or regular processing
        if kb_id:
            logger.info(f"Processing KB request with model: {model_id}")
            retrieval_config = {"numberOfResults": num_results} if num_results else {}
            
            # Unified KB processing with optional image
            return glib.process_kb_input(
                prompt_content=prompt_text,
                kb_id=kb_id,
                model_id=model_id,
                image_bytes=image_bytes,
                system_prompt=system_prompt,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                retrieval_config=retrieval_config,
                num_results=num_results
            )
        else:
            logger.info(f"Processing regular request with model: {model_id}")
            # Unified processing function
            response = glib.process_input(
                prompt_content=prompt_text,
                model_id=model_id,
                system_prompt=system_prompt,
                image_bytes=image_bytes,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens
            )
            return response, None  # No citations for regular processing
            
    except Exception as e:
        logger.error(f"Error during processing: {str(e)}")
        raise

# Cột 4: Hiển thị kết quả
with col4:
    st.subheader("Result")

    if go_button:
        if not prompt_text.strip():
            st.error("Please enter a prompt")
        else:
            with st.spinner("Processing..."):
                try:
                    # Get image bytes if uploaded
                    image_bytes = uploaded_file.getvalue() if uploaded_file else None
                    
                    # Get system prompt if provided
                    sys_prompt = system_prompt.strip() if 'system_prompt' in locals() and system_prompt.strip() else None
                    
                    # Get KB ID if enabled
                    kb_id = selected_kb_id if enable_kb else None
                    
                    # Get num results for KB
                    kb_results = num_results if 'num_results' in locals() else 5
                    
                    # Process request
                    response, citations = process_request(
                        prompt_text=prompt_text,
                        model_id=selected_model_id,
                        temperature=temperature,
                        top_p=top_p,
                        max_tokens=max_tokens,
                        system_prompt=sys_prompt,
                        image_bytes=image_bytes,
                        kb_id=kb_id,
                        num_results=kb_results
                    )
                    
                    # Hiển thị kết quả
                    st.write(response)
                    
                    # Display citations if available
                    if citations:
                        with st.expander("Citations", expanded=False):
                            for i, citation in enumerate(citations, 1):
                                st.markdown(f"**Citation {i}:**")
                                st.json(citation)
                        
                except Exception as e:
                    logger.error(f"Error during processing: {str(e)}")
                    st.error(f"Đã xảy ra lỗi: {str(e)}")
                    if "AccessDeniedException" in str(e):
                        st.error("Kiểm tra IAM Role có đủ quyền truy cập vào Bedrock API và Knowledge Base")
                    elif "ResourceNotFoundException" in str(e):
                        st.error("Knowledge Base không tồn tại hoặc không khả dụng")
                    else:
                        st.error("Kiểm tra IAM Role có đủ quyền truy cập vào Bedrock Model")
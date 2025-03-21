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

# Chia layout thành 3 cột
col1, col2, col3, col4 = st.columns(4)

# Dictionary chứa các model options
model_options_dict = {
    "Claude 3.5 Sonnet": "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "Amazon Nova Lite": "amazon.nova-lite-v1:0", 
    "Amazon Nova Pro": "amazon.nova-pro-v1:0"
}

# Dictionary chứa các knowledge base options
kb_options_dict = {
    "None": None,
    "tthau-test-kb-01": "HYDL8ADSDN",
    "tthau-test-kb-02": "LWS78SW0OR"
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

    # Inference parameters
    st.subheader("Inference Parameters")
    
    help_temperature = "Controls randomness. Lower values are more deterministic, higher values more creative."
    help_top_p = "Controls token choices. Lower values focus on most likely tokens."
    help_max_tokens = "Maximum number of tokens to generate in the response."
    
    temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.0, step=0.1, 
                           help=help_temperature, format='%.1f')
    top_p = st.slider("Top P", min_value=0.1, max_value=1.0, value=0.5, step=0.1, 
                     help=help_top_p, format='%.1f')
    max_tokens = st.slider("Max Tokens", min_value=100, max_value=4000, value=2000, step=100, 
                          help=help_max_tokens)

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
    prompt_text = st.text_area(
        "Enter your prompt:",
        height=150,
        help="Enter your question or prompt.",
    )
    
    go_button = st.button("Go", type="primary")

# Cột 4: Hiển thị kết quả
with col4:
    st.subheader("Result")

    if go_button:
        if not prompt_text.strip():
            st.error("Please enter a prompt")
        else:
            with st.spinner("Processing..."):
                try:
                    # Xác định nếu có hình ảnh hay không
                    image_bytes = uploaded_file.getvalue() if uploaded_file else None
                    
                    # Lựa chọn phương thức xử lý phù hợp dựa trên input và Knowledge Base
                    if enable_kb and selected_kb_id:
                        # Sử dụng Knowledge Base API
                        logger.info(f"Processing with Knowledge Base: {selected_kb_id}")
                        
                        retrieval_config = {"numberOfResults": num_results} if 'num_results' in locals() else {}
                        
                        if image_bytes:
                            response, citations = glib.get_kb_response_with_image(
                                prompt_content=prompt_text,
                                kb_id=selected_kb_id,
                                image_bytes=image_bytes,
                                model_id=selected_model_id,
                                temperature=temperature,
                                top_p=top_p,
                                max_tokens=max_tokens,
                                retrieval_config=retrieval_config
                            )
                        else:
                            response, citations = glib.get_kb_response(
                                prompt_content=prompt_text,
                                kb_id=selected_kb_id,
                                model_id=selected_model_id,
                                temperature=temperature,
                                top_p=top_p,
                                max_tokens=max_tokens,
                                retrieval_config=retrieval_config
                            )
                        
                        # Hiển thị kết quả
                        st.write(response)
                        
                        # Hiển thị citations nếu có
                        if citations:
                            st.subheader("Citations")
                            for i, citation in enumerate(citations):
                                st.markdown(f"**Source {i+1}:**")
                                for ref in citation.get('retrievedReferences', []):
                                    content = ref.get('content', {})
                                    if 'text' in content:
                                        st.markdown(f"- {content['text'][:200]}...")
                    else:
                        # Sử dụng API nguyên bản không có Knowledge Base
                        if image_bytes:
                            logger.info(f"Processing image request with model: {selected_model_id}")
                            response = glib.get_response_from_model(
                                prompt_content=prompt_text, 
                                image_bytes=image_bytes,
                                model_id=selected_model_id,
                                temperature=temperature,
                                top_p=top_p,
                                max_tokens=max_tokens
                            )
                        else:
                            logger.info(f"Processing text request with model: {selected_model_id}")
                            response = glib.get_text_response(
                                prompt_content=prompt_text,
                                model_id=selected_model_id,
                                temperature=temperature,
                                top_p=top_p,
                                max_tokens=max_tokens
                            )
                        
                        # Hàm phát hiện và phân tích JSON
                        def is_json(text):
                            try:
                                # Regex để tìm JSON pattern
                                json_pattern = r'(\{[^{}]*(\{[^{}]*\}[^{}]*)*\})'
                                json_matches = re.findall(json_pattern, text)
                                
                                if json_matches:
                                    potential_json = json_matches[0][0]
                                    json.loads(potential_json)  # Kiểm tra nếu có thể parse
                                    return potential_json
                                return None
                            except (json.JSONDecodeError, IndexError):
                                return None
                        
                        # Xử lý và hiển thị kết quả
                        json_content = is_json(response)
                        
                        if json_content:
                            # Tách phần văn bản và phần JSON
                            non_json_part = response.replace(json_content, "")
                            if non_json_part.strip():
                                st.write(non_json_part)
                            
                            # Hiển thị JSON dưới dạng có cấu trúc
                            json_data = json.loads(json_content)
                            st.json(json_data)
                        else:
                            # Hiển thị văn bản thông thường
                            st.write(response)
                        
                except Exception as e:
                    logger.error(f"Error during processing: {str(e)}")
                    st.error(f"Đã xảy ra lỗi: {str(e)}")
                    if "AccessDeniedException" in str(e):
                        st.error("Kiểm tra IAM Role có đủ quyền truy cập vào Bedrock API và Knowledge Base")
                    elif "ResourceNotFoundException" in str(e):
                        st.error("Knowledge Base không tồn tại hoặc không khả dụng")
                    else:
                        st.error("Kiểm tra IAM Role có đủ quyền truy cập vào Bedrock Model")
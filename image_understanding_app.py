import streamlit as st
import image_understanding_lib as glib
import json
import re
import logging
import uuid
import os
from dotenv import load_dotenv
import base64

# Load environment variables
load_dotenv()

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cấu hình trang
st.set_page_config(layout="wide", page_title="Image Understanding")
st.title("Image Understanding")

# Định nghĩa CSS để tạo khung và styling
st.markdown("""
<style>
    .message-container {
        border: 1px solid #ccc;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 20px;
        background-color: #f9f9f9;
    }
    .user-message {
        background-color: #f0f7ff;
        border-left: 5px solid #4361ee;
    }
    .assistant-message {
        background-color: #f0fff4;
        border-left: 5px solid #4cc9a0;
    }
    .content-item {
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
        background-color: #ffffff;
    }
    .message-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .controls-container {
        background-color: #f0f0f0;
        border-radius: 5px;
        padding: 5px;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Dictionary chứa các model options
model_options_dict = {
    "Amazon Nova Premier": "us.amazon.nova-premier-v1:0",
    "Amazon Nova Pro": "apac.amazon.nova-pro-v1:0",
    "Amazon Nova Lite": "apac.amazon.nova-lite-v1:0",
    "Claude 3.5 Sonnet v2": "apac.anthropic.claude-3-5-sonnet-20241022-v2:0"
}

# Initialize session state
# Sửa phần khởi tạo session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": [
                {
                    "id": str(uuid.uuid4()),
                    "type": "image" if st.session_state.get("enable_rag", False) else "text",
                    "data": None if st.session_state.get("enable_rag", False) else ""
                }
            ]
        }
    ]

# Chia layout thành 3 cột
col1, col2, col3 = st.columns([1.5 , 3, 2.5])

# Cột 1: Cấu hình model và parameters
with col1:
    with st.container(border=True):
        st.subheader("Model Configuration")
        
        # Chọn model
        model_selection = st.selectbox(
            "Model:",
            options=list(model_options_dict.keys()),
            index=0,
        )
        selected_model_id = model_options_dict[model_selection]

        # Thêm sau phần Model Configuration
        with st.container(border=True):
            st.subheader("RAG Configuration")
            
            # RAG checkbox
            enable_rag = st.checkbox("Enable RAG Mode", key="enable_rag")
            
            if enable_rag:
                st.info("📸 RAG Mode requires uploading an image in Messages section")
                # Database selector với config từ .env
                db_options = {
                    "Planogram DB (Default)": {
                        "host": os.getenv("DB_HOST"),
                        "port": os.getenv("DB_PORT", "5432"),
                        "database": os.getenv("DB_NAME"),
                        "user": os.getenv("DB_USER"),
                        "password": os.getenv("DB_PASSWORD")
                    }
                }
                
                # Validate DB config
                default_db = db_options["Planogram DB (Default)"]
                if not all([default_db["host"], default_db["user"], default_db["password"]]):
                    st.error("⚠️ Database credentials not found in .env file!")
                    st.info("Please configure: DB_HOST, DB_USER, DB_PASSWORD")
                else:
                    selected_db = st.selectbox(
                        "Select Database:",
                        options=list(db_options.keys()),
                        key="selected_db"
                    )
                    st.session_state.db_config = db_options[selected_db]
                    
                    # Show connection status
                    if st.button("Test Connection", key="test_db"):
                        try:
                            import psycopg2
                            conn = psycopg2.connect(**st.session_state.db_config)
                            conn.close()
                            st.success("✅ Database connected successfully!")
                        except Exception as e:
                            st.error(f"❌ Connection failed: {str(e)}")


    with st.container(border=True):
        st.subheader("Inference Parameters")
        
        # Xác định loại model
        is_anthropic_model = "anthropic" in selected_model_id.lower()
        
        # Temperature - hiển thị cho cả hai loại model
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=glib.CLAUDE_DEFAULT_TEMPERATURE if is_anthropic_model else glib.NOVA_DEFAULT_TEMPERATURE,
            step=0.1,
            format='%.1f'
        )
        
        # Top P - hiển thị cho cả hai loại model nhưng với các tham số khác nhau
        top_p = st.slider(
            "Top P",
            min_value=0.1,
            max_value=1.0,
            value=glib.CLAUDE_DEFAULT_TOP_P if is_anthropic_model else glib.NOVA_DEFAULT_TOP_P,
            step=0.001 if is_anthropic_model else 0.1,
            format='%.3f' if is_anthropic_model else '%.1f'
        )
        
        # Top K - chỉ hiển thị cho Anthropic model
        top_k = st.slider(
            "Top K",
            min_value=1,
            max_value=500 if is_anthropic_model else 128,
            value=glib.CLAUDE_DEFAULT_TOP_K if is_anthropic_model else glib.NOVA_DEFAULT_TOP_K,
            step=1
        )
        
        # Max Tokens - hiển thị cho cả hai loại model
        max_tokens = st.slider(
            "Max Tokens",
            min_value=100,
            max_value=4000,
            value=glib.CLAUDE_DEFAULT_MAX_TOKENS if is_anthropic_model else glib.NOVA_DEFAULT_MAX_TOKENS,
            step=100
        )
    
    with st.container(border=True):
        st.subheader("System Prompt")
        system_prompt = st.text_area(
            "Enter system instructions:",
            height=500,
            help="Instructions that guide the model's behavior."
        )

# Cột 2: Messages và Content
with col2:
    with st.container(border=True):
        st.subheader("Messages")
        
        # Thêm hướng dẫn khi RAG mode
        if st.session_state.get("enable_rag", False):
            st.warning("⚠️ RAG Mode Active: Please upload an image to start")

        def create_rag_messages(best_match):
            """Create message structure for RAG"""
            description, ref_base64, inventory, distance = best_match
            
            # Clear existing messages except first
            st.session_state.messages = [st.session_state.messages[0]]
            
            # Add system message
            system_content = """## Task
        You are a Planogram Specialist for Uniben, a beverage company. Your task is to evaluate the planograms (product placement) in refrigerators containing Uniben's beverage products."""
            
            # Update system prompt in col1
            # (This needs to be handled via session state)
            
            # Add instruction message
            st.session_state.messages.append({
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": [{
                    "id": str(uuid.uuid4()),
                    "type": "text",
                    "data": """## Instructions
        Review the provided information about Uniben's beverage products:
        ### Uniben's Beverage Products
        - The refrigerator is yellow.
        - Yellow bottle with yellow cap is Boncha...
        [full instruction text]"""
                }]
            })
            
            # Add reference image
            st.session_state.messages.append({
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": [{
                    "id": str(uuid.uuid4()),
                    "type": "image",
                    "data": base64.b64decode(ref_base64)
                }]
            })
            
            # Add inventory response
            st.session_state.messages.append({
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "content": [{
                    "id": str(uuid.uuid4()),
                    "type": "text",
                    "data": inventory
                }]
            })
            
            # Final message already has the uploaded image
            # Just add the evaluation prompt
            for msg in st.session_state.messages:
                if msg["role"] == "user" and any(c["type"] == "image" for c in msg["content"]):
                    msg["content"].append({
                        "id": str(uuid.uuid4()),
                        "type": "text",
                        "data": """### Output Format
        The last refrigerator is the one you need to evaluate. Only give me back the response with the format like before, count from the bottom shelf to top, do not give me anything else."""
                    })
                    break
        
        # Function to add a new content item to a message
        def add_content_item(message_id):
            for i, msg in enumerate(st.session_state.messages):
                if msg["id"] == message_id:
                    st.session_state.messages[i]["content"].append({
                        "id": str(uuid.uuid4()),
                        "type": "text",
                        "data": ""
                    })
                    break
        
        # Function to add a new message
        def add_message():
            st.session_state.messages.append({
                "id": str(uuid.uuid4()),
                "role": "user",
                "content": [
                    {
                        "id": str(uuid.uuid4()),
                        "type": "text",
                        "data": ""
                    }
                ]
            })
        
        # Function to delete a message
        def delete_message(message_id):
            st.session_state.messages = [msg for msg in st.session_state.messages if msg["id"] != message_id]
        
        # Function to delete a content item
        def delete_content_item(message_id, content_id):
            for i, msg in enumerate(st.session_state.messages):
                if msg["id"] == message_id:
                    if len(msg["content"]) > 1:  # Don't delete the last content item
                        st.session_state.messages[i]["content"] = [
                            content for content in msg["content"] if content["id"] != content_id
                        ]
                    else:
                        st.warning("Không thể xóa content cuối cùng của message")
                    break
        
        # Function to update content data
        def update_content_data(message_id, content_id, data):
            for i, msg in enumerate(st.session_state.messages):
                if msg["id"] == message_id:
                    for j, content in enumerate(msg["content"]):
                        if content["id"] == content_id:
                            st.session_state.messages[i]["content"][j]["data"] = data
                            break
                    break
        
        # Function to update content type
        def update_content_type(message_id, content_id, content_type):
            for i, msg in enumerate(st.session_state.messages):
                if msg["id"] == message_id:
                    # Nếu role là assistant, không cho phép thay đổi content type
                    if msg["role"] == "assistant":
                        return
                        
                    for j, content in enumerate(msg["content"]):
                        if content["id"] == content_id:
                            if st.session_state.messages[i]["content"][j]["type"] != content_type:
                                st.session_state.messages[i]["content"][j]["type"] = content_type
                                # Reset data when changing type
                                if content_type == "image":
                                    st.session_state.messages[i]["content"][j]["data"] = None
                                else:
                                    st.session_state.messages[i]["content"][j]["data"] = ""
                            break
                    break
        
        # Function to update message role
        def update_message_role(message_id, role):
            for i, msg in enumerate(st.session_state.messages):
                if msg["id"] == message_id:
                    # Không cho phép thay đổi role của message đầu tiên
                    if i == 0:
                        return
                    st.session_state.messages[i]["role"] = role
                    # Nếu role là assistant, đảm bảo tất cả content type là text
                    if role == "assistant":
                        for j, content in enumerate(st.session_state.messages[i]["content"]):
                            if content["type"] != "text":
                                st.session_state.messages[i]["content"][j]["type"] = "text"
                                st.session_state.messages[i]["content"][j]["data"] = ""
                    break
        
        # Display all messages
        for msg_idx, message in enumerate(st.session_state.messages):
            # Create message container with appropriate styling based on role
            message_class = "user-message" if message["role"] == "user" else "assistant-message"
            
            with st.expander(f"Message {msg_idx+1}: {message['role'].capitalize()}", expanded=True):
                # Message header with role selector and delete button
                cols = st.columns([2, 3, 1.5])
                with cols[0]:
                    if msg_idx == 0:  # Message đầu tiên
                        st.text("Role: user")  # Chỉ hiển thị text, không cho phép thay đổi
                    else:
                        current_role_index = 0 if message["role"] == "user" else 1
                        new_role = st.selectbox(
                            "Role",
                            options=["user", "assistant"],
                            index=current_role_index,
                            key=f"role_{message['id']}"
                        )
                        
                        # Check and update if role has changed
                        if new_role != message["role"]:
                            update_message_role(message["id"], new_role)
                
                with cols[2]:
                    if msg_idx > 0:  # Chỉ hiển thị nút xóa cho message không phải đầu tiên
                        st.button("🗑️ Delete Message", key=f"delete_msg_{message['id']}", 
                                on_click=delete_message, args=(message["id"],))
                
                # Display all content items in this message
                st.markdown(f"##### Content Items ({len(message['content'])})")
                
                for content_idx, content in enumerate(message["content"]):
                    with st.container(border=True):
                        st.markdown(f"**Item {content_idx+1}**")
                        # Content item header
                        cont_cols = st.columns([2, 3, 1])
                                                
                        with cont_cols[0]:
                            if message["role"] == "assistant":
                                # Nếu role là assistant, content type phải là text
                                st.text("Content Type: text")
                            else:
                                current_type_index = 0 if content["type"] == "text" else 1
                                content_type = st.selectbox(
                                    "Content Type",
                                    options=["text", "image"],
                                    index=current_type_index,
                                    key=f"type_{content['id']}"
                                )
                                
                                # Check if content type has changed
                                if content_type != content["type"]:
                                    update_content_type(message["id"], content["id"], content_type)
                        
                        with cont_cols[2]:
                            st.button("🗑️ Delete", key=f"delete_content_{content['id']}", 
                                     on_click=delete_content_item, args=(message["id"], content["id"]))
                        
                        # Display appropriate input based on content type
                        if content["type"] == "text":
                            text_data = st.text_area(
                                "Text Content",
                                value=content["data"] if content["data"] is not None else "",
                                key=f"text_{content['id']}",
                                height=500
                            )
                            # Only update if data has changed
                            if text_data != content["data"]:
                                update_content_data(message["id"], content["id"], text_data)
                        elif content["type"] == "image":
                            uploaded_file = st.file_uploader(
                                "Upload Image",
                                type=['png', 'jpg', 'jpeg'],
                                key=f"image_{content['id']}"
                            )
                            
                            # Sửa phần upload image trong Messages
                            if uploaded_file:
                                try:
                                    image_bytes = uploaded_file.getvalue()
                                    update_content_data(message["id"], content["id"], image_bytes)
                                    
                                    # RAG auto-fill khi upload image
                                    if st.session_state.get("enable_rag", False) and st.session_state.get("db_config"):
                                        with st.spinner("Finding similar images..."):
                                            try:
                                                # Import check
                                                import image_understanding_lib as glib
                                                
                                                # Get embedding
                                                embedding, base64_img = glib.get_image_embedding(image_bytes)
                                                
                                                # Query similar images
                                                results = glib.query_similar_images(
                                                    embedding, 
                                                    st.session_state.db_config
                                                )
                                                
                                                if results and results[0][3] <= 0.1:  # High similarity
                                                    # Auto-create RAG messages
                                                    create_rag_messages(results[0])
                                                    st.success("✅ RAG messages created successfully!")
                                                    st.rerun()
                                                else:
                                                    st.warning("⚠️ No similar images found in database")
                                                    
                                            except ImportError as e:
                                                st.error(f"Import error: {str(e)}")
                                            except Exception as e:
                                                st.error(f"RAG error: {str(e)}")
                                                logger.error(f"RAG processing failed: {str(e)}", exc_info=True)
                                                
                                except Exception as e:
                                    st.error(f"File upload error: {str(e)}")  
                                              
                # Add content button
                st.button("➕ Add Content Item", key=f"add_content_{message['id']}", 
                         on_click=add_content_item, args=(message["id"],), use_container_width=False)
        
        # Add message button
        st.button("➕ Add New Message", on_click=add_message, use_container_width=False, type="primary")

# Cột 3: Process và Result
with col3:
    # Process button trong container riêng
    with st.container(border=True):
        st.subheader("Processing")
        process_button = st.button("Process", type="primary", use_container_width=True)
    
    # Result container
    with st.container(border=True):
        st.subheader("Result")
        
        if process_button:
            # Trong process_button handler
            if enable_rag:
                # Check có image không
                has_image = False
                for msg in st.session_state.messages:
                    if any(c["type"] == "image" and c["data"] for c in msg["content"]):
                        has_image = True
                        break
                
                if not has_image:
                    st.error("RAG Mode requires at least one image!")
                    st.stop()
            with st.spinner("Processing..."):
                try:
                    # Validate input - đảm bảo có ít nhất một message có nội dung
                    valid_messages = False
                    for msg in st.session_state.messages:
                        for content in msg["content"]:
                            if (content["type"] == "text" and content["data"] and content["data"].strip()) or \
                               (content["type"] == "image" and content["data"] is not None):
                                valid_messages = True
                                break
                        if valid_messages:
                            break
                    
                    if not valid_messages:
                        st.error("Vui lòng thêm nội dung text hoặc image vào ít nhất một message trước khi xử lý.")
                    else:
                        # Prepare data for processing
                        is_anthropic_model = "anthropic" in selected_model_id.lower()
                        
                        # Convert UI messages to API format
                        api_messages = []
                        for message in st.session_state.messages:
                            api_content = []
                            
                            for content_item in message["content"]:
                                # Xử lý text content
                                if content_item["type"] == "text" and content_item["data"] and content_item["data"].strip():
                                    if is_anthropic_model:
                                        api_content.append({
                                            "type": "text",
                                            "text": content_item["data"].strip()
                                        })
                                    else:  # Nova
                                        api_content.append({
                                            "text": content_item["data"].strip()
                                        })
                                # Xử lý image content
                                elif content_item["type"] == "image" and content_item["data"] is not None:
                                    image_bytes = content_item["data"]
                                    image_format = glib.detect_image_format(image_bytes)
                                    
                                    if is_anthropic_model:
                                        api_content.append({
                                            "type": "image",
                                            "source": {
                                                "type": "base64",
                                                "media_type": f"image/{image_format}",
                                                "data": glib.base64.b64encode(image_bytes).decode('utf-8')
                                            }
                                        })
                                    else:  # Nova
                                        api_content.append({
                                            "image": {
                                                "format": image_format,
                                                "source": {
                                                    "bytes": glib.base64.b64encode(image_bytes).decode('utf-8')
                                                }
                                            }
                                        })
                            
                            # Chỉ thêm message nếu nó có nội dung
                            if api_content:
                                api_messages.append({
                                    "role": message["role"],
                                    "content": api_content
                                })
                        
                        if not api_messages:
                            st.error("Không có message hợp lệ nào để xử lý.")
                        else:
                            # Process with the appropriate API
                            response = glib.process_conversation(
                                messages=api_messages,
                                model_id=selected_model_id,
                                system_prompt=system_prompt.strip() if system_prompt and system_prompt.strip() else None,
                                temperature=temperature,
                                top_p=top_p,
                                top_k=top_k,
                                max_tokens=max_tokens
                            )
                            
                           # Display response

                            # # Thử phát hiện và hiển thị JSON định dạng
                            try:
                                # Tìm chuỗi JSON bằng regex
                                json_matches = re.findall(r'\{.*\}', response, re.DOTALL)
                                if json_matches:
                                    for json_str in json_matches:
                                        try:
                                            json_obj = json.loads(json_str)
                                            st.code(json.dumps(json_obj, indent=2, ensure_ascii=False), language="json")
                                            break  # Chỉ hiển thị JSON đầu tiên tìm thấy
                                        except:
                                            continue
                            except Exception as e:
                                logger.error(f"Lỗi khi định dạng JSON: {str(e)}") 
                            
                            # Thông báo thành công
                            st.success("Xử lý thành công!")

                            st.subheader("Full response")
                            st.write(response)
                            
                
                except Exception as e:
                    logger.error(f"Error during processing: {str(e)}")
                    error_message = str(e)
                    
                    # Chi tiết hơn về lỗi
                    if "AccessDeniedException" in error_message:
                        st.error(f"Lỗi quyền truy cập: {error_message}")
                        st.error("Kiểm tra IAM Role có đủ quyền truy cập vào Bedrock API")
                    elif "ResourceNotFoundException" in error_message:
                        st.error(f"Model không tìm thấy: {error_message}")
                        st.error("Kiểm tra model ID và region có chính xác không")
                    elif "ValidationException" in error_message:
                        st.error(f"Lỗi định dạng dữ liệu: {error_message}")
                        st.error("Kiểm tra định dạng dữ liệu input")
                    elif "ServiceQuotaExceededException" in error_message:
                        st.error(f"Quá giới hạn quota: {error_message}")
                        st.error("Liên hệ AWS để tăng quota hoặc thử lại sau")
                    elif "ThrottlingException" in error_message:
                        st.error(f"Bị giới hạn tần suất gọi API: {error_message}")
                        st.error("Hãy thử lại sau một lúc")
                    else:
                        st.error(f"Đã xảy ra lỗi: {error_message}")







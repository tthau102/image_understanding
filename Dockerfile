FROM python:3.9-slim

WORKDIR /app

# Cài đặt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY image_understanding_lib.py .
COPY image_understanding_app.py .

# Cấu hình AWS credentials sẽ được mount từ máy host

# Port mặc định cho Streamlit
EXPOSE 8501

# Sửa lỗi port và đường dẫn
ENV PATH="/usr/local/bin:${PATH}"
CMD ["streamlit", "run", "image_understanding_app.py", "--server.address=0.0.0.0", "--server.port=8080"]

# docker run -p 8080:8080 -v ~/.aws:/root/.aws image-understanding-app
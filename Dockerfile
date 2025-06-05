FROM python:3.9-slim

WORKDIR /app

# Cài đặt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY *.py .

# Cấu hình AWS credentials sẽ được mount từ máy host

# Port mặc định cho Streamlit
EXPOSE 8080

# Tạo user không phải root
RUN addgroup --system appgroup && \
    adduser --system --group appuser && \
    chown -R appuser:appgroup /app

# Chuyển sang user không phải root
USER appuser

# Sửa lỗi port và đường dẫn
ENV PATH="/usr/local/bin:${PATH}"
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8080"]
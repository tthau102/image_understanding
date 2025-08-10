# 📊 Planogram Compliance Review System

Hệ thống review và quản lý dữ liệu hình ảnh với tích hợp Label Studio và AWS services.

## 🚀 Tính năng chính

- **🔍 Review Tab**: Xem và review hình ảnh từ database với 3 cột (tên ảnh, preview ảnh, kết quả phân tích)
- **📊 Label Studio Tab**: Upload ảnh lên S3, đồng bộ với Label Studio, và export annotations
- **🚀 Deploy Endpoint Tab**: Chọn folder từ S3 bucket và tạo endpoint thông qua Lambda function

## 📋 Yêu cầu hệ thống

### Python Dependencies
```
streamlit>=1.28.0
boto3>=1.26.0
psycopg2-binary>=2.9.0
pandas>=1.5.0
requests>=2.28.0
```

### AWS Services
- **S3**: Lưu trữ hình ảnh
- **Lambda**: Xử lý export annotations và tạo endpoint
- **RDS PostgreSQL**: Lưu trữ metadata và kết quả

### External Services
- **Label Studio**: Annotation platform

## 🛠️ Cài đặt và triển khai

### 1. Clone repository
```bash
git clone <repository-url>
cd image_understanding
```

### 2. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 3. Cấu hình AWS Credentials
Tạo file `~/.aws/credentials` hoặc set environment variables:
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=ap-southeast-1
```

### 4. Cấu hình ứng dụng
Copy và chỉnh sửa file config:
```bash
cp config_sample.py config.py
```

Chỉnh sửa `config.py`:
```python
# S3 Configuration
S3_BUCKET_NAME = "your-s3-bucket-name"
S3_REGION = "ap-southeast-1"

# PostgreSQL Database Configuration
DB_CONFIG = {
    "host": "your-db-host",
    "port": 5432,
    "database": "your-database-name",
    "user": "your-username",
    "password": "your-password",
}

# Table Configuration
DB_RESULT = "your_results_table_name"

# Label Studio Configuration
LABEL_STUDIO_API_TOKEN = "your-label-studio-token"
LABEL_STUDIO_BASE_URL = "https://your-labelstudio-url.com"
LABEL_STUDIO_PROJECT_ID = "your-project-id"
```

### 5. Thiết lập Database (Nếu dùng Onpremise)
Tạo bảng `results` trong PostgreSQL:
```sql
CREATE TABLE results (
    id SERIAL PRIMARY KEY,
    image_name VARCHAR(255) NOT NULL,
    s3_url TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    need_review BOOLEAN DEFAULT FALSE,
    review_comment TEXT,
    product_count JSONB,
    -- Thêm các cột khác theo nhu cầu
);
```

### 6. Chạy ứng dụng

#### Development
```bash
streamlit run app.py
```

#### Production với Docker
```bash
# Build image
docker build -t planogram-app .

# Run container
docker run -p 8080:8080 \
  -v ~/.aws:/home/appuser/.aws:ro \
  -e AWS_DEFAULT_REGION=ap-southeast-1 \
  planogram-app
```

## 🐳 Docker Deployment

### Build và run
```bash
# Build
docker build -t planogram-app .

# Run với AWS credentials
docker run -d \
  --name planogram \
  -p 8080:8080 \
  -v ~/.aws:/home/appuser/.aws:ro \
  -e AWS_DEFAULT_REGION=ap-southeast-1 \
  planogram-app
```

### Docker Compose
```yaml
version: '3.8'
services:
  planogram:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ~/.aws:/home/appuser/.aws:ro
    environment:
      - AWS_DEFAULT_REGION=ap-southeast-1
    restart: unless-stopped
```

## 🔍 Troubleshooting

### Lỗi kết nối Database
- Kiểm tra thông tin kết nối trong `config.py`
- Đảm bảo PostgreSQL đang chạy và accessible
- Kiểm tra firewall/security groups

### Lỗi AWS Credentials
- Kiểm tra AWS credentials: `aws sts get-caller-identity`
- Đảm bảo có quyền truy cập S3 và Lambda
- Kiểm tra region settings

### Lỗi Label Studio
- Kiểm tra API token và base URL
- Đảm bảo Label Studio project tồn tại
- Kiểm tra network connectivity
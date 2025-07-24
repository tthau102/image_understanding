# 📊 Planogram Compliance

Professional review system and Label Studio integration for planogram compliance analysis.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Docker (optional)
- AWS Account with S3 access
- Label Studio instance
- PostgreSQL database

### 1. Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd planogram-compliance

# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

### 2. Configure Environment Variables

Edit `.env` file with your settings:

```bash
# Database (for Review functionality)
DB_HOST=your-rds-endpoint.amazonaws.com
DB_PASSWORD=your-secure-password

# S3 Storage (for Image Upload)
S3_BUCKET_NAME=your-s3-bucket
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Label Studio Integration
LABEL_STUDIO_URL=http://your-labelstudio-server:8080
LABEL_STUDIO_API_TOKEN=your-api-token-here

# Lambda (for Export functionality)
LAMBDA_FUNCTION_NAME=your-export-lambda-function-name
```

### 3. Run Application

#### Option A: Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run application
streamlit run main.py --server.port 8080
```

#### Option B: Docker
```bash
# Build image
docker build -t planogram-compliance .

# Run container
docker run -d -p 8080:8080 \
  --env-file .env \
  --name planogram-app \
  planogram-compliance
```

#### Option C: Docker with AWS Credentials
```bash
# Run with AWS credentials from host
docker run -d -p 8080:8080 \
  -v ~/.aws:/home/appuser/.aws:ro \
  --env-file .env \
  --name planogram-app \
  planogram-compliance
```

### 4. Access Application

Open http://localhost:8080 in your browser.

## 📋 Features

### 🔍 Review Tab
- **Pending Items Dashboard**: View all items awaiting review
- **Search & Filter**: Find specific images quickly  
- **Image Preview**: Display images from S3 with presigned URLs
- **Analysis Results**: Show compliance status and product analysis
- **Statistics**: Overview of pass/fail rates and comments

### 📥 Import & Processing Tab
- **Project Selection**: Choose Label Studio project visually
- **Image Upload**: Upload multiple images (PNG, JPG, JPEG)
- **Automatic Import**: Upload to S3 + sync with Label Studio
- **Export Labels**: Trigger Lambda function for annotation export

## 🏗️ Architecture

```
planogram-compliance/
├── app/
│   ├── config.py              # Environment-based configuration
│   ├── services/
│   │   ├── data_ops.py        # Database, S3, Lambda services
│   │   ├── labelstudio_service.py  # Label Studio API integration
│   │   └── storage_service.py # Image processing workflow
│   └── utils/
│       └── validators.py      # Image validation utilities
├── assets/
│   └── styles.css            # Custom styling (if needed)
├── scripts/
│   ├── deploy.sh             # Deployment script
│   └── docker_rollout.sh     # Docker deployment
├── main.py                   # Main Streamlit application
├── Dockerfile               # Container configuration
├── .env.example            # Environment template
└── requirements.txt        # Python dependencies
```

## 🔧 Configuration

### Database Setup
Ensure your PostgreSQL database has the `results` table:

```sql
CREATE TABLE results (
    id SERIAL PRIMARY KEY,
    image_name VARCHAR(255),
    s3_url TEXT,
    product_count JSONB,
    compliance_assessment BOOLEAN,
    review_comment TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### S3 Bucket Setup
1. Create S3 bucket in your AWS region
2. Configure CORS for direct uploads:

```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": ["x-amz-server-side-encryption", "x-amz-request-id", "x-amz-id-2"],
        "MaxAgeSeconds": 3600
    }
]
```

3. Set appropriate IAM permissions for your AWS credentials

### Label Studio Setup
1. Get your API token from Label Studio (Account → Access Token)
2. Ensure your Label Studio instance is accessible from the application
3. Create projects for image annotation

## 🐳 Docker Deployment

### Build and Deploy
```bash
# Build image
docker build -t planogram-compliance:latest .

# Deploy with environment file
docker run -d \
  --name planogram-compliance \
  -p 8080:8080 \
  --env-file .env \
  --restart unless-stopped \
  planogram-compliance:latest
```

### Production Deployment
```bash
# Use deployment script
chmod +x scripts/docker_rollout.sh
./scripts/docker_rollout.sh
```

## 🔒 Security

- ✅ Environment-based configuration (no hardcoded secrets)
- ✅ Non-root container user  
- ✅ Presigned URLs for secure S3 access
- ✅ Input validation for all uploads
- ✅ Error handling and logging

## 📊 Monitoring

### Health Check
```bash
# Check application health
curl http://localhost:8080/_stcore/health
```

### Logs
```bash
# View container logs
docker logs planogram-compliance

# Follow logs
docker logs -f planogram-compliance
```

## 🛠️ Development

### Local Development Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run in debug mode
DEBUG=true streamlit run main.py
```

### Code Structure
- **Services**: Business logic and external integrations
- **Utils**: Shared utilities and validators  
- **Components**: UI components (for future modularization)
- **Config**: Centralized configuration management

## 📈 Performance

### Recommended Limits
- **Images per batch**: ≤ 50 images for optimal performance
- **File size**: ≤ 200MB per image
- **Supported formats**: PNG, JPG, JPEG

### Scaling Considerations
- Use load balancer for multiple instances
- Consider Redis for session state in multi-instance setup
- Monitor S3 costs and implement lifecycle policies

## 🔍 Troubleshooting

### Common Issues

**1. Database Connection Error**
```bash
# Check database connectivity
psql -h $DB_HOST -U $DB_USER -d $DB_NAME
```

**2. S3 Access Denied**
```bash
# Verify AWS credentials
aws s3 ls s3://$S3_BUCKET_NAME
```

**3. Label Studio API Error**
```bash
# Test API connection
curl -H "Authorization: Token $LABEL_STUDIO_API_TOKEN" \
     $LABEL_STUDIO_URL/api/projects
```

**4. Lambda Function Not Found**
```bash
# List Lambda functions
aws lambda list-functions --query 'Functions[].FunctionName'
```

### Debug Mode
Set `DEBUG=true` in `.env` for detailed logging and error messages.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**📞 Support**: For issues or questions, please create an issue in the repository.
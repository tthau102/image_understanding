#!/bin/bash

# Default branch là branch hiện tại
branch=$(git rev-parse --abbrev-ref HEAD)

if [ -n "$1" ]; then
    branch="$1"
    # Chuyển sang branch được chỉ định nếu khác với branch hiện tại
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    if [ "$current_branch" != "$branch" ]; then
        echo "Switching to branch: $branch"
        git checkout $branch || { echo "Failed to checkout $branch"; exit 1; }
    fi
fi

# Lấy danh sách các file đã thay đổi
changed_files=$(git diff --name-only --cached)

# Lấy nội dung thay đổi
diff_content=$(git diff)

# Giới hạn kích thước diff để tránh vượt quá giới hạn token
diff_content=$(echo "$diff_content" | head -c 10000)

# Prompt được cải tiến để Claude chỉ trả về commit message text
prompt=$(cat <<EOF
Trả về chính xác một dòng commit message dựa trên các thay đổi sau đây. Không thêm bất kỳ giải thích hay nội dung phụ nào:

Các file đã thay đổi:
$changed_files

Chi tiết thay đổi:
$diff_content

Quy tắc:
- Chỉ trả về MỘT DÒNG duy nhất
- Bắt đầu bằng động từ hành động (Add, Update, Fix, Refactor, etc.)
- Ngắn gọn, không quá 72 ký tự
- Không thêm dấu ngoặc kép hoặc bất kỳ định dạng nào khác
- Không bao gồm chú thích hoặc giải thích
- Nếu code không có thay đổi. Hãy trả về "No change"
EOF
)

# Tạo file request tạm thời
request_file=$(mktemp)
response_file=$(mktemp)

cat > "$request_file" << EOF
{
  "anthropic_version": "bedrock-2023-05-31",
  "max_tokens": 100,
  "messages": [
    {
      "role": "user",
      "content": $(echo "$prompt" | jq -Rs .)
    }
  ]
}
EOF

# Gọi Amazon Bedrock API
if aws bedrock-runtime invoke-model \
    --model-id apac.anthropic.claude-3-5-sonnet-20241022-v2:0 \
    --body file://$request_file \
    --cli-binary-format raw-in-base64-out \
    --region ap-southeast-1 \
    "$response_file"; then

    # Trích xuất commit message từ response
    commit_message=$(cat "$response_file" | jq -r '.content[0].text' 2>/dev/null)
    
    # Đảm bảo commit message chỉ có một dòng
    commit_message=$(echo "$commit_message" | tr -d '\n' | tr -d '\r')
    
    # Kiểm tra commit message
    if [ -z "$commit_message" ] || [ "$commit_message" = "null" ]; then
        exit
    fi
else
    exit
fi

# Xóa các file tạm
rm -f "$request_file" "$response_file"

echo "Commit message: $commit_message"

# Thực hiện commit và push
git add .
git commit -m "$commit_message"
git push -u origin $branch --force

echo "Changes pushed to $branch branch"
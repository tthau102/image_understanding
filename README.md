# image_understanding
streamlit run image_understanding_app.py --server.port 8080 --server.enab
leXsrfProtection=false

# Docker Run
docker run -dt -p 80:8080 -v ~/.aws:/root/.aws --name image-understanding-app-tokyo image-understanding-app
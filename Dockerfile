FROM python:3.11
# Expose port
EXPOSE 8080
# Set work dir
WORKDIR /app

# Update pip
RUN pip install --upgrade pip

# Copy and install dependencies
COPY . ./
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Define an entrypoint
ENTRYPOINT ["streamlit", "run", "predict.py", "--server.port=8080", "--server.address=0.0.0.0"]
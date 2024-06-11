FROM python:3.11

# Update pip
RUN pip install --upgrade pip

# Copy and install dependencies
COPY ./requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt
FROM python:alpine

# Set working directory
WORKDIR /app

# Install dependencies
RUN apk add --no-cache postgresql-libs gcc python3-dev musl-dev postgresql-dev

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Run the data population script
CMD ["python", "populate_data.py"]

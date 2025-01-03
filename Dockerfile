FROM python:3.12-slim

# 1. Create a working directory
WORKDIR /app

# 2. Copy your local requirements.txt
COPY requirements.txt .

# 3. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy your app source code
COPY . .

# 5. Expose the port that your app listens on (e.g., 8501 for Streamlit)
EXPOSE 8501

# 6. Specify the command to run your app
CMD ["streamlit", "run", "mongo_dba_script.py", "--server.port=8501", "--server.address=0.0.0.0"]

# Start from the official Ollama image
FROM ollama/ollama:latest

# Set up a working directory inside the container
WORKDIR /app

# Install Python and Pip, which are needed to run our backend
RUN apt-get update && apt-get install -y python3 python3-pip

# Copy the Python requirements file first
COPY ./requirements.txt .

# Install all of our Python dependencies, bypassing the system protection
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Now, copy the rest of our backend application code
COPY ./app ./app
COPY ./start.sh .

# Make our startup script executable
RUN chmod +x /app/start.sh

# Tell Docker that our application will listen on port 8080
EXPOSE 8080

# THE FIX: Set our script as the main command for the container
ENTRYPOINT ["/app/start.sh"]
# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
# (Make sure to create a requirements.txt file if you haven't)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir python-telegram-bot==20.* requests nest_asyncio

# Make port 8443 available to the world outside this container
EXPOSE 8443

# Run sumsub_bot.py when the container launches
CMD ["python", "sumsub_bot.py"]

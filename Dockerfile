FROM python:3.9-slim-buster
WORKDIR /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# Expose port 80
EXPOSE 80

# Run the command to start the Flask app
CMD ["python", "app.py"]

# docker run -p 8080:80 -v /home/$USER/Downloads/temp:/data -it iap-tema2
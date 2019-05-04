FROM python:2.7-slim

WORKDIR /twitter

COPY . /twitter

RUN pip install -r requirements.txt

# Make port 80 available to the world outside this container
#EXPOSE 80

# Run Twitter script
CMD ["python", "twitterScript.py"]

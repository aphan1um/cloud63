FROM python:3.6-slim

WORKDIR /twitter

COPY twitterutils.py /twitter
COPY twitterscript.py /twitter
COPY requirements.txt /twitter

RUN pip install -r requirements.txt

# Make port 80 available to the world outside this container
#EXPOSE 80

# Run Twitter script
CMD ["python", "-u", "twitterscript.py"]

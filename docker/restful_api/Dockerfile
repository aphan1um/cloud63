FROM python:3.6-slim

WORKDIR /restapi

COPY flask_server.py /restapi
COPY requirements.txt /restapi

RUN pip install -r requirements.txt

# Flash restful API server incoming port
EXPOSE 5000

# Run Twitter script
CMD ["python", "-u", "flask_server.py"]

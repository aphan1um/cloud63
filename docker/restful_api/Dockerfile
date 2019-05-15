#
# For Cloud Team 63:
#  * Akshaya Shankar - 1058281
#  * Andy Phan - 696382
#  * Chenbang Huang - 967186
#  * Prashanth Shrinivasan - 986472
#  * Qian Sun – 1027266
#

FROM python:3.6-slim

WORKDIR /restapi

COPY flask_server.py /restapi
COPY requirements.txt /restapi

RUN pip install -r requirements.txt

# Flash restful API server incoming port
EXPOSE 5000

# Run Twitter script
CMD ["python", "-u", "flask_server.py"]

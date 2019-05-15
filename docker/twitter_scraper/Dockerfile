#
# For Cloud Team 63:
#  * Akshaya Shankar - 1058281
#  * Andy Phan - 696382
#  * Chenbang Huang - 967186
#  * Prashanth Shrinivasan - 986472
#  * Qian Sun – 1027266
#

FROM python:3.6-slim

WORKDIR /twitter

COPY twitterutils.py /twitter
COPY twitterscript.py /twitter
COPY twitterdoc.py /twitter
COPY requirements.txt /twitter
COPY state_shapes.7z /twitter

RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y p7zip-full
RUN 7z x state_shapes.7z

EXPOSE 5000

# Run Twitter script
CMD ["python", "-u", "twitterscript.py"]

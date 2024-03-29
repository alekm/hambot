FROM python:3.10

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN python3 -m pip install -U --no-cache-dir -r requirements.txt
RUN apt update && apt install -y librsvg2-bin

COPY . .

CMD [ "python", "./hambot.py" ]

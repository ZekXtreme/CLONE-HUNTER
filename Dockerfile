FROM arata74/clone:latest

COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY . .

CMD ["bash","start.sh"]
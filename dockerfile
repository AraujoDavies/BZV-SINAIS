FROM python:3.11.10

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

ENV TZ=America/Sao_Paulo

# CMD [ "python", "entradas.py" ]
# # CMD [ "python", "routine.py" ]
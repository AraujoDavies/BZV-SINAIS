FROM python

WORKDIR /blzebra

COPY . .

RUN pip install -r requeriments.txt

ENV TZ=America/Sao_Paulo

CMD [ "python", "routine.py" ]
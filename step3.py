# Avisar no telegram se tem algum padrão e monitorar resultado final
import logging
from helper_sql import db_mysql
from sqlalchemy import text
from os import getenv
from dotenv import load_dotenv
from helper_telegram import enviar_no_telegram, chat_id, app, resultado_da_entrada
from api_betfair import api_betfair

load_dotenv('config.env')

def enviar_entrada_no_telegram():
    """
        3.1 - Enviar sinal no telegram
    """
    # Faça select na entradas q tenham 'evento_em_andamento' = 1 e 'id_telegram' = NULL
    logging.warning('3.1 - fazendo select para sinal no telegram...')
    s_comando = "select market_id, mandante, visitante, tempo, odd, campeonato, mercadoSelecionado from sinais where evento_em_andamento = '1' and id_telegram IS NULL;"
    engine = db_mysql()
    with engine.begin() as c:
        sinais = c.execute(text(s_comando)).fetchall()

    # Enviando sinais
    if bool(sinais):
        for sinal in sinais:
            logging.warning('3.1 - Enviando sinal no telegram...')
            
            market_id = str(sinal[0])
            mandante = str(sinal[1])
            visitante = str(sinal[2])
            tempo = str(sinal[3])
            odd = str(sinal[4])
            campeonato = str(sinal[5])
            mercado_selecionado = str(sinal[6])

            # Se mandante for a zebra
            if mercado_selecionado == "0":
                back_ao = mandante

            # Se visitante for a zebra
            elif mercado_selecionado == "1":
                back_ao = visitante

            msg = getenv('SINAL').replace(
                '{mandante}', mandante).replace(
                    '{visitante}', visitante).replace(
                '{tempo}', tempo).replace('{odd}', odd).replace(
                '{campeonato}', campeonato).replace("{back_ao}", back_ao)

            id_telegram = enviar_no_telegram(chat_id, msg)

            # Update coluna do telegram usando market_id
            u_comando = f"""UPDATE sinais
    SET id_telegram = '{id_telegram}'
    WHERE market_id = '{market_id}';"""

            with engine.begin() as c:
                c.execute(text(u_comando))


def att_resultado():
    """
        3.2 - última tarefa... atualizar coluna resultado no DB, indicando se foi green ou red.
    """
    logging.warning('3.2 - fazendo select para API da BETFAIR...')
    comando = "SELECT market_id, id_telegram, mercadoSelecionado FROM sinais WHERE evento_em_andamento = 1 AND id_telegram IS NOT NULL AND resultado IS NULL;"
    engine = db_mysql()
    with engine.begin() as c:
        resultados_para_att = c.execute(text(comando)).fetchall()

    if bool(resultados_para_att):
        logging.warning(f'3.2 - Encontrou {len(resultados_para_att)} para att...')
        for result in resultados_para_att:
            market_id = result[0]
            reply_msg_id = result[1]
            selecao = result[2]

            logging.warning('3.2 - buscando dados na API da betfair')
            mercado_na_api = api_betfair(market_id)
            status = mercado_na_api['result'][0]['status'] # OPEN / CLOSED
            status_da_zebra = mercado_na_api['result'][0]['runners'][selecao]['status'] # WINNER / LOSER / ACTIVE

            # Se mercado está fechado(jogo acabou)
            if status == "CLOSED":
                logging.warning('3.2 - Enviando resultado da entrada no telegram...')
                if status_da_zebra == "WINNER":
                    msg = f'✅ GREEN ✅'
                    resultado_db = 'green'
                    app.run(
                        resultado_da_entrada(
                        int(getenv('TELEGRAM_CHAT_ID')), reply_msg_id, msg
                        )
                    )
                # se RED
                else:
                    msg = f"❌ RED ❌"
                    resultado_db = 'red'
                    app.run(
                        resultado_da_entrada(
                            int(getenv('TELEGRAM_CHAT_ID')), reply_msg_id, msg
                        )
                    )
                # database
                comando = f"""UPDATE sinais
SET resultado = '{resultado_db}', evento_em_andamento = '0'
WHERE market_id = '{market_id}';"""

                logging.warning(f'3.2 - SQL: {comando}')

                with engine.begin() as c:
                    c.execute(text(comando))
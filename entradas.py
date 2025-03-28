import logging
from sqlalchemy import text

from time import sleep
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

from helper_browser import meu_browser
from helper_sql import db_mysql
from step1 import acessa_betfair
from helper_telegram import enviar_no_telegram
from sync_db import gsheet_sync

SQL_CONSULTA_SINAL = """
SELECT market_id, mercadoSelecionado FROM sinais WHERE entradaProposta = 'N' AND resultado IS NULL AND campeonato IN (SELECT campeonato FROM (SELECT 
    campeonato,
    SUM(CASE WHEN resultado = 'green' THEN 1 ELSE 0 END) AS qt_green,
    SUM(CASE WHEN resultado = 'red' THEN 1 ELSE 0 END) AS qt_red,
    IFNULL(SUM(CASE WHEN resultado = 'green' THEN 1 ELSE 0 END) /
    NULLIF(SUM(CASE WHEN resultado = 'red' THEN 1 ELSE 0 END), 0), SUM(CASE WHEN resultado = 'green' THEN 1 ELSE 0 END)) AS acima_quatro_e_lucrativo
FROM 
    sinais
GROUP BY 
    campeonato
HAVING 
    acima_quatro_e_lucrativo >= 4
    ) campeonatos_lucrativos
) ORDER BY data_raspagem DESC LIMIT 1;
"""

CHAT_ID = '-1002294019228'

# log_name = './logs/entradas'
# log_name += datetime.now().strftime('%d%m')
# log_name += '.log'

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    encoding='utf-8',
    format='%(asctime)s - %(levelname)s: %(message)s',
)


def meu_saldo(b) -> float | str:
    """
        Args: 
            Browser(__splinter__)

        returns:
            valor do saldo (__float__)

            ERRO (__str__)
    """
    saldo_xpath = '//tr[@rel="main-wallet"]//td[@rel="main"]'
    existe_saldo = b.is_element_present_by_xpath(saldo_xpath, wait_time=20)
    if bool(existe_saldo) == False:
        return 'ERRO AO OBTER MEU SALDO'
    saldo = b.find_by_xpath(saldo_xpath).text
    saldo = saldo.split(' ')[-1]
    try:
        saldo = float(saldo)
    except ValueError:
        sleep(5)
        existe_saldo = b.is_element_present_by_xpath(saldo_xpath, wait_time=20)
        saldo = b.find_by_xpath(saldo_xpath).text
        saldo = saldo.split(' ')[-1]
        saldo = float(saldo)
    return saldo


def propor_entrada_a125(b, market_id, mercado_selecionado, valor_apostado):
    """
        Propoe entrada a @1.25

        Args: 
            Browser (__splinter__)
            url (__str__) -> url do evento
            mercado_selecionado (__int__) -> 0 (quando zebra mandante) | 1 (quando zebra visitante)
            valor_apostado (__float__) -> quanto será apostado

        Returns:
            Quando entrada proposta -> True (__bool__)

            Quando entrada proposta Cancelada -> False (__bool__)
    """
    url = "https://www.betfair.com/exchange/plus/football/market/" + market_id
    b.visit(url)
    x = 0
    while True:
        x += 1 # a cada 3s recarrega
        # logging.warning('URL Atual: %s', b.url)
        if market_id in b.url:
            break
        sleep(1)
        if x % 5 == 0: b.visit(url)

    carregou_site = b.is_element_present_by_xpath('//td[contains(@class, "last-back-cell")]', wait_time=90)
    if bool(carregou_site) == False:
        logging.error('Falha ao carregar site...')
        with engine.begin() as c:
            c.execute(text(f"UPDATE sinais SET entradaProposta = 'S' WHERE market_id = '{market_id}';"))
        return False
    sleep(1)

    banca = meu_saldo(b)
    logging.warning('Valor da banca: %s', banca)

    # click na odd do mercado da zebra
    try:
        odd_back = b.find_by_xpath('//td[contains(@class, "last-back-cell")]')[mercado_selecionado].text.split('\n')[0]
        odd_back = float(odd_back)
    except:
        odd_back = 50

    if odd_back > 1.5:
        logging.error('ODD Back MUITO maior que o esperado: %s', odd_back)
        return False
    
    b.find_by_xpath('//td[contains(@class, "last-back-cell")]')[mercado_selecionado].click()
    # propoe a odd de 1.25
    b.find_by_xpath('//div[@class="betslip-price-ladder"]//input').fill('1.25')
    # preenche valor da aposta
    b.find_by_xpath('//betslip-size-input//input').fill(valor_apostado)
    b.find_by_xpath('//ours-button[@button-type="submit"]').click()
    sleep(2)
    b.find_by_xpath('//ours-button[@button-type="submit"]').click()

    # checar se foi correspondido
    logging.warning('Aguardando aposta ser correspondida...')
    correspondida = b.is_element_present_by_xpath('//div[@class="cashout-liability-value"]', wait_time=45)
    if correspondida == True:
        risco = b.find_by_xpath('//div[@class="cashout-liability-value"]').first
        risco = risco.text.replace('R$', '')
        logging.warning('Aposta correspondida. Risco: %s', risco)

        with engine.begin() as c:
            c.execute(text(f"UPDATE sinais SET entradaProposta = 'S' WHERE market_id = '{market_id}';"))
            partida = c.execute(text(f"select CONCAT(mandante, ' X ', visitante) from sinais where market_id = '{market_id}';")).fetchall()
            partida = partida[0][0]
            insert_entrada = f"""INSERT INTO `projeto_back_zebra`.`entradas` 
(`market_id`, `data`, `banca`, `partida`, `stake`, `stake_correspondida`)
VALUES
('{market_id}', NOW(), '{banca}', '{partida}', '{valor_apostado}', '{risco}')
"""
            c.execute(text(insert_entrada))

        return True
    else:
        # cancela aposta
        logging.warning('Aposta não correspondeu, cancelando entrada.')
        try:
            b.find_by_xpath('//span[@class="receipt-footer__cancel-unmatched"]').click()
            logging.warning('Aposta cancelada!')
        except:
            logging.error('Falha ao clicar no botão de cancelar entrada D:')

    return False


def atualizar_stake_control(market_id):
    try:
        while True: # espera evento terminar
            logging.warning('esperando evento terminar...')
            with engine.begin() as c:
                evento_acabou = c.execute(text(f'SELECT * FROM sinais where market_id = "{market_id}" and resultado IS NOT NULL;')).fetchall()
                if bool(evento_acabou) == True:
                    break
            sleep(300)

        with engine.begin() as c:
            dados = c.execute(text(f"SELECT banca, pl FROM entradas WHERE market_id = {market_id};")).fetchall()
            banca_ini = dados[0][0]
            pl = dados[0][1]
        
        if pl == None: # se nao tem PL, atualize
            b = meu_browser()
            acessa_betfair(b)
            banca_now = meu_saldo(b)
            b.quit()
            banca_ini = float(banca_ini)

            pl = (banca_ini - banca_now) * -1

            with engine.begin() as c:
                c.execute(text(f"UPDATE entradas SET pl = {pl}, banca_final = {banca_now} WHERE market_id = {market_id};"))
                stake_info = c.execute(text("SELECT stake_base, stake_atual FROM stake_control WHERE id = 1;")).fetchall()
                stake_base = stake_info[0][0]
                stake_atual = stake_info[0][1]
                nova_stake_atual = stake_atual + pl

                # se green e nao dobrou a stake ainda...
                if pl > 0 and nova_stake_atual < stake_base * 2: # atualizar stake
                    c.execute(text(f"UPDATE stake_control SET stake_atual = {nova_stake_atual}, banca = {banca_now}, update_datetime = NOW() WHERE id = 1;"))
                else: # stake atual reseta
                    c.execute(text(f"UPDATE stake_control SET stake_atual = {stake_base}, banca = {banca_now}, update_datetime = NOW() WHERE id = 1;"))
    
        return True
    except:
        return False


def atualizar_stake_control_ciclos(market_id):
    try:
        while True: # espera evento terminar
            logging.warning('esperando evento terminar...')
            with engine.begin() as c:
                evento_acabou = c.execute(text(f'SELECT * FROM sinais where market_id = "{market_id}" and resultado IS NOT NULL;')).fetchall()
                if bool(evento_acabou) == True:
                    break
            sleep(300)

        with engine.begin() as c:
            dados = c.execute(text(f"SELECT banca, pl FROM entradas WHERE market_id = {market_id};")).fetchall()
            banca_ini = dados[0][0]
            pl = dados[0][1]
        
        if pl == None: # se nao tem PL, atualize
            b = meu_browser()
                    
            timeout = 0
            logou = acessa_betfair(b)
            while logou == False:
                logou = acessa_betfair(b)
                timeout += 1
                if timeout > 3:
                    logging.critical('Várias tentativas de login falharam')
                    break

            banca_now = meu_saldo(b)
            b.quit()
            banca_ini = float(banca_ini)

            pl = (banca_ini - banca_now) * -1

            with engine.begin() as c:
                # Inserir dados na tabela de entradas
                c.execute(text(f"UPDATE entradas SET pl = {pl}, banca_final = {banca_now} WHERE market_id = {market_id};"))
                
                # atualizar valor para próxima entrada
                stake_info = c.execute(text("SELECT stake_base, stake_atual, qual_ciclo, qual_entrada_do_ciclo FROM stake_control WHERE id = 1;")).fetchall()
                stake_base = stake_info[0][0]
                stake_atual = stake_info[0][1]
                qual_ciclo = stake_info[0][2]
                qual_entrada_do_ciclo = stake_info[0][3]
                nova_stake_atual = stake_atual + pl

            status_envio = enviar_resultado_telegram(market_id)
            logging.warning('Enviou no telegram: %s', status_envio) 
            
            if pl > 0: # se foi green - enviar msg e ajustar o ciclo
                sleep(10)

                # atualizar stake_atual, qual_ciclo, qual_entrada_do_ciclo, banca
                if qual_entrada_do_ciclo < 3:
                    qual_entrada_do_ciclo += 1
                else:
                    qual_entrada_do_ciclo = 1
                    qual_ciclo += 1
                    if qual_ciclo == 2:
                        nova_stake_atual = stake_base
                    elif qual_ciclo == 3:
                        nova_stake_atual = stake_base * 2
                    elif qual_ciclo == 4:
                        nova_stake_atual = stake_base * 4
                    elif qual_ciclo == 5:
                        nova_stake_atual = stake_base * 8
                    else: 
                        nova_stake_atual = stake_base
                        qual_ciclo = 1

                update_stake_control = f"UPDATE stake_control SET stake_atual = {nova_stake_atual}, banca = {banca_now}, qual_ciclo = {qual_ciclo}, qual_entrada_do_ciclo = {qual_entrada_do_ciclo}, update_datetime = NOW() WHERE id = 1;"
            else: # se red - resetar o ciclo
                update_stake_control = f"UPDATE stake_control SET stake_atual = {stake_base}, banca = {banca_now}, qual_ciclo = 1, qual_entrada_do_ciclo = 1, update_datetime = NOW() WHERE id = 1;"

            with engine.begin() as c:
                c.execute(text(update_stake_control))

        return True
    except:
        return False


def enviar_entrada_em_andamento(market_id):
    try:
        with engine.begin() as c:
            dados_msg = c.execute(text(f"select partida from entradas where market_id = '{market_id}';")).fetchall()

        partida = dados_msg[0][0]

        msg = f"""
❗️❗️🦓 ENTRADA EM ANDAMENTO
❗️❗️🦓 {partida}
"""

        id_telegram = enviar_no_telegram(CHAT_ID, msg)

        return id_telegram
    except:
        return 'ERRO ao enviar resultado no telegram'
 

def enviar_resultado_telegram(market_id):
    try:
        with engine.begin() as c:
            dados_msg = c.execute(text(f"select partida, stake, pl from entradas where market_id = '{market_id}';")).fetchall()
            stake_info = c.execute(text("SELECT qual_ciclo, qual_entrada_do_ciclo FROM stake_control WHERE id = 1;")).fetchall()
        
        qual_ciclo = stake_info[0][0]
        qual_entrada_do_ciclo = stake_info[0][1]

        partida = dados_msg[0][0]
        stake = dados_msg[0][1]
        pl = dados_msg[0][2]

        if pl > 0:
            msg = f"""
❗️❗️🦓 {partida} 🦓❗️❗️

Stake: {stake} 💰
Resultado: {pl} ✅

Ciclo: {qual_ciclo} ({qual_entrada_do_ciclo}° entrada do ciclo)
"""
        else:
            msg = f"""
❗️❗️🦓 {partida} 🦓❗️❗️

Stake: {stake} 💰
Resultado: {pl} ❌

Quebrou no ciclo {qual_ciclo}
"""

        id_telegram = enviar_no_telegram(CHAT_ID, msg)

        return id_telegram
    except:
        return 'ERRO ao enviar resultado no telegram'


def atualizando_gsheet():
    logging.warning('atualizando entradas')

    # id_telegram = enviar_no_telegram(CHAT_ID, 'ON ON ON')
    with engine.begin() as c:
        todas_entradas = c.execute(text('SELECT * FROM entradas;')).fetchall()

    df = pd.DataFrame(todas_entradas, dtype='str')

    # converter em float
    for column in ['banca', 'stake', 'pl', 'banca_final']:
        df[column] = df[column].map(lambda x: float(x))

    # ajuste data
    df['data'] = df['data'].map(lambda x: x.split()[0])
    status_sync = gsheet_sync(df)

    logging.warning('status sync: %s', status_sync)


# sleep(30)
engine = db_mysql()
logging.warning('DB ON...')
# market_id = '1.236092576'
# mercado_selecionado = 0
# valor_apostado = 5
# enviar_resultado_telegram('1.240632910')
# import sys
# sys.exit()

try:
    atualizando_gsheet()
except:
    pass


logging.warning('APP ON...')
while True:
    try:
        with engine.begin() as c:
            market = c.execute(text(SQL_CONSULTA_SINAL)).fetchall()
            if bool(market):
                stake = c.execute(text("SELECT stake_atual FROM stake_control WHERE id = 1;")).fetchall()

        if bool(market):
            logging.warning('Encontrou entrada...')
            b = meu_browser(enable_video=True)
            
            timeout = 0
            logou = acessa_betfair(b)
            banca_now = meu_saldo(b)
            logging.info('saldo: %s', banca_now)
            while type(banca_now) != float:
                logou = acessa_betfair(b)
                banca_now = meu_saldo(b)
                logging.info('saldo: %s', banca_now)
                timeout += 1
                if timeout > 3:
                    logging.critical('Várias tentativas de login falharam')
                    break

            market_id = market[0][0]
            mercado_selecionado = market[0][1]
            valor_apostado = stake[0][0]

            logging.warning('Propondo entrada...')
            apostou = propor_entrada_a125(b, market_id, mercado_selecionado, valor_apostado)
            logging.warning('Entrada proposta: %s', apostou)

            if apostou == True: # espera o evento acabar e atualiza PL + stake control
                try: # fecha o browser
                    b.quit()
                except: 
                    pass

                enviar_entrada_em_andamento(market_id)

                while True:
                    atualizou = atualizar_stake_control_ciclos(market_id)
                    if atualizou == True:
                        logging.warning('Atualizou stake control')
                        # status_envio = enviar_resultado_telegram(market_id)
                        # logging.warning('Enviou no telegram: %s', status_envio)
                        atualizando_gsheet()
                        break
            else:
                try: # fecha o browser
                    b.quit()
                    # cancelar entrada
                    with engine.begin() as c:
                        c.execute(text(f"UPDATE sinais SET entradaProposta = 'S' WHERE market_id = '{market_id}';"))
                except: 
                    pass

        sleep(5)
    except Exception as error:
        logging.error(error)
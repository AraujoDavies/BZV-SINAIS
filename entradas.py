import logging
from sqlalchemy import text

from time import sleep
from helper_browser import meu_browser
from helper_sql import db_mysql
from step1 import acessa_betfair
from dotenv import load_dotenv
from helper_telegram import enviar_no_telegram, chat_id

load_dotenv('config.env')

logging.basicConfig(
    level=logging.WARNING,
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
        logging.warning('URL Atual: %s', b.url)
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
        b.find_by_xpath('//span[@class="receipt-footer__cancel-unmatched"]').click()
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
                c.execute(text(f"UPDATE entradas SET pl = {pl} WHERE market_id = {market_id};"))
                stake_info = c.execute(text("SELECT stake_base, stake_atual FROM stake_control WHERE id = 1;")).fetchall()
                stake_base = stake_info[0][0]
                stake_atual = stake_info[0][1]
                nova_stake_atual = stake_atual + pl

                # se green e nao dobrou a stake ainda...
                if pl > 0 and nova_stake_atual < stake_base * 2: # atualizar stake
                    c.execute(text(f"UPDATE stake_control SET stake_atual = {nova_stake_atual}, banca = {banca_now}, update_datetime = NOW() WHERE id = 1;"))
                else: # stake atual reseta
                    c.execute(text(f"UPDATE stake_control SET stake_atual = {stake_base}, update_datetime = NOW() WHERE id = 1;"))
    
        return True
    except:
        return False


def enviar_resultado_telegram(market_id):
    try:
        with engine.begin() as c:
            dados_msg = c.execute(text(f"select partida, stake, pl from entradas where market_id = '{market_id}';")).fetchall()

        partida = dados_msg[0][0]
        stake = dados_msg[0][1]
        pl = dados_msg[0][2]

        if pl > 0:
            msg = f"""
    ❗️❗️🦓 BZV Entrada realizada 🦓❗️❗️

{partida}

Stake: {stake} 💰
Resultado: {pl} ✅✅
    """
        else:
            msg = f"""
    ❗️❗️🦓 BZV Entrada realizada 🦓❗️❗️

{partida}

Stake: {stake} 💰
Resultado: {pl} ❌❌
    """
            
        id_telegram = enviar_no_telegram(chat_id, msg)

        return id_telegram
    except:
        return 'ERRO ao enviar resultado no telegram'
       
engine = db_mysql()
logging.warning('ON...')
# market_id = '1.236092576'
# mercado_selecionado = 0
# valor_apostado = 5
# import sys
# sys.exit()

while True:
    with engine.begin() as c:
        market = c.execute(text("SELECT market_id, mercadoSelecionado FROM sinais WHERE entradaProposta = 'N' AND resultado IS NULL ORDER BY data_raspagem DESC LIMIT 1;")).fetchall()
        if bool(market):
            stake = c.execute(text("SELECT stake_atual FROM stake_control WHERE id = 1;")).fetchall()

    if bool(market):
        logging.warning('Encontrou entrada...')
        b = meu_browser()
        acessa_betfair(b)
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

            while True:
                atualizou = atualizar_stake_control(market_id)
                if atualizou == True:
                    logging.warning('Atualizou stake control')
                    status_envio = enviar_resultado_telegram(market_id)
                    logging.warning('Enviou no telegram: %s', status_envio)
                    break
        else:
            try: # fecha o browser
                b.quit()
            except: 
                pass

    sleep(5)
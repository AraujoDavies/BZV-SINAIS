# O objetivo desta rotina é entrar na betfair, analisar os dados, 
# add no DB, enviar sinal no telegram e por fim salvar o resultado da entrada

import schedule, logging, datetime
from helper_browser import meu_browser
from selenium.common.exceptions import InvalidSessionIdException

# passo a passo
from step1 import acessa_betfair
from step2 import dados_jogos_que_estao_ao_vivo, salvar_padrao_zebra_mandante, salvar_padrao_zebra_visitante
from step3 import enviar_entrada_no_telegram, att_resultado
from dotenv import load_dotenv
from time import sleep

load_dotenv('config.env')

logging.basicConfig(
    level=logging.WARNING,
    encoding='utf-8',
    format='%(asctime)s - %(levelname)s: %(message)s',
)


def run_rotina(browser):
    try:
        logging.warning('-------------start------------')
        acessa_betfair(browser)
        browser.is_element_present_by_xpath('//table[@class="coupon-table"]', wait_time=10)
        for i in range(10):
            dados = dados_jogos_que_estao_ao_vivo(browser)
            if bool(dados):
                salvar_padrao_zebra_mandante(dados)
                salvar_padrao_zebra_visitante(dados)
            enviar_entrada_no_telegram()
        att_resultado()
        logging.warning('-------------finish------------')
    except:
        logging.critical('ROTINA FALHOU')
        sleep(60)
    # finally:
    #     browser.quit()

sleep(90)
browser = meu_browser()

while True:
    try:
        print(browser.title)
    except InvalidSessionIdException:
        browser = meu_browser()

    run_rotina(browser)
    sleep(3)
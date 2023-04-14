# O objetivo desta rotina é entrar na betfair, analisar os dados, 
# add no DB, enviar sinal no telegram e por fim salvar o resultado da entrada

import schedule, logging, datetime
from helper_browser import meu_browser

# passo a passo
from step1 import acessa_betfair
from step2 import dados_jogos_que_estao_ao_vivo, salvar_padrao
from step3 import enviar_entrada_no_telegram, att_resultado
from dotenv import load_dotenv
from time import sleep

load_dotenv('config.env')

logging.basicConfig(
    level=logging.INFO,
    encoding='utf-8',
    format='%(asctime)s - %(levelname)s: %(message)s',
)

def run_rotina():
    try:
        logging.warning('-------------start------------')
        browser = meu_browser()
        acessa_betfair(browser)
        browser.is_element_present_by_xpath('//table[@class="coupon-table"]', wait_time=10)
        for i in range(10):
            dados = dados_jogos_que_estao_ao_vivo(browser)
            if bool(dados):
                salvar_padrao(dados)
            enviar_entrada_no_telegram()
        att_resultado()
        logging.warning('-------------finish------------')
    except:
        logging.critical('ROTINA FALHOU')
        sleep(60)
    finally:
        browser.quit()


run_rotina()
schedule.every(10).seconds.do(run_rotina)

while True:
    schedule.run_pending()
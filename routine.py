# O objetivo desta rotina é entrar na betfair, analisar os dados, 
# add no DB, enviar sinal no telegram e por fim salvar o resultado da entrada

import schedule, logging, datetime, os
from helper_browser import meu_browser
from selenium.common.exceptions import InvalidSessionIdException

# passo a passo
from step1 import acessa_betfair
from step2 import dados_jogos_que_estao_ao_vivo, salvar_padrao_zebra_mandante, salvar_padrao_zebra_visitante
from step3 import enviar_entrada_no_telegram, att_resultado
from dotenv import load_dotenv
from time import sleep

load_dotenv()

if os.name == 'nt': # "nt" é windows | "posix" é linux/mac
    log_name = './logs/sinais'
    log_name += datetime.datetime.now().strftime('%d%m')
    log_name += '.log'
    logging.warning("Você está no Windows - Logs salvos!")
    logging.basicConfig(
        filename=log_name,
        level=logging.INFO,
        encoding='utf-8',
        format='%(asctime)s - %(levelname)s: %(message)s',
    )
else:
    logging.warning('Não está salvando logs')
    logging.basicConfig(
        level=logging.INFO,
        encoding='utf-8',
        format='%(asctime)s - %(levelname)s: %(message)s',
    )

def run_rotina(browser):
    try:
        # logging.warning('-------------start------------')
        
        timeout = 0
        logou = acessa_betfair(browser)
        while logou == False:
            logou = acessa_betfair(browser)
            timeout += 1
            if timeout > 3:
                logging.critical('Várias tentativas de login falharam')
                break

        browser.is_element_present_by_xpath('//table[@class="coupon-table"]', wait_time=20)
        for i in range(10):
            dados = dados_jogos_que_estao_ao_vivo(browser)
            if bool(dados):
                salvar_padrao_zebra_mandante(dados)
                salvar_padrao_zebra_visitante(dados)
            enviar_entrada_no_telegram()
        att_resultado()
        # logging.warning('-------------finish------------')
    except InvalidSessionIdException:
        logging.error('Fechou o navegador em execução')
    except Exception as error:
        logging.critical('ROTINA FALHOU: %s', str(error))
        sleep(10)
    # finally:
    #     browser.quit()

# sleep(90)

while True:
    try:
        print(browser.title)
    except:
        logging.warning('Abrindo chrome!')
        browser = meu_browser(enable_vnc=False)

    run_rotina(browser)
    sleep(3)
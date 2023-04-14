# Acessar betfair e fazer login

from os import getenv
from dotenv import load_dotenv
import logging

load_dotenv('config.env')

def acessa_betfair(b):
    """
        1 Acessar e Logar.
    """
    logging.warning("1 - Acessando betfair...")
    try:
        # Variaveis
        url_betfair = getenv("URL_BETFAIR")
        user_betfair = getenv("USER_BETFAIR")
        pass_betfair = getenv("PASS_BETFAIR")

        b.visit(url_betfair)
        # Aceitar cookies
        if b.is_element_present_by_xpath('//button[@id="onetrust-accept-btn-handler"]', wait_time=10):
            b.find_by_xpath('//button[@id="onetrust-accept-btn-handler"]').click()
        # ajustar visualização
        b.find_by_xpath('//div[@class="group-by-filter"]//*[@class="selected-option"]').click()
        b.find_by_xpath('//*[@class="options-list"]//*[@title = "Data"]').click()
        # form login
        b.is_element_present_by_xpath('//input[@name="username"]', wait_time=10)
        b.find_by_xpath('//input[@name="username"]').fill(user_betfair)
        b.find_by_xpath('//input[@name="password"]').fill(pass_betfair)
        b.find_by_xpath('//input[@value="Login"]').click()
        logging.warning("1 - login feito com sucesso!")
    except:
        b.screenshot(getenv("PRINT_DIR"))
        logging.error("1 - ERRO ao acessar betfair!")
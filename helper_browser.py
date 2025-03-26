from selenium import webdriver
from selenium.webdriver import Chrome
from splinter import Browser
from selenium.webdriver.chrome.options import Options
from splinter.driver.webdriver import BaseWebDriver

import requests

# p desenv
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.chrome.service import Service
# service = Service(ChromeDriverManager().install())


def execute_cmd_via_api_selenium(driver):
    url = f"http://localhost:4444/wd/hub/session/{driver.driver.session_id}/goog/cdp/execute"

    headers = {
        'Content-Type': 'application/json',
    }

    json_data = {
        'cmd': 'Emulation.setGeolocationOverride',
        'params': {
            'latitude': -23.3507386,
            'longitude': -46.7452335,
            'accuracy': 100,
        },
    }

    response = requests.post(
        url=url,
        headers=headers,
        json=json_data,
    )

    print(response.json())


def meu_browser(enable_video = False, enable_vnc = False):   
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--force-device-scale-factor=0.9")
    # chrome_options.add_argument("--user-data-dir=C:\\Users\\MrRobot\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 1")

    # Definindo argumentos ou preferências
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.geolocation": 1  # Permite geolocalização
    })

    # Definindo capabilities personalizadas
    chrome_options.set_capability("browserName", "chrome")
    chrome_options.set_capability("browserVersion", "128.0")
    chrome_options.set_capability("selenoid:options", {
        "enableVideo": enable_video,
        "enableVNC": enable_vnc
    })

    driver = Browser(driver_name='remote',browser='chrome', command_executor='http://127.0.0.1:4444/wd/hub', options=chrome_options)
    driver.driver.session_id

    execute_cmd_via_api_selenium(driver)

    return driver
    # driver local
    # return Browser('chrome', options=chrome_options) #, service=service)

if __name__ == '__main__':
    enable_video, enable_vnc = False, True
    b = meu_browser(enable_video, enable_vnc)
    b.visit("https://www.google.com/maps")

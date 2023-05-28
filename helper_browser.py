from splinter import Browser
from selenium.webdriver.chrome.options import Options

# p desenv
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.chrome.service import Service
# service = Service(ChromeDriverManager().install())

chrome_options = Options()
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--force-device-scale-factor=0.9")
# chrome_options.add_argument("--user-data-dir=C:\\Users\\MrRobot\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 1")


def meu_browser():
    return Browser(driver_name='remote',browser='Chrome', command_executor='http://localhost:4444', options=chrome_options)
    # driver local
    # return Browser('chrome', options=chrome_options, service=service)
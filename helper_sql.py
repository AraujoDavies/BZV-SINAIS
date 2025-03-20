from sqlalchemy import create_engine
import urllib.parse
from os import getenv
from dotenv import load_dotenv

load_dotenv('config.env')

def db_mysql():
    host= getenv('HOST_DATABASE')
    user= getenv('USER_DATABASE')
    password= getenv('PASSWORD_DATABASE')
    database= getenv('USE_DATABASE')

    password = urllib.parse.quote_plus(password)
    engine = create_engine(f'mysql+pymysql://{user}:{password}@{host}/{database}')
    return engine

if __name__ == '__main__':
    engine = db_mysql()
    from sqlalchemy import text
    with engine.begin() as c:
        a = c.execute(text("select * from sinais")).fetchall()

# print(a)
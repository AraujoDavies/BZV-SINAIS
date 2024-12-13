# ao iniciar um novo sheet deve ter pelo menos uma linha
import platform

if platform.system() == 'Windows':
    from dotenv import load_dotenv

    load_dotenv()

import logging
import os
from datetime import datetime
from time import sleep

import gspread
import pandas as pd

from oauth2client.service_account import ServiceAccountCredentials




def gsheet_sync(df: pd.DataFrame) -> int:
    """
    Sobe os dados do banco sqlLite para o GSHEET.

    Return:

        (_int_) -> Quantidade de linhas alteradas no gsheet
    """
    cred = os.getcwd() + os.sep + 'crespo-gregio-171328fd6bd7.json'
    nome_planilha = 'bzv_db_sync' 
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive',
    ]
    try:
        # Autenticar usando o arquivo JSON das credenciais
        creds = ServiceAccountCredentials.from_json_keyfile_name(cred, scope)
        client = gspread.authorize(creds)

        spreadsheet = client.open(nome_planilha)
        worksheet = spreadsheet.get_worksheet(0)  # Seleciona a primeira aba

        # Converter o DataFrame para uma lista de listas, incluindo o cabeçalho
        data = [df.columns.values.tolist()] + df.values.tolist()

        # Atualizar os dados na planilha (substituindo o conteúdo existente)
        worksheet.clear()   # truncate
        info = worksheet.update(data)
        return info['updatedRows']
    except Exception as error:
        logging.error('Falha ao sync: %s', str(error))
        return 0

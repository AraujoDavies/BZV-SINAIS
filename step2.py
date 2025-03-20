# Encontrar padrão de back zebra em casa e salvar no banco de dados

from bs4 import BeautifulSoup
import pandas as pd
import datetime, logging
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from helper_sql import db_mysql
from time import sleep
from os import getenv
from dotenv import load_dotenv

load_dotenv('config.env')

def dados_jogos_que_estao_ao_vivo(b):
    """
        2.1 - Coletar dados dos jogos que estão rolando. (Função auxiliar)
    """
    sleep(5)
    html = b.find_by_xpath(
        '//table[@class="coupon-table"]'
    ).first.html
    soup = BeautifulSoup(html, 'html.parser')
    # lista de jogos (caso tenha  jogos ao vivo, focará neles. caso não pegara todos)...
    jogos_in_live = soup.find_all(
        'tr',
        attrs={'ng-repeat-start': '(marketId, event) in vm.tableData.events'},
    )
   
    dados_dos_jogos = []

    # pegando ids do banco de dados para não acrescentar novamente
    market_ids = []
    engine = db_mysql()
    with engine.begin() as c:
        market_ids_db = c.execute(text("SELECT market_id FROM sinais WHERE evento_em_andamento = 1")).fetchall()

    for id in market_ids_db:
        market_ids.append(id[0])

    for jogo in jogos_in_live:
        # variavel de controle
        ignore_evento = False
        # tempo do jogo
        tempo = jogo.find('div').text
        dict = {}
        if 'Ao vivo' in tempo or 'Hoje às' in tempo or 'Começa em' in tempo or 'FIM' in tempo or 'INT' in tempo:
            continue
        else:
            minutos = jogo.find('div', 'middle-label')
            if bool(minutos):
                
                # Pegando ID do mercado, ignorando os q já estão no banco
                market_id_raspado = jogo.td.find('a', 'mod-link').get('data-market-id')
                if market_id_raspado in market_ids:
                    logging.info(f'2.1 - pulando o ID {market_id_raspado} já existe no DB!')
                    ignore_evento = True
                else:
                    logging.info(f'2.1 - ID {market_id_raspado} não existe no DB. incluso no dict!')
                        
                if ignore_evento:
                    continue
                dict[
                    'market-id'
                ] = jogo.td.find('a', 'mod-link').get('data-market-id')

                dict['data_raspagem'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                minutos = jogo.find('div', 'middle-label').text
                dict['tempo'] = (
                    minutos.replace("'", '') if "'" in minutos else minutos
                )
                
                # Equipes, separando mandante e visitante
                equipes = jogo.find('ul', class_='runners')
                dict['mandante'] = equipes.find_all('li')[0].attrs['title']
                dict['visitante'] = equipes.find_all('li')[1].attrs['title']

                # placar do mandante e do visitante
                placar_mandante = jogo.find('div', 'scores').find('span', 'home').text                
                placar_visitante = jogo.find('div', 'scores').find('span', 'away').text
                dict['placar'] = f'{placar_mandante} - {placar_visitante}'

                # ODDS new
                odds = jogo.find('td', "coupon-runners") # area de odds
                odds_b = odds.find_all('button') # 6 botões
                dict['odd_back_mandante'] = (
                    0 if odds_b[0].find('label').text == '' 
                    else odds_b[0].find('label').text
                )
                dict['odd_lay_mandante'] = (
                    0 if odds_b[1].find('label').text == '' 
                    else odds_b[1].find('label').text
                )
                dict['odd_back_visitante'] = (
                    0 if odds_b[-2].find('label').text == ''
                    else odds_b[-2].find('label').text
                )
                dict['odd_lay_visitante'] = (
                    0 if odds_b[-1].find('label').text == ''
                    else odds_b[-1].find('label').text
                )

                # competição
                url = f"https://www.betfair.com/exchange/plus/{jogo.td.find('a', 'mod-link').get('href')}"
                dict['competicao'] = url.split('/')[-2]

                # Liquidez
                dict['liquidez'] = float(
                    jogo.find('li', class_='matched-amount-value')
                    .text.replace(',', '')
                    .replace('R$', '')
                )

                # Mercado está suspenso ?
                dict['mercado_suspenso'] = bool(
                    jogo.find('div', 'state-overlay-container')
                )

                # salvando na lista
                dados_dos_jogos.append(dict)
    
    logging.info(f"2.1 - jogos coletados para analise {len(dados_dos_jogos)}")
    return dados_dos_jogos


def salvar_padrao_zebra_mandante(dados):
    """
        2.2 - analisa dados dos jogos q estão rolando e salva padrão no DB. (Função principal)
    """
    df= pd.DataFrame(dados)

    logging.info("2.2 ZebraMandante - Convertendo valores...")
    # convertendo valores
    df['odd_lay_mandante'] = df['odd_lay_mandante'].astype(float)
    df['odd_back_mandante'] = df['odd_back_mandante'].astype(float)
    df['tempo'] = df['tempo'].astype(int)
    df['liquidez'] = df['liquidez'].astype(int)

    logging.info("2.2 ZebraMandante - Adicionando coluna GAP")
    # criando colunas
    df['gap'] = df['odd_lay_mandante'] - df['odd_back_mandante']

    logging.info(f"2.2 ZebraMandante - Jogos em analise: {df.mandante.count()}")
    # tempo de jogo entre 85 e 89
    padrao_tempo = (df['tempo'] >= float(getenv("TEMPO_INICIAL"))) & (df['tempo'] < float(getenv("TEMPO_FINAL")))
    logging.info(f"2.2 ZebraMandante - Jogos entre 85 e 90 min: {df[padrao_tempo].mandante.count()}")
    # placar 2 - 1, 1 - 0
    padrao_score = (df['placar'] == '1 - 0') | (df['placar'] == '2 - 1')
    logging.info(f"2.2 ZebraMandante - Jogos com placar esperado: {df[padrao_score].mandante.count()}")
    # ODD
    padrao_odd = (df['odd_back_mandante'] > float(getenv("ODD_MIN"))) & (df['odd_back_mandante'] < float(getenv("ODD_MAX")))
    logging.info(f"2.2 ZebraMandante - Jogos com padrão de ODD: {df[padrao_odd].mandante.count()}")
    # liquidez > 40k
    padrao_liq = (df['liquidez'] >= float(getenv("LIQUIDEZ")))
    logging.info(f"2.2 ZebraMandante - Jogos com liquidez: {df[padrao_liq].mandante.count()}")
    # mercado não suspenso
    padrao_suspended = (df['mercado_suspenso'] == False) 
    logging.info(f"2.2 ZebraMandante - Jogos Não suspensos: {df[padrao_suspended].mandante.count()}")
    # gap aceitável
    padrao_gap = (df['gap'] < float(getenv("GAP")))
    logging.info(f"2.2 ZebraMandante - Jogos com gap ok: {df[padrao_gap].mandante.count()}")


    padrao = padrao_suspended & padrao_liq & padrao_tempo & padrao_score & padrao_gap & padrao_odd
    logging.info(f"2.2 ZebraMandante - Jogos com padrão: {df[padrao].mandante.count()}")

    engine = db_mysql()

    for linha in df[padrao].index:
        t = (df['market-id'][linha], df['data_raspagem'][linha], f"{df['tempo'][linha]}", df['mandante'][linha], df['visitante'][linha],
    df['placar'][linha], f"{df['odd_back_mandante'][linha]}", df['competicao'][linha], f"{df['liquidez'][linha]}", "0") 
        
        comando = f"""INSERT INTO sinais 
(market_id, data_raspagem, tempo, mandante, visitante, placar, odd, campeonato, liquidez, mercadoSelecionado)
VALUES
{t};
        """
        logging.info(f"2.2 ZebraMandante - SQL: {comando}")
        try:
            with engine.begin() as c:
                c.execute(text(comando))
        except SQLAlchemyError as ie:
            logging.critical(f"POSSIVELMENTE {df['market-id'][linha]} JÁ EXISTE NO BANCO... {ie}")



def salvar_padrao_zebra_visitante(dados):
    """
        2.2 - analisa dados dos jogos q estão rolando e salva padrão no DB. (Função principal)
    """
    df= pd.DataFrame(dados)

    logging.info("2.2 ZebraVisitante - Convertendo valores...")
    # convertendo valores
    df['odd_lay_visitante'] = df['odd_lay_visitante'].astype(float)
    df['odd_back_visitante'] = df['odd_back_visitante'].astype(float)
    df['tempo'] = df['tempo'].astype(int)
    df['liquidez'] = df['liquidez'].astype(int)

    logging.info("2.2 ZebraVisitante - Adicionando coluna GAP")
    # criando colunas
    df['gap'] = df['odd_lay_visitante'] - df['odd_back_visitante']

    logging.info(f"2.2 ZebraVisitante - Jogos em analise: {df.mandante.count()}")
    # tempo de jogo entre 85 e 89
    padrao_tempo = (df['tempo'] >= float(getenv("TEMPO_INICIAL"))) & (df['tempo'] < float(getenv("TEMPO_FINAL")))
    logging.info(f"2.2 ZebraVisitante - Jogos entre 85 e 90 min: {df[padrao_tempo].mandante.count()}")
    # placar 2 - 1, 1 - 0
    padrao_score = (df['placar'] == '0 - 1') | (df['placar'] == '1 - 2')
    logging.info(f"2.2 ZebraVisitante - Jogos com placar esperado: {df[padrao_score].mandante.count()}")
    # ODD
    padrao_odd = (df['odd_back_visitante'] > float(getenv("ODD_MIN"))) & (df['odd_back_visitante'] < float(getenv("ODD_MAX")))
    logging.info(f"2.2 ZebraVisitante - Jogos com padrão de ODD: {df[padrao_odd].mandante.count()}")
    # liquidez > 40k
    padrao_liq = (df['liquidez'] >= float(getenv("LIQUIDEZ")))
    logging.info(f"2.2 ZebraVisitante - Jogos com liquidez: {df[padrao_liq].mandante.count()}")
    # mercado não suspenso
    padrao_suspended = (df['mercado_suspenso'] == False) 
    logging.info(f"2.2 ZebraVisitante - Jogos Não suspensos: {df[padrao_suspended].mandante.count()}")
    # gap aceitável
    padrao_gap = (df['gap'] < float(getenv("GAP")))
    logging.info(f"2.2 ZebraVisitante - Jogos com gap ok: {df[padrao_gap].mandante.count()}")


    padrao = padrao_suspended & padrao_liq & padrao_tempo & padrao_score & padrao_gap & padrao_odd
    logging.info(f"2.2 ZebraVisitante - Jogos com padrão: {df[padrao].mandante.count()}")

    engine = db_mysql()

    for linha in df[padrao].index:
        t = (df['market-id'][linha], df['data_raspagem'][linha], f"{df['tempo'][linha]}", df['mandante'][linha], df['visitante'][linha],
    df['placar'][linha], f"{df['odd_back_visitante'][linha]}", df['competicao'][linha], f"{df['liquidez'][linha]}", "1") 
        
        comando = f"""INSERT INTO sinais 
(market_id, data_raspagem, tempo, mandante, visitante, placar, odd, campeonato, liquidez, mercadoSelecionado)
VALUES
{t};
        """
        logging.info(f"2.2 ZebraVisitante - SQL: {comando}")
        try:
            with engine.begin() as c:
                c.execute(text(comando))
        except SQLAlchemyError as ie:
            logging.critical(f"POSSIVELMENTE {df['market-id'][linha]} JÁ EXISTE NO BANCO... {ie}")

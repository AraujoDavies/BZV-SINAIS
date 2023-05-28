# pip install pyrogram
# pip install tgcrypto
from os import getenv

from dotenv import load_dotenv
from pyrogram import Client

import logging

load_dotenv('config.env')

from pyrogram import Client

# api_id = 13847847
# api_hash = "f04ebf6d6c59aace23fba25ffa7c3891"
# app = Client(getenv('TELEGRAM_CLIENT'), api_id=api_id, api_hash=api_hash)
app = Client(getenv('TELEGRAM_CLIENT'))
chat_id_mandante = getenv('TELEGRAM_CHAT_ID_MANDANTE') # -1001849267600
chat_id_visitante = getenv('TELEGRAM_CHAT_ID_VISITANTE')

def enviar_no_telegram(chat_id, msg):
    """
        Enviando mensagem e salva o ID no banco
    """
    app.start()
    msg = app.send_message(chat_id, f'{msg}')
    id = msg.id
    app.stop()
    return id

# msg = 'dadada'
# enviar_no_telegram(chat_id_visitante, msg)

async def resultado_da_entrada(chat_id, reply_msg_id, msg):
    """
        responde a msg de entrada com o resultado(green/red)
    """
    await app.start()
    await app.send_message(chat_id, f'{msg}', reply_to_message_id=reply_msg_id)
    await app.stop()

# app.run(resultado_da_entrada(chat_id, reply_msg_id, msg))

# função assíncrona
@app.on_message() # quando receber uma mensagem...
async def resposta(client, message): 
    print(message.chat.id, message.text) #Pessoa, oq a pessoa diz ao bot
    # await message.reply('me sorry yo no hablo tu language D:') # resposta do bot

# app.run() # executa
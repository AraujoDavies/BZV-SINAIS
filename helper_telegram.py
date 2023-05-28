# pip install pyrogram
# pip install tgcrypto
from os import getenv

from dotenv import load_dotenv
from pyrogram import Client

import logging

load_dotenv('config.env')

from pyrogram import Client

app = Client(getenv('TELEGRAM_CLIENT'))
chat_id = getenv('TELEGRAM_CHAT_ID') 

def enviar_no_telegram(chat_id, msg):
    """
        Enviando mensagem e salva o ID no banco
    """
    app.start()
    msg = app.send_message(chat_id, f'{msg}')
    id = msg.id
    app.stop()
    return id

# enviar_no_telegram(chat_id, msg)

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
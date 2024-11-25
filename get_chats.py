from pyrogram import Client
from dotenv import load_dotenv
from os import getenv

load_dotenv('config.env')

with Client(getenv('TELEGRAM_CLIENT')) as app:
    all_chats = app.get_dialogs()

    list_chats = []

    for chat in all_chats:
        list_chats.append([chat.chat.id, chat.chat.title])

# with open(f'./chats/meus_chats_{getenv("SESSION").split("/")[-1]}.txt', mode="w", encoding="utf-8") as arquivo:
print('Chat Name - Chat ID')
for chat in list_chats:
    if chat[1] != None:
        print(f'{chat[1]} - {chat[0]}')

print('')
print('Selecione o ID do CHAT DESTINO e do CHAT ORIGEM e configure em config.env')
print('')

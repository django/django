
def ws_message(message):
    "Echoes messages back to the client"
    message.reply_channel.send(message.content)

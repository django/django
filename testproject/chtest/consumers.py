from channels.sessions import enforce_ordering


#@enforce_ordering(slight=True)
def ws_connect(message):
    pass


#@enforce_ordering(slight=True)
def ws_message(message):
    "Echoes messages back to the client"
    message.reply_channel.send(message.content)

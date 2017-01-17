from channels.sessions import enforce_ordering


def ws_message(message):
    "Echoes messages back to the client"
    message.reply_channel.send({'text': message['text']})

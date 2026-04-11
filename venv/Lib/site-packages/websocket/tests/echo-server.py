#!/usr/bin/env python

# From https://github.com/aaugustin/websockets/blob/main/example/echo.py

import asyncio
import os

import websockets

LOCAL_WS_SERVER_PORT = int(os.environ.get("LOCAL_WS_SERVER_PORT", "8765"))


async def echo(websocket):
    async for message in websocket:
        await websocket.send(message)


async def main():
    async with websockets.serve(echo, "localhost", LOCAL_WS_SERVER_PORT):
        await asyncio.Future()  # run forever


asyncio.run(main())

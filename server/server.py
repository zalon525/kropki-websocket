import asyncio
import websockets
import itertools
import json
import sys


HOST = "localhost"
PORT = 8765


class Player:
    counter = itertools.count(start=1, step=1)

    def __init__(self, speed=4, start_x=0, start_y=0):
        self.id = next(self.counter)
        self.speed = speed
        self.x = start_x
        self.y = start_y

    def move_up(self):
        self.y -= self.speed

    def move_down(self):
        self.y += self.speed

    def move_right(self):
        self.x += self.speed

    def move_left(self):
        self.x -= self.speed


class ServerMessage:
    dict = {}

    def to_json(self):
        return json.dumps(self.dict)


class PlayerJoinedMessage(ServerMessage):
    def __init__(self, player):
        self.dict = {
            'type': 'player_joined',
            'body': {
                'id': player.id,
                'x': player.x,
                'y': player.y
            }
        }


class PlayerLeftMessage(ServerMessage):
    def __init__(self, player):
        self.dict = {
            'type': 'player_left',
            'body': {
                'id': player.id
            }
        }


class PlayerMovedMessage(ServerMessage):
    def __init__(self, player):
        self.dict = {
            'type': 'player_moved',
            'body': {
                'id': player.id,
                'x': player.x,
                'y': player.y
            }
        }


class Game:
    def __init__(self, event_loop, host=HOST, port=PORT):
        self.event_loop = event_loop
        self.host = host
        self.port = port
        self.sync_connections = []
        self.players = []

    async def connection_handler(self, websocket, path):
        player = Player()
        self.players.append(player)

        await self.sync_game_state(websocket)
        await self.broadcast_message(PlayerJoinedMessage(player))
        self.sync_connections.append(websocket)

        try:
            while True:
                await self.handle_player_input(websocket, player)
        finally:
            self.sync_connections.remove(websocket)
            self.players.remove(player)
            await self.broadcast_message(PlayerLeftMessage(player))

    async def handle_player_input(self, websocket, player):
        msg = json.loads(await websocket.recv())
        print("Received: {}".format(json.dumps(msg)))
        if msg['type'] == 'keypressed':
            key = msg['body']['key']
            if key == 'w':
                player.move_up()
            elif key == 's':
                player.move_down()
            elif key == 'd':
                player.move_right()
            elif key == 'a':
                player.move_left()

            await self.broadcast_message(PlayerMovedMessage(player))

    async def broadcast_message(self, msg):
        print("Broadcast: {}".format(msg.to_json()))
        if self.sync_connections:
            await asyncio.wait([ws.send(msg.to_json()) for ws in self.sync_connections])

    async def sync_game_state(self, websocket):
        await asyncio.wait([websocket.send(PlayerJoinedMessage(p).to_json()) for p in self.players])

    def run_game_loop(self):
        start_server = websockets.serve(self.connection_handler, self.host, self.port)
        self.event_loop.run_until_complete(start_server)
        self.event_loop.run_forever()


def main(argv):
    game = Game(asyncio.get_event_loop())
    game.run_game_loop()


if __name__ == '__main__':
    sys.exit(main(sys.argv))

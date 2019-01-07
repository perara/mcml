import asyncio
import time

from builder import Struct
from manager import Manager
from tcpserver import TCPServer


class Agent(TCPServer):

    def __init__(self):
        super().__init__()

    async def _run(self):

        while True:
            await self.forward(str(self.pid))
            await asyncio.sleep(1)


class StateReplace(TCPServer):

    def __init__(self):
        super().__init__()

    async def _process(self, x):
        return x + " => " + str(self.pid)


class RGB2Gray(TCPServer):

    def __init__(self):
        super().__init__()

    async def _process(self, x):
        return x + " => " + str(self.pid)


class Model(TCPServer):

    def __init__(self):
        super().__init__()
        self.counter = 0
        self.time = time.time()

    async def _process(self, x):
        #print(x + " => " + str(self.pid))
        if time.time() > self.time + 1:
            print("Msg per sec: %s" % self.counter)
            self.time = time.time()
            self.counter = 0
        self.counter += 1



if __name__ == "__main__":
    """Manager, Could be started anywhere...."""
    manager = Manager(host='0.0.0.0', port=41000)
    manager.daemon = True
    manager.start()

    #Build Struct.
    struct = Struct({
        "manager": ('127.0.0.1', 41000),
        "model": [
            (Agent, 1),
            (StateReplace, 1),
            (RGB2Gray, 2),
            (Model, 1)
        ]
    })


    loop = asyncio.get_event_loop()
    loop.create_task(struct.build())


    loop.run_forever()

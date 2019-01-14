import asyncio
import time
import numpy as np
from builder import Struct
from manager import Manager
from tcpserver import TCPServer


class Agent(TCPServer):

    def __init__(self):
        super().__init__()

    async def _run(self):
        data = np.random.randn(80, 80, 3)

        while True:
            await self.forward(data)
            await asyncio.sleep(0)


class OtherAgent(Agent):

    def __init__(self):
        super().__init__()


class StateReplace(TCPServer):

    def __init__(self):
        super().__init__()

    async def _process(self, x):
        return x
        #return x + " => " + str(self.pid)


class RGB2Gray(TCPServer):

    def __init__(self):
        super().__init__()

    async def _process(self, x):
        pass # return x + " => " + str(self.pid)


class Model(TCPServer):

    def __init__(self):
        super().__init__()

    async def _process(self, x):
        pass


if __name__ == "__main__":
    """Manager, Could be started anywhere...."""
    manager = Manager(host='0.0.0.0', port=41000)
    manager.daemon = True
    manager.start()

    # TODO much werk. make struct building work...

    """Define the structure of the processing unit."""
    struct = Struct({
        "manager": dict(
            host='127.0.0.1',
            port='41000'
        ),
        "model": [
            [
                dict(agent=OtherAgent, population=4, extra_remotes=[Model])
            ],
            [
                dict(agent=Agent, population=5, extra_remotes=[]),
                dict(agent=StateReplace, population=4),
                dict(agent=RGB2Gray, population=1),
                dict(agent=Model, population=1)

            ]

        ]
    })

    loop = asyncio.get_event_loop()
    loop.create_task(struct.build())
    loop.run_forever()





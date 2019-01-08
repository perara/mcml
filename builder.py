class Struct:

    def __init__(self, struct):
        self.struct = struct

    async def build(self):

        previous_service = []
        depth = 0  # Process Depth
        for data in reversed(self.struct["model"]):

            # TODO this.
            if len(data) == 1:
                cls = data[0]
                count = 1
                remote_services = []
            elif len(data) == 2:
                cls = data[0]
                count = data[1]
                remote_services = []
            elif len(data) == 3:
                cls = data[0]
                count = data[1]
                remote_services = [x.__name__ for x in data[2]]
            else:
                raise ValueError("Struct.build() recieived wrong number of parameters on a layer")


            for i in range(count):

                obj = cls()
                await obj.set_manager(*self.struct["manager"])
                await obj.set_remote_service(remote_service_names=remote_services + previous_service)
                await obj.set_depth(depth)
                obj.daemon = True
                obj.start()

            depth += 1
            previous_service = [cls.__name__]


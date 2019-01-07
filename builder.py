class Struct:

    def __init__(self, struct):
        self.struct = struct

    async def build(self):

        previous_service = None
        depth = 0  # Process Depth
        for cls, count in reversed(self.struct["model"]):
            for i in range(count):

                obj = cls()
                await obj.set_manager(*self.struct["manager"])
                await obj.set_remote_service(remote_service_name=previous_service)
                await obj.set_depth(depth)
                obj.daemon = True
                obj.start()

            depth += 1
            previous_service = cls.__name__


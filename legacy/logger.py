import logging
logging.basicConfig(level=logging.WARNING)

mcml_log = logging.getLogger('mcml')
mcml_log.setLevel(logging.DEBUG)

manager_log = logging.getLogger('mcml_manager')
manager_log.setLevel(logging.DEBUG)

tcpserver_log = logging.getLogger('tcpserver')
tcpserver_log.setLevel(logging.DEBUG)

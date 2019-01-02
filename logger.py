import logging




mcml_log = logging.getLogger('mcml')
mcml_log.setLevel(logging.DEBUG)

manager_log = logging.getLogger('mcml_manager')
manager_log.setLevel(logging.DEBUG)


ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

mcml_log.addHandler(ch)
manager_log.addFilter(ch)

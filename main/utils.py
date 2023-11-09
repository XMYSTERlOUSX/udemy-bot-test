import logging
import sys
import importlib
from pathlib import Path

import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('log.txt'), logging.StreamHandler()],
    level=logging.INFO)
logger = logging.getLogger(__name__)

def load_plugins(plugin_name):
    path = Path(f"main/plugins/{plugin_name}.py")
    name = "main.plugins.{}".format(plugin_name)
    spec = importlib.util.spec_from_file_location(name, path)
    load = importlib.util.module_from_spec(spec)
    # load.logger = logging.getLogger(plugin_name)
    spec.loader.exec_module(load)
    sys.modules["main.plugins." + plugin_name] = load
    logger.info("main has Imported " + plugin_name)

#!/usr/bin/env -S python -u

import yaml
import argparse
import os

CONFIG_FILE_PATH = f'{os.path.expanduser("~")}/.config/clash/config.yaml'
PATTERN = "^\{[a-zA-Z_][a-zA-Z0-9_]*\}$"


def load_config():
    with open(CONFIG_FILE_PATH) as config_file:
        config = yaml.load(config_file, Loader=yaml.BaseLoader)

    for proxy in config['Proxy']:
        print(proxy['name'])




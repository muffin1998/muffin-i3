import configparser
import copy
import argparse
import os

CWD = os.getcwd()
SECTION_BAR = 'bar/main'
COLOR_FLAG = '$color$'
THEME_FOLDER_FLAG = '${theme_folder}$'
KEY_COLOR = 'color'
KEY_LEFT_BORDER = 'left-border'
KEY_RIGHT_BORDER = 'right-border'
KEY_BORDER_BACKGROUND = 'background'
KEY_BORDER_FOREGROUND = 'foreground'
KEY_PADDING_LEFT = 'padding-left'
KEY_PADDING_RIGHT = 'padding-right'
BAR_BACKGROUND = 'background'
MODULE_BORDER_LEFT_PREFIX = 'border-left-of-'
MODULE_BORDER_RIGHT_PREFIX = 'border-right-of-'
MODULE_SECTION_PREFIX = 'module/'
MODULES_LEFT = 'modules-left'
MODULES_CENTER = 'modules-center'
MODULES_RIGHT = 'modules-right'
MODULES_POSITIONS = [MODULES_LEFT, MODULES_CENTER, MODULES_RIGHT]
CONTENT = 'content'
CONTENT_BACKGROUND = 'content-background'
CONTENT_FOREGROUND = 'content-foreground'
POLYBAR_CONFIG_PATH = 'sources/config.ini'
POLYBAR_COLOR_CONFIG_PATH = 'sources/polybar-color.ini'
MODULE_CONFIG_PATH = 'sources/module.ini'
MODULE_PART_CONFIG_PATH = 'sources/module-part.ini'
MODULE_COLOR_CONFIG_PATH = 'sources/module-color.ini'
OUTPUT_MODULE_CONFIG_PATH = 'module.ini'
OUTPUT_POLYBAR_CONFIG_PATH = 'config.ini'
OUTPUT_COLOR_CONFIG_PATH = 'color.ini'
OUTPUT_FILES = [OUTPUT_COLOR_CONFIG_PATH, OUTPUT_MODULE_CONFIG_PATH, OUTPUT_POLYBAR_CONFIG_PATH]
INCLUDE_PATHS = [f'{CWD}/{OUTPUT_COLOR_CONFIG_PATH}', f'{CWD}/{OUTPUT_MODULE_CONFIG_PATH}']
MODULE_BORDER = {'type': 'custom/text', 'content': '', 'content-background': '', 'content-foreground': ''}
BORDER_LEFT = 0
BORDER_RIGHT = 1
SYMBOL_LEFT = ''
SYMBOL_RIGHT = ''


def get_content(symbol, padding_left, padding_right):
    padding_left_str = ' ' * padding_left
    padding_right_str = ' ' * padding_right
    return f'"%{{T4}}{padding_left_str}{symbol}{padding_right_str}%{{T-}}"'


def write_config(config, path):
    with open(path, 'w') as config_file:
        config.write(config_file)


def print_config(config):
    for section in config.sections():
        print(f'[{section}]')
        for key in config[section]:
            print(f'{key} = {config[section][key]}')


def get_config(path):
    config = configparser.RawConfigParser()
    config.read(path)

    return config


def update_module_config(module_chains_with_position, color_bg):
    module_part_config = get_config(MODULE_PART_CONFIG_PATH)
    module_config = get_config(MODULE_CONFIG_PATH)
    module_color_config = get_config(MODULE_COLOR_CONFIG_PATH)
    module_list_with_position = {}

    def add_module_border(symbol, border_bg, border_fg, padding_left, padding_right):
        module_section = f'{MODULE_SECTION_PREFIX}{name}'
        border = copy.copy(MODULE_BORDER)
        border[CONTENT] = get_content(symbol, padding_left, padding_right)
        border[CONTENT_BACKGROUND] = border_bg
        border[CONTENT_FOREGROUND] = border_fg
        module_config[module_section] = {}
        for option in border.keys():
            module_config[module_section][option] = border[option]

    def get_value(value, default):
        return value if value is not None else default

    for position in MODULES_POSITIONS:
        module_list_with_position[position] = []
        for module_chain in module_chains_with_position[position]:
            size = len(module_chain)
            for index in range(size):
                module = module_chain[index]
                left_border = get_value(module_part_config[module].getboolean(KEY_LEFT_BORDER), False)
                right_border = get_value(module_part_config[module].getboolean(KEY_RIGHT_BORDER), False)
                padding_left = get_value(module_part_config[module].getint(KEY_PADDING_LEFT), 0)
                padding_right = get_value(module_part_config[module].getint(KEY_PADDING_RIGHT), 0)
                color_pre = color_bg \
                    if index == 0 or (left_border and module_part_config[module_chain[index - 1]].getboolean(KEY_RIGHT_BORDER)) \
                    else module_part_config[module_chain[index - 1]].get(KEY_COLOR)
                color = module_part_config[module].get(KEY_COLOR)
                color_next = color_bg \
                    if index == size - 1 or (right_border and module_part_config[module_chain[index + 1]].getboolean(KEY_LEFT_BORDER)) \
                    else module_part_config[module_chain[index + 1]].get(KEY_COLOR)
                if left_border or padding_left != 0:
                    name = f'{MODULE_BORDER_LEFT_PREFIX}{module}'
                    module_list_with_position[position].append(name)
                    # border = copy.copy(border_left)
                    add_module_border(SYMBOL_LEFT if left_border else '', color_pre, color, padding_left, 0)
                for name in module.split('|'):
                    module_list_with_position[position].append(name)
                    module_section = f'{MODULE_SECTION_PREFIX}{name}'
                    for option in module_color_config[module_section]:
                        value = module_color_config[module_section][option]
                        module_config[module_section][option] = color if value == COLOR_FLAG else module_color_config[module_section][option]
                if right_border or padding_right != 0:
                    name = f'{MODULE_BORDER_RIGHT_PREFIX}{module}'
                    module_list_with_position[position].append(name)
                    # border = copy.copy(border_right)
                    add_module_border(SYMBOL_RIGHT if right_border else '', color_next, color, 0, padding_right)

    return module_config, module_list_with_position


def update_polybar_config():
    polybar_config = get_config(POLYBAR_CONFIG_PATH)
    polybar_color_config = get_config(POLYBAR_COLOR_CONFIG_PATH)
    module_chains_with_position = {}
    for position in MODULES_POSITIONS:
        module_chains_with_position[position] = []
        value = polybar_config[SECTION_BAR][position]
        value = value.strip()
        if value != '':
            for module_chain_str in value.split(' '):
                module_chain_str = module_chain_str.strip()
                module_chain = []
                for module in module_chain_str.split('~'):
                    module_chain.append(module)
                module_chains_with_position[position].append(module_chain)
    print(module_chains_with_position)
    color_bg = polybar_color_config[SECTION_BAR][BAR_BACKGROUND]
    for section in polybar_color_config.sections():
        for option in polybar_color_config[section]:
            polybar_config[section][option] = polybar_color_config[section][option]
    module_config, module_list_with_position = update_module_config(module_chains_with_position, color_bg)
    print_config(module_config)
    print(module_list_with_position)
    for position in MODULES_POSITIONS:
        polybar_config[SECTION_BAR][position] = ' '.join(module for module in module_list_with_position[position])
    print_config(polybar_config)

    return polybar_config, module_config
    # write_config(module_config, OUTPUT_MODULE_CONFIG_PATH)


def update_script_path(module_config):
    for section in module_config.sections():
        for option in module_config[section]:
            value = module_config[section][option]
            if value.find(THEME_FOLDER_FLAG) != -1:
                module_config[section][option] = value.replace(THEME_FOLDER_FLAG, f'{CWD}/')


def add_includes():
    with open(OUTPUT_POLYBAR_CONFIG_PATH, 'r') as fp:
        content = fp.readlines()
    with open(OUTPUT_POLYBAR_CONFIG_PATH, 'w') as fp:
        for path in INCLUDE_PATHS:
            fp.writelines(f'include-file = {path}\n')
        fp.write('\n')
        fp.writelines(content)


def backup():
    import shutil
    if os.path.exists('backup'):
        shutil.rmtree('backup')
    os.mkdir('backup')
    backup_files = []
    for path in OUTPUT_FILES:
        if os.path.exists(path):
            with open(path) as fp:
                lines = fp.readlines()
            des_path = f'backup/{path}'
            with open(des_path, 'w') as fp:
                fp.writelines(lines)
            backup_files.append(des_path)

    return backup_files


def remove():
    for path in OUTPUT_FILES:
        if os.path.exists(path):
            os.remove(path)


def write(configs):
    for path in OUTPUT_FILES:
        write_config(configs[path], path)


def main():
    color_config = get_config(color_config_path)
    polybar_config, module_config = update_polybar_config()
    update_script_path(module_config)
    backup()
    remove()
    write({OUTPUT_COLOR_CONFIG_PATH: color_config, OUTPUT_POLYBAR_CONFIG_PATH: polybar_config, OUTPUT_MODULE_CONFIG_PATH: module_config})
    add_includes()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--color-config-file", type=str, default="nord.ini")
    args = parser.parse_args()
    color_config_path = f'sources/colors/{args.color_config_file}'
    print(f'color file path: {color_config_path}')
    main()
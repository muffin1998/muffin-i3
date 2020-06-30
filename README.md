# Muffin's i3

The project is a backup of my i3

## Features

- nord color schema
- polybar module for Netease Cloud Music

## Applications

- Polybar
- Picom
- Rofi
- Alacritty as default terminal
- Chrome
- PyCharm
- VSCode
- SogouPinyin from UKylin Community([fcitx-sogouimebs](https://gitee.com/laomocode/fcitx-sogouimebs))
- Netease Cloud Music
- Clash For Linux
- Typora


## Fonts

- Google Sans and Source Han Sans CN as default Sans font
- Fantasque Sans Mono Nerd Font and Sarasa Mono SC as default Monospace font
- Fantasque Sans Mono, Sarasa Mono SC and Iosevka Nerd Font as Polybar font

## Themes

- [Nordic](https://github.com/EliverLara/Nordic) (contain both gtk theme and qt theme, use LXAppearance and Kvantum Manager to apply)
- [Nord Skin for Chrome](https://chrome.google.com/webstore/detail/nord/abehfkkfjlplnjadfcjiflnejblfmmpj?utm_source=chrome-ntp-icon)
- Nord Skin for PyCharm
- Nord Skin for VSCode

## Tips

### i3wm
- $mod + up, down, left, right: Switch focus among windows in the same workspace
- $mod + Shift + up, down, left, right:
- $mod + r: Enter resize mode, use up, down, left, right to modify the size by 10px, Esc to exit
- $mod + left click: Move floating window
- $mod + right click: Resize floating window

### x

```shell script
xprop | grep "CLASS"
```

## To Do List

Network manager context menu create by rofi (base on connman ?)

Audio output device select (pulsectl(libpulse api for python) or dbus ?)

Fcitx config tool 

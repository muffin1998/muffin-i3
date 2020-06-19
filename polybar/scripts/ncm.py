#!/usr/bin/env -S python -u

# Note: /usr/bin/env -S option may not work on some platform,
# add python -u before script path in 'sources/module.ini' and use '#!/usr/bin/env python' instead

import dbus
import socket
import os
import stat
import time
import argparse
from threading import Thread
from threading import Event
from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop

DBusGMainLoop(set_as_default=True)

BUS_NAME = 'org.mpris.MediaPlayer2.netease-cloud-music'
OBJ_PATH = '/org/mpris/MediaPlayer2'
COMMAND_SOCKET_ADDR = '/tmp/command.sock'
PIPE_FILE_0 = '/tmp/nmc_panel_pipe_0'

playback_status_changed = Event()
s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)


def get_track_information(meta_data=None):
    if meta_data is None or dbus.String('xesam:artist') not in meta_data or dbus.String('xesam:title') not in meta_data:
        return {'artist': '', 'title': ''}
    artist = meta_data[dbus.String('xesam:artist')]
    if isinstance(artist, dbus.Array):
        artist = '/'.join(artist)
    title = str(meta_data[dbus.String('xesam:title')])
    return {'artist': artist, 'title': title}


class Player:

    def __init__(self):
        self._play_pause = None
        self._play_previous = None
        self._play_next = None
        self._playback_status = 'stop'
        self._track_information = get_track_information()
        self._is_available = False

    def is_available(self):
        return self._is_available

    def set_available(self, value):
        self._is_available = value

    def play_pause(self):
        if self._play_pause is not None:
            self._play_pause()

    def play_previous(self):
        if self._play_previous is not None:
            self._play_previous()

    def play_next(self):
        if self._play_next is not None:
            self._play_next()

    def set_methods(self, play_pause=None, play_previous=None, play_next=None):
        self._play_pause = play_pause
        self._play_previous = play_previous
        self._play_next = play_next

    def set_playback_status(self, playback_status='stop'):
        self._playback_status = playback_status

    def get_playback_status(self):
        return self._playback_status

    def set_track_information(self, track_information):
        self._track_information = track_information

    def get_track_information(self):
        return self._track_information


class BackgroundService(Thread):

    def __init__(self, bus_name, obj_path, pipe):
        Thread.__init__(self)
        self._bus_name = bus_name
        self._obj_path = obj_path
        self._player = Player()
        # self._playback_status_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        # self._track_information_socket_addr = TRACK_INFORMATION_SOCKET_ADDR
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self._session_bus = dbus.SessionBus()
        self._pipe = pipe
        if self._bus_name in self._session_bus.list_names():
            self._init_player_monitor()
        self._init_application_monitor()
        self._command_receiver = self._init_command_receiver()
        self._loop = GLib.MainLoop()

    def run(self) -> None:
        self._command_receiver.start()
        self._loop.run()

    def _set_track_information(self, new_track_information=None):
        old_track_information = self._player.get_track_information()
        for key in new_track_information:
            if old_track_information[key] != new_track_information[key]:
                self._player.set_track_information(new_track_information)
                self._pipe.write(str(new_track_information) + '\n')
                self._pipe.flush()
                return

    def _set_playback_status(self, new_playback_status):
        # self._player.set_playback_status(playback_status)
        # try:
        #     self._sock.sendto(self._player.get_playback_status().encode(),
        #                       self._playback_status_socket_addr)
        # except (FileNotFoundError, ConnectionRefusedError):
        #     print("socket file not available (playback_status)")
        if self._player.get_playback_status() != new_playback_status:
            self._player.set_playback_status(new_playback_status)
            playback_status_changed.set()

    def _init_application_monitor(self):

        def on_name_owner_changed(name, old_owner, new_owner):
            if name == BUS_NAME and not old_owner:
                self._init_player_monitor()
            elif name == BUS_NAME and not new_owner:
                self._properties_changed.remove()
                self._properties_changed = None
                self._set_track_information(get_track_information())
                self._set_playback_status('stop')

        self._session_bus.add_signal_receiver(on_name_owner_changed, 'NameOwnerChanged')

    def _init_player_monitor(self):

        def on_properties_changed(interface, changed_properties, invalidated_properties):
            if dbus.String('Metadata') in changed_properties:
                new_track_information = get_track_information(changed_properties[dbus.String('Metadata')])
                self._set_track_information(new_track_information)
            if dbus.String('PlaybackStatus') in changed_properties:
                new_playback_status = changed_properties[dbus.String('PlaybackStatus')]
                self._set_playback_status(new_playback_status)

        self._obj = self._session_bus.get_object(self._bus_name, self._obj_path)
        self._player_interface = dbus.Interface(self._obj, 'org.mpris.MediaPlayer2.Player')
        self._properties_interface = dbus.Interface(self._obj, 'org.freedesktop.DBus.Properties')
        self._properties_changed = self._properties_interface.connect_to_signal('PropertiesChanged',
                                                                                on_properties_changed)
        # get interfaces, methods and properties
        get_property = self._properties_interface.get_dbus_method('Get')
        play_pause = self._player_interface.get_dbus_method('PlayPause')
        play_previous = self._player_interface.get_dbus_method('Previous')
        play_next = self._player_interface.get_dbus_method('Next')
        meta_data = get_property('org.mpris.MediaPlayer2.Player', 'Metadata')
        playback_status = get_property('org.mpris.MediaPlayer2.Player', 'PlaybackStatus')
        self._player.set_methods(play_pause, play_previous, play_next)
        self._set_track_information(get_track_information(meta_data))
        self._set_playback_status(playback_status)

    def _init_command_receiver(self):

        class CommandReceiver(Thread):

            def __init__(self, player):
                Thread.__init__(self)
                self._player = player
                self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                self._command_socket = COMMAND_SOCKET_ADDR

            def run(self) -> None:
                if os.path.exists(self._command_socket):
                    os.unlink(self._command_socket)
                self._sock.bind(self._command_socket)
                while True:
                    command = self._sock.recv(1024).decode()
                    if command == 'play-pause':
                        self._player.play_pause()
                    elif command == 'play-previous':
                        self._player.play_previous()
                    elif command == 'play-next':
                        self._player.play_next()

        return CommandReceiver(self._player)

    def get_player(self):
        return self._player


def display_track_information():
    global scroll_list_updated
    track_information_changed = Event()
    scroll_list_current = []
    interval = 4

    def receive_track_information():
        widths = [
            (126, 1), (159, 0), (687, 1), (710, 0), (711, 1),
            (727, 0), (733, 1), (879, 0), (1154, 1), (1161, 0),
            (4347, 1), (4447, 2), (7467, 1), (7521, 0), (8369, 1),
            (8426, 0), (9000, 1), (9002, 2), (11021, 1), (12350, 2),
            (12351, 1), (12438, 2), (12442, 0), (19893, 2), (19967, 1),
            (55203, 2), (63743, 1), (64106, 2), (65039, 1), (65059, 0),
            (65131, 2), (65279, 1), (65376, 2), (65500, 1), (65510, 2),
            (120831, 1), (262141, 2), (1114109, 1),
        ]
        max_width = 20
        step = 5

        def get_width(o):
            """Return the screen column width for unicode ordinal o."""
            if o == 0xe or o == 0xf:
                return 0
            for num, wid in widths:
                if o <= num:
                    return wid
            return 1

        def cal_width(title_artist):
            width = [0]
            for (index, char) in enumerate(title_artist):
                width.append(width[index] + get_width(ord(char)))
            return width

        def set_scroll_list(title_artist):
            global scroll_list_updated

            scroll_list_updated = []

            if not title_artist:
                return

            width = cal_width(title_artist)
            # print(width)
            size = len(title_artist)
            index = step - max_width

            def truncate(start, end):
                pos_start = pos_end = -1
                fill_start = fill_end = 0
                for index in range(size + 1):
                    if pos_start == -1 and width[index] >= start:
                        pos_start = index
                        fill_start = 1 if width[index] > start else 0
                    if index + 1 <= size and pos_end == -1 and width[index + 1] >= end:
                        pos_end = index if width[index + 1] > end else index + 1
                        fill_end = 1 if width[index + 1] > end else 0

                    if pos_start != -1 and pos_end != -1:
                        break

                return f'{" " * fill_start}{title_artist[pos_start: pos_end]}{" " * fill_end}'

            while index < width[size]:
                start = index if index > 0 else 0
                end = index + max_width if index + max_width < width[size] else width[size]
                fill_start = abs(index) if index < 0 else 0
                fill_end = index + max_width - width[size] if index + max_width > width[size] else 0
                s = f'{" " * fill_start}{truncate(start, end)}{" " * fill_end}'
                scroll_list_updated.append(s)
                index += step

        while True:
            while not (os.path.exists(PIPE_FILE_0) and stat.S_ISFIFO(os.stat(PIPE_FILE_0).st_mode)):
                time.sleep(1)
            with open(PIPE_FILE_0) as fd:
                while True:
                    # fd = os.open(pipe_file, os.O_RDONLY)
                    data = fd.readline()
                    if not data:
                        break
                    track_information = eval(data)
                    if not track_information['artist'] and not track_information['title']:
                        title_artist = ''
                    else:
                        title_artist = f'{track_information["artist"]} - {track_information["title"]}'
                    set_scroll_list(title_artist)
                    track_information_changed.set()

    receiver = Thread(target=receive_track_information)
    receiver.start()

    import copy
    index = 0
    size = 0
    while True:
        if track_information_changed.is_set():
            scroll_list_current = copy.copy(scroll_list_updated)
            # print(scroll_list_updated)
            track_information_changed.clear()
            index = 0
            size = len(scroll_list_current)
        if size == 0:
            print('无歌曲信息')
        else:
            print(scroll_list_current[index % size])
            index += 1
        track_information_changed.wait(interval)


def display_playback_status():
    if os.path.exists(PIPE_FILE_0):
        os.unlink(PIPE_FILE_0)
    os.mkfifo(PIPE_FILE_0)
    with open(PIPE_FILE_0, 'w') as fd:
        background_service = BackgroundService(BUS_NAME, OBJ_PATH, pipe=fd)
        background_service.start()
        player = background_service.get_player()
        while True:
            playback_status_changed.clear()
            if player.get_playback_status().lower() == 'playing':
                print("")
            else:
                print("契")
            playback_status_changed.wait()


def send_command(command):
    try:
        s.sendto(command.encode(), COMMAND_SOCKET_ADDR)
    except (FileNotFoundError, ConnectionRefusedError):
        print("socket file not available (command)")


parser = argparse.ArgumentParser()
parser.add_argument('--command', type=str)
parser.add_argument('--display', type=str, default='track-information')
args = parser.parse_args()

if args.command is not None:
    send_command(args.command)
else:
    if args.display == 'track-information':
        display_track_information()
    elif args.display == 'playback-status':
        display_playback_status()

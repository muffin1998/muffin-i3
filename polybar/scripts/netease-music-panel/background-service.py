#!/usr/bin/env python

import dbus
import socket
import os
from threading import Thread
from threading import Event
from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop

DBusGMainLoop(set_as_default=True)

BUS_NAME = 'org.mpris.MediaPlayer2.netease-cloud-music'
OBJ_PATH = '/org/mpris/MediaPlayer2'

track_information_changed = Event()
playback_status_changed = Event()


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
        self._playback_status = 'Stop'
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

    def set_playback_status(self, playback_status='Stop'):
        self._playback_status = playback_status

    def get_playback_status(self):
        return self._playback_status

    def set_track_information(self, track_information):
        self._track_information = track_information

    def get_track_information(self):
        return self._track_information


class BackgroundService:

    def __init__(self, bus_name, obj_path):
        self._bus_name = bus_name
        self._obj_path = obj_path
        self._player = Player()
        # self._playback_status_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._playback_status_socket_addr = '/tmp/playback_status.sock'
        self._track_information_socket_addr = '/tmp/track_information.sock'
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self._session_bus = dbus.SessionBus()
        self._loop = GLib.MainLoop()

    def start(self):
        if self._bus_name in self._session_bus.list_names():
            self._init_player_monitor()
        self._init_application_monitor()
        command_receiver = self._init_command_receiver()
        command_receiver.start()
        self._loop.run()

    def _set_track_information(self, track_information=None):
        self._player.set_track_information(track_information)
        try:
            self._sock.sendto(str(self._player.get_track_information()).encode('utf-8'),
                              self._track_information_socket_addr)
        except (FileNotFoundError, ConnectionRefusedError):
            print("socket file not available (track_information)")

    def _set_playback_status(self, playback_status):
        self._player.set_playback_status(playback_status)
        try:
            self._sock.sendto(self._player.get_playback_status().encode(),
                              self._playback_status_socket_addr)
        except (FileNotFoundError, ConnectionRefusedError):
            print("socket file not available (playback_status)")

    def _init_application_monitor(self):

        def on_name_owner_changed(name, old_owner, new_owner):
            if name == BUS_NAME and not old_owner:
                self._init_player_monitor()
            elif name == BUS_NAME and not new_owner:
                self._properties_changed.remove()
                self._properties_changed = None
                self._set_track_information(get_track_information())
                self._set_playback_status('Stop')
                self._player.set_available(False)

        self._session_bus.add_signal_receiver(on_name_owner_changed, 'NameOwnerChanged')

    def _init_player_monitor(self):

        def on_properties_changed(interface, changed_properties, invalidated_properties):
            if dbus.String('Metadata') in changed_properties:
                track_information = self._player.get_track_information()
                new_track_information = get_track_information(changed_properties[dbus.String('Metadata')])
                for key in track_information:
                    if track_information[key] != new_track_information[key]:
                        self._set_track_information(new_track_information)
                        return
            if dbus.String('PlaybackStatus') in changed_properties:
                if changed_properties[dbus.String('PlaybackStatus')] != self._player.get_playback_status():
                    self._set_playback_status(changed_properties[dbus.String('PlaybackStatus')])
                    return

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
        self._player.set_available(True)

    def _init_command_receiver(self):

        class CommandReceiver(Thread):

            def __init__(self, player):
                Thread.__init__(self)
                self._player = player
                self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                self._command_socket = '/tmp/command.sock'

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

    def _init_subscriber_manager(self):

        class SubscriberManager(Thread):

            def __init__(self):
                Thread.__init__(self)

            def run(self) -> None:
                pass

    def get_player(self):
        return self._player


if __name__ == '__main__':
    # def on_properties_changed(interface, changed_properties, invalidated_properties):
    #     print(interface)
    #     print(changed_properties)
    #     print(invalidated_properties)
    #     print(dbus.String('PlaybackStatus') in changed_properties)
    # obj = dbus.SessionBus().get_object(BUS_NAME, OBJ_PATH)
    # properties_interface = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
    # properties_interface.connect_to_signal('PropertiesChanged', on_properties_changed)
    # loop = GLib.MainLoop()
    # loop.run()
    # introspect_interface = dbus.Interface(obj, 'org.freedesktop.DBus.Introspectable')
    # properties_interface = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
    # player_interface = dbus.Interface(obj, 'org.mpris.MediaPlayer2.Player')
    # introspect = introspect_interface.get_dbus_method('Introspect')
    # get_property = properties_interface.get_dbus_method('Get')
    # play = player_interface.get_dbus_method('Play')
    # pause = player_interface.get_dbus_method('Pause')
    # play_previous = player_interface.get_dbus_method('Previous')
    # play_next = player_interf#!/usr/bin/env python
    # # self._player.set_methods(play, pause, play_previous, play_next)
    # meta_data = get_property('org.mpris.MediaPlayer2.Player', 'Metadata')
    # playback_status = get_property('org.mpris.MediaPlayer2.Player', 'PlaybackStatus')
    # print(meta_data)
    # print(playback_status)
    # print(meta_data[dbus.String('xesam:title')])
    background_service = BackgroundService(BUS_NAME, OBJ_PATH)
    background_service.start()
    # import socket
    # s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # while True:
    #     track_information_changed.clear()
    #     print(player.get_track_information())
    #     s.sendto(player.get_playback_status().encode(), ('127.0.0.1', 8181))
    #     track_information_changed.wait(5)

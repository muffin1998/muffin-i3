#!/usr/bin/env -S python -u

# Note: /usr/bin/env -S option may not work on some platform,
# add python -u before script path in 'sources/module.ini' and use '#!/usr/bin/env python' instead

import argparse
import socket
import os
from threading import Thread, Event, Lock

playback_status_socket = '/tmp/playback_status.sock'
track_information_socket = '/tmp/track_information.sock'
command_socket = '/tmp/command.sock'
s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)


def unlink_socket(socket_file):
    if os.path.exists(socket_file):
        os.unlink(socket_file)


artist_title = ''
artist_title_len = 0


def display_track_information():
    max_width = 24
    step = 4
    interval = 3
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
    updated = Event()
    lock = Lock()

    def get_width(o):
        """Return the screen column width for unicode ordinal o."""
        global widths
        if o == 0xe or o == 0xf:
            return 0
        for num, wid in widths:
            if o <= num:
                return wid
        return 1

    def cal_width():
        width = 0
        for char in artist_title:
            width += get_width(ord(char))
        return width

    def truncate(index):
        pass

    def receive():
        global artist_title, artist_title_len
        unlink_socket(track_information_socket)
        s.bind(track_information_socket)
        while True:
            data = s.recv(1024).decode(encoding='utf-8')
            track_information = eval(data)
            lock.acquire()
            if not track_information['artist'] and not track_information['title']:
                artist_title = ''
            else:
                artist_title = f'{track_information["artist"]} - {track_information["title"]}'
                before = max_width - step
                after = len(artist_title) % step
                artist_title = f'{" " * before}{artist_title}{" " * after}'
                artist_title_len = len(artist_title)
            updated.set()
            lock.release()

    def display():
        index = max_width - step
        while True:
            lock.acquire()
            if updated.is_set():
                updated.clear()
                index = max_width - step
            if not artist_title:
                print('无歌曲信息')
            else:
                print(artist_title[index:index + max_width if index + max_width <= artist_title_len else artist_title_len],
                      end='')
                print(artist_title[0:index + max_width - artist_title_len if index + max_width > artist_title_len else 0])
                index = (index + step) % artist_title_len
            lock.release()
            updated.wait(interval)

    receiver = Thread(target=receive)
    receiver.start()
    # receive()
    display()


def display_playback_status():

    unlink_socket(playback_status_socket)
    s.bind(playback_status_socket)
    print("契")
    while True:
        playback_status = s.recv(1024).decode()
        if playback_status.lower() == 'playing':
            print("")
        else:
            print("契")


def send_command(command):

    try:
        s.sendto(command.encode(), command_socket)
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


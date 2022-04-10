#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import dbus
from dbus.mainloop.glib import DBusGMainLoop

from ..utils import temporary_directory

DBusGMainLoop(set_as_default=True)

CONTROLS = {
    "ALSA": {
        "mute": "amixer set Master -q mute",
        "unmute": "amixer set Master -q unmute",
        "up": "amixer set Master -q 1%+",
        "down": "amixer set Master -q 1%-"
    },
}

class Controls:
    ALSA = {
        "mute": "amixer set Master -q mute",
        "unmute": "amixer set Master -q unmute",
        "up": "amixer set Master -q 1%+",
        "down": "amixer set Master -q 1%-"
    }

def do_nothing(*args, **kwargs):
    """Do nothing"""
    pass

class DbusHandler:

    players = []
    driver = "ALSA"

    def __init__(self):
        self.tmp_directory = temporary_directory
        self.controls = getattr(Controls, self.driver, None)
        if self.controls is None:
            raise Exception("Unsupported driver: %s", self.driver)
        self.bus = dbus.SessionBus()
        self._getPlayerList()

    def _getPlayerList(self):
        for i in self.bus.list_names():
            if i.startswith("org.mpris.MediaPlayer2."):
                self.players.append(i)
    def _get_player_name(self, i, player):
        if i.startswith("org.mpris.MediaPlayer2."):
            return i[len("org.mpris.MediaPlayer2."):]
        else:
            return player.Get('org.mpris.MediaPlayer2',
                              'DesktopEntry',
                              dbus_interface='org.freedesktop.DBus.Properties')


class LinuxWrapper(DbusHandler):
    def __init__(self):
        super().__init__()

    def pause(self):
        player_names = []
        for i in self.players:
            player = self.bus.get_object(i, '/org/mpris/MediaPlayer2')
            player_status = player.Get('org.mpris.MediaPlayer2.Player',
                                       'PlaybackStatus',
                                       dbus_interface='org.freedesktop.DBus.Properties')
            if player_status == 'Playing':
                player_name = self._get_player_name(i, player)
                player_names.append(player_name)
                player.Pause(dbus_interface='org.mpris.MediaPlayer2.Player',
                             reply_handler=do_nothing, error_handler=do_nothing)
        if player_names != []:
            for i in os.listdir(self.tmp_directory+'/paused-players/'):

                os.remove(self.tmp_directory+'/paused-players/'+i)
            for player_name in player_names:
                player_status_file = open(self.tmp_directory+'/paused-players/'+player_name,
                                          "w")
                player_status_file.close()


    def play(self):
        for i in os.listdir(self.tmp_directory+'/paused-players/'):
            try:
                player = self.bus.get_object('org.mpris.MediaPlayer2.'+i,
                                        '/org/mpris/MediaPlayer2')
            except Exception:
                if i in os.listdir(self.tmp_directory+'/paused-players'):
                    os.remove(self.tmp_directory+'/paused-players/'+i)

            player_status = player.Get('org.mpris.MediaPlayer2.Player',
                                       'PlaybackStatus',
                                       dbus_interface='org.freedesktop.DBus.Properties')
            if player_status == 'Paused':
                player.Play(dbus_interface='org.mpris.MediaPlayer2.Player',
                            reply_handler=do_nothing, error_handler=do_nothing)
                if i in os.listdir(self.tmp_directory+'/paused-players'):
                    os.remove(self.tmp_directory+'/paused-players/'+i)


    def stop(self):
        for i in self.players:
            player = self.bus.get_object(i, '/org/mpris/MediaPlayer2')
            player_status = player.Get('org.mpris.MediaPlayer2.Player',
                                       'PlaybackStatus',
                                       dbus_interface='org.freedesktop.DBus.Properties')
            if player_status == 'Playing' or player_status == 'Stopped':
                player.Stop(dbus_interface='org.mpris.MediaPlayer2.Player',
                            reply_handler=do_nothing,
                            error_handler=do_nothing)


    def toggle(self):
        playing = False
        for i in self.players:
            player = self.bus.get_object(i, '/org/mpris/MediaPlayer2')
            player_status = player.Get('org.mpris.MediaPlayer2.Player',
                                       'PlaybackStatus',
                                       dbus_interface='org.freedesktop.DBus.Properties')
            if player_status == 'Playing':
                playing = True
        if playing:
            self.pause()
        else:
            self.play()


    def next(self):
        for i in self.players:
            player = self.bus.get_object(i, '/org/mpris/MediaPlayer2')
            player_status = player.Get('org.mpris.MediaPlayer2.Player',
                                       'PlaybackStatus',
                                       dbus_interface='org.freedesktop.DBus.Properties')
            if player_status == 'Playing':
                player.Next(dbus_interface='org.mpris.MediaPlayer2.Player',
                            reply_handler=do_nothing,
                            error_handler=do_nothing)


    def previous(self):
        for i in self.players:
            player = self.bus.get_object(i, '/org/mpris/MediaPlayer2')
            player_status = player.Get('org.mpris.MediaPlayer2.Player',
                                       'PlaybackStatus',
                                       dbus_interface='org.freedesktop.DBus.Properties')
            if player_status == 'Playing':
                player.Previous(dbus_interface='org.mpris.MediaPlayer2.Player',
                                reply_handler=do_nothing,
                                error_handler=do_nothing)

    def mute(self):
        os.system(CONTROLS[self.driver]["mute"])


    def unmute(self):
        os.system(CONTROLS[self.driver]["unmute"])


    def up(self):
        os.system(CONTROLS[self.driver]["up"])


    def down(self):
        os.system(CONTROLS[self.driver]["down"])

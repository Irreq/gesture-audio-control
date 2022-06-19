#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import subprocess

import dbus
from dbus.mainloop.glib import DBusGMainLoop

from .. import utils

"""
TODO:

+ Implement other backends other than alsa. -> VolumeControls._aggregate_soundcards
+ Get initial volume level from start. -> VolumeControls.__init__
"""

DBusGMainLoop(set_as_default=True)

CONTROLS = {
    "ALSA": {
        "mute": "amixer set Master -q mute",
        "unmute": "amixer set Master -q unmute",
        "up": "amixer set Master -q 1%+",
        "down": "amixer set Master -q 1%-"
    },
}

BLACKLIST = ["capture", "mic", "internal", "monitor", "beep", "mode", "iec958", "pcm", "loudness"]

WHITELIST = ["master", "usb audio"]

def check_software(cmd):
    try:
        if subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT):
            return True
    except:
        return False


# for name, value in {"pulseaudio": "pactl", "alsa": "amixer"}.items():
#     print(name, value)
#
# exit()

def output(cmd):
    os.system(cmd)

class Cards:

    class Alsa:
        pass

    class PulseAudio:
        def set_volume(percentage):
            cmd = f"pactl -- set-sink-volume 1 {percentage}%"
            output(cmd)

    class PipeWire:
        pass

    class Jack:
        pass

    def __init__(self, cards):
        # Aggregate cards
        self.cards = []
        for id in cards:
            card = getattr(self, id, None)
            if card is not None:
                self.card.append(card())



    def get_cards(self):
        pass

    def handle(self, function, args):
        for card in self.cards:
            f = getattr(card, function, None)
            if f is not None:
                try:
                    f(args)
                except Exception as e:
                    print(e)






class VolumeControls:
    """Handle multiple audio devices."""

    muted = False
    change = 1  # Percentage %
    percentage = 50  # initial value TODO

    def __init__(self, driver="alsa"):
        self.driver = driver
        self.debug = utils.debug
        self.soundcards = self._aggregate_soundcards()

        # self.test_soundcards = Cards("PulseAudio")

        if not self.soundcards:
            raise IOError("No soundcards could be detected, is `alsa` installed?")

        # print(list(self.soundcards.values()))
        # if "'Master'" in [k for i in self.soundcards.values() for k in i]:

        # print(r)

        # sys.exit(2)

    def get_initial_volume(self, card=None):
        cmd = "amixer get 'Master'"
        if card is not None:
            cmd = "amixer -c %d get 'Master'" % card

        try:
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
            candidates = []  # TODO: Can be separate audio levels, eg. bass or mid
            for match in re.findall(r"\[(\d{0,3})%\]", str(output)):
                candidates.append(int(match))

            self.percentage = max(candidates)
        except:
            self.percentage = 50





    def _aggregate_soundcards(self, blacklist=BLACKLIST, whitelist=WHITELIST):
        """Find the name of soundcards to use for audio control."""

        card_number = 0
        self.soundcards = {}

        while True:
            tmp_card = []
            try:
                output = subprocess.check_output(f"amixer -c {str(card_number)}",
                                                 shell=True,
                                                 stderr=subprocess.STDOUT)

                # Match only 'Master' and similar
                pattern = "(Simple mixer control) ('[A-Z][^']*['])"

                # Ignore blacklisted devices
                for _, match in re.findall(pattern, str(output)):
                    candidate = True
                    for item in blacklist:
                        if item in match.lower():
                            candidate = False
                            break
                    if not candidate:
                        continue

                    if match == "'Master'":
                        try:
                            self.get_initial_volume(card=card_number)
                        except Exception as e:
                            print(e)
                    tmp_card.append(match)

                    # for w_item in whitelist:
                    #     if w_item in match.lower():
                    #         tmp_card.append(match)
                    #         if match == "'Master'":
                    #             try:
                    #                 self.get_initial_volume(card=card_number)
                    #             except Exception as e:
                    #                 print(e)

                if any(tmp_card):
                    self.soundcards[card_number] = tmp_card
            except:
                break
            card_number += 1

        print(self.soundcards)

        return self.soundcards

    def volume_change(self, value, change=None):
        if change:
            self.change = change

        if self.percentage + value < 0 or self.percentage + value > 100:
            return
        else:
            self.percentage += value

        if self.driver == "alsa":
            for id in self.soundcards:
                for device in self.soundcards[id]:
                    # cmd = "amixer -c {0} set {1} -q {2}%{3}".format(id, device,
                    #                                                 self.change,
                    #                                                 value)
                    cmd = "amixer -c {0} set {1} -q {2}%".format(id, device,
                                                                 self.percentage)
                    # os.system(cmd)
                    # self.debug(cmd)

        self.set_volume()

    def mute(self):
        if not self.muted:
            self.muted = False

    def unmute(self):
        if self.muted:
            self.muted = True

    def set_volume(self):
        cmd = f"pactl -- set-sink-volume 1 {self.percentage}%"
        print(self.percentage, end="\r     ")
        os.system(cmd)
        # self.test_soundcards.handle("set_Volume", self.percentage)


def do_nothing(*args, **kwargs):
    """Do nothing"""
    pass

class DbusHandler:

    players = []
    # driver = "alsa"

    tmp_directory = utils.temporary_directory

    def __init__(self):
        # self.tmp_directory = temporary_directory
        # self.controls = getattr(Controls, self.driver, None)
        # if self.controls is None:
        #     raise Exception("Unsupported driver: %s", self.driver)
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


class LinuxWrapper(DbusHandler, VolumeControls):
    """Wrapper for Dbus and volume control."""
    def __init__(self):
        # Initiate DbusHandler and VolumeControls
        # for base_class in self.__class__.__bases__:
        #      base_class.__init__(self)
        DbusHandler.__init__(self)
        VolumeControls.__init__(self)

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

    # def mute(self):
    #     os.system(CONTROLS[self.driver]["mute"])
    #
    #
    # def unmute(self):
    #     os.system(CONTROLS[self.driver]["unmute"])


    def up(self):
        self.volume_change(self.change)


    def down(self):
        self.volume_change(-self.change)

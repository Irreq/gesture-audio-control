#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import platform

from .. import utils

name = platform.system()

if name == "Linux":
    utils.temporary_directory = "/tmp/PythonGestureAudioController"
    from .linux import LinuxWrapper as AudioWrapper

elif name == "Darwin":
    utils.temporary_directory = "/tmp/PythonGestureAudioController"
    from .darwin import DarwinWrapper as AudioWrapper

elif name == "Windows":
    utils.temporary_directory = "/tmp/PythonGestureAudioController"
    from .windows import WindowsWrapper as AudioWrapper

else:
    print("Unsupported Operating System: %s, Abborting." % name)
    sys.exit(0)


"""Initial check of temporary files"""
if not os.path.isdir(utils.temporary_directory):
    os.makedirs(utils.temporary_directory)
    if not os.path.isdir(utils.temporary_directory+'/players'):
        os.makedirs(utils.temporary_directory+'/players')
    if not os.path.isdir(temporary_directory+'/paused-players'):
        os.makedirs(utils.temporary_directory+'/paused-players')
    if not os.path.isfile(temporary_directory+'/driver'):
        with open(utils.temporary_directory+'/driver', 'a'):
            os.utime(utils.temporary_directory+'/driver', None)
        # with open(utils.temporary_directory+'/driver', 'w') as f:
        #     f.write("ALSA")
        #     f.close()

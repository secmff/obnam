# Copyright (C) 2007  Lars Wirzenius <liw@iki.fi>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


"""Misc. utility functions for Obnam"""


import os


def make_stat_result(st_mode=0, st_ino=0, st_dev=0, st_nlink=0, st_uid=0,
                     st_gid=0, st_size=0, st_atime=0, st_mtime=0, st_ctime=0,
                     st_blocks=0, st_blksize=0, st_rdev=0):

    dict = {
        "st_mode": st_mode,
        "st_ino": st_ino,
        "st_dev": st_dev,
        "st_nlink": st_nlink,
        "st_uid": st_uid,
        "st_gid": st_gid,
        "st_size": st_size,
        "st_atime": st_atime,
        "st_mtime": st_mtime,
        "st_ctime": st_ctime,
        "st_blocks": st_blocks,
        "st_blksize": st_blksize,
        "st_rdev": st_rdev,
    }
    
    tup = (st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid, st_size,
           st_atime, st_mtime, st_ctime)

    return os.stat_result(tup, dict)


def create_file(filename, contents):
    """Create a new file with the given contents.
    
    If the file already exists, the existing contents are overwritten.
    
    """
    
    f = file(filename, "w")
    f.write(contents)
    f.close


def read_file(filename):
    """Return the contents of a file."""
    f = file(filename)
    contents = f.read()
    f.close()
    return contents


# The following sets up the Guppy/Heapy memory use profiler for easy use.
# If it's not available, the update_heapy() function won't do anything.
try: # pragma: no cover
    import guppy
except ImportError: # pragma: no cover
    def update_heapy(msg, f=None):
        pass
else: #pragma: no cover
    heapy = guppy.hpy()
    import sys
    def update_heapy(msg, f=sys.stdout):
        f.write("\n============================\n%s:\n%s\n\n" % 
                (msg, heapy.heap()))
        heapy.setref()

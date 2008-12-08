# Copyright (C) 2008  Lars Wirzenius <liw@liw.fi>
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


import unittest

import obnamlib


class DirTests(unittest.TestCase):

    def setUp(self):
        self.dir = obnamlib.Dir(id="id", name="name", 
                                dirrefs=["dir1", "dir2"],
                                fgrefs=["fg1", "fg2"])

    def test_sets_name_correctly(self):
        self.assertEqual(self.dir.name, "name")

    def test_sets_dirrefs_correctl(self):
        self.assertEqual(self.dir.dirrefs, ["dir1", "dir2"])

    def test_sets_fgrefs_correctl(self):
        self.assertEqual(self.dir.fgrefs, ["fg1", "fg2"])

    def test_prepare_encodes_name(self):
        self.dir.prepare_for_encoding()
        self.assertEqual(self.dir.find_strings(kind=obnamlib.FILENAME), 
                         ["name"])

    def test_prepare_encodes_dirrefs(self):
        self.dir.prepare_for_encoding()
        self.assertEqual(self.dir.find_strings(kind=obnamlib.DIRREF), 
                         ["dir1", "dir2"])

    def test_prepare_encodes_fgrefs(self):
        self.dir.prepare_for_encoding()
        self.assertEqual(self.dir.find_strings(kind=obnamlib.FILEGROUPREF), 
                         ["fg1", "fg2"])
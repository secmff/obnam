# Copyright (C) 2010  Lars Wirzenius
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import logging
import os
import stat
import time

import obnamlib


class FsckPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.register_command('fsck', self.fsck)
        
    def fsck(self, args):
        self.app.config.require('store')
        logging.debug('fsck on %s' % self.app.config['store'])

        storefs = self.app.fsf.new(self.app.config['store'])
        storefs.connect()
        self.store = obnamlib.Store(storefs)
        
        self.check_root()

    def check_root(self):
        '''Check the root node.'''
        logging.debug('Checking root node')
        self.app.hooks.call('status', 'Checking root node')
        for host in self.store.list_hosts():
            self.check_host(host)
    
    def check_host(self, hostname):
        '''Check a host.'''
        logging.debug('Checking host %s' % hostname)
        self.app.hooks.call('status', 'Checking host %s' % hostname)
        self.store.open_host(hostname)
        for genid in self.store.list_generations():
            self.check_generation(genid)

    def check_generation(self, genid):
        '''Check a generation.'''
        logging.debug('Checking generation %s' % genid)
        self.app.hooks.call('status', 'Checking generation %s' % genid)


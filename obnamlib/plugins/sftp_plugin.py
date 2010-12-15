# Copyright (C) 2009  Lars Wirzenius <liw@liw.fi>
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


import errno
import logging
import os
import pwd
import random
import socket
import stat
import subprocess
import urlparse

# As of 2010-07-10, Debian's paramiko package triggers
# RandomPool_DeprecationWarning. This will eventually be fixed. Until
# then, there is no point in spewing the warning to the user, who can't
# do nothing.
# http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=586925
import warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    import paramiko

import obnamlib


DEFAULT_SSH_PORT = 22


def ioerror_to_oserror(method):
    '''Decorator to convert an IOError exception to OSError.
    
    Python's os.* raise OSError, mostly, but paramiko's corresponding
    methods raise IOError. This decorator fixes that.
    
    '''
    
    def helper(self, filename, *args, **kwargs):
        try:
            return method(self, filename, *args, **kwargs)
        except IOError, e:
            raise OSError(e.errno, e.strerror, filename)
    
    return helper


class SSHChannelAdapter(object):

    '''Take an ssh subprocess and pretend it is a paramiko Channel.'''
    
    # This is inspired by the ssh.py module in bzrlib.

    def __init__(self, proc):
        self.proc = proc

    def send(self, data):
        return os.write(self.proc.stdin.fileno(), data)

    def recv(self, count):
        try:
            return os.read(self.proc.stdout.fileno(), count)
        except socket.error, e:
            if e.args[0] in (errno.EPIPE, errno.ECONNRESET, errno.ECONNABORTED,
                             errno.EBADF):
                # Connection has closed.  Paramiko expects an empty string in
                # this case, not an exception.
                return ''
            raise

    def get_name(self):
        return 'obnam SSHChannelAdapter'

    def close(self):
        for func in [self.proc.stdin.close, self.proc.stdout.close, 
                     self.proc.wait]:
            try:
                func()
            except OSError:
                pass


class SftpFS(obnamlib.VirtualFileSystem):

    '''A VFS implementation for SFTP.
    
    
    
    '''

    def __init__(self, baseurl):
        obnamlib.VirtualFileSystem.__init__(self, baseurl)
        self.sftp = None
        self.reinit(baseurl)
        
    def connect(self):
        if not self._connect_openssh():
            self._connect_paramiko()
        self.chdir(self.path)

    def _connect_paramiko(self):
        self.transport = paramiko.Transport((self.host, self.port))
        self.transport.connect()
        self._check_host_key(self.host)
        self._authenticate(self.user)
        self.sftp = paramiko.SFTPClient.from_transport(self.transport)

    def _connect_openssh(self):
        args = ['ssh',
                '-oForwardX11=no', '-oForwardAgent=no',
                '-oClearAllForwardings=yes', '-oProtocol=2',
                '-p', str(self.port),
                '-l', self.user,
                '-s', self.host, 'sftp']

        try:
            proc = subprocess.Popen(args,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    close_fds=True)
        except OSError:
            return False

        self.transport = None
        self.sftp = paramiko.SFTPClient(SSHChannelAdapter(proc))
        return True

    def _check_host_key(self, hostname):
        key = self.transport.get_remote_server_key()
        known_hosts = os.path.expanduser('~/.ssh/known_hosts')
        keys = paramiko.util.load_host_keys(known_hosts)
        if hostname not in keys:
            raise obnamlib.AppException('Host not in known_hosts: %s' % 
                                        hostname)
        elif not keys[hostname].has_key(key.get_name()):
            raise obnamlib.AppException('No host key for %s' % hostname)
        elif keys[hostname][key.get_name()] != key:
            raise obnamlib.AppException('Host key has changed for %s' % 
                                        hostname)
    
    def _authenticate(self, username):
        agent = paramiko.Agent()
        agent_keys = agent.get_keys()
        for key in agent_keys:
            try:
                self.transport.auth_publickey(username, key)
                return
            except paramiko.SSHException:
                pass
        raise obnamlib.AppException('Can\'t authenticate to SSH server '
                                    'using agent.')

    def close(self):
        self.sftp.close()
        if self.transport:
            self.transport.close()
            self.transport = None
        self.sftp = None
        logging.info('VFS %s closing down; bytes_read=%d bytes_written=%d' %
                     (self.baseurl, self.bytes_read, self.bytes_written))

    def reinit(self, baseurl):
        scheme, netloc, path, query, fragment = urlparse.urlsplit(baseurl)

        if scheme != 'sftp':
            raise obnamlib.Error('SftpFS used with non-sftp URL: %s' % baseurl)

        if '@' in netloc:
            user, netloc = netloc.split('@', 1)
        else:
            user = self._get_username()

        if ':' in netloc:
            host, port = netloc.split(':', 1)
            port = int(port)
        else:
            host = netloc
            port = DEFAULT_SSH_PORT

        if path.startswith('/~/'):
            path = path[3:]

        self.host = host
        self.port = port
        self.user = user
        self.path = path
        
        if self.sftp:
            self.sftp.chdir(path)

    def _get_username(self):
        return pwd.getpwuid(os.getuid()).pw_name

    def getcwd(self):
        return self.sftp.getcwd()

    @ioerror_to_oserror
    def chdir(self, pathname):
        self.sftp.chdir(pathname)

    @ioerror_to_oserror
    def listdir(self, pathname):
        return self.sftp.listdir(pathname)

    def lock(self, lockname):
        try:
            self.write_file(lockname, '')
        except IOError, e:
            if e.errno == errno.EEXIST:
                raise obnamlib.AppException('Lock %s already exists' % 
                                            lockname)
            else:
                raise

    def unlock(self, lockname):
        if self.exists(lockname):
            self.remove(lockname)

    def exists(self, pathname):
        try:
            self.lstat(pathname)
        except OSError:
            return False
        else:
            return True

    def isdir(self, pathname):
        try:
            st = self.lstat(pathname)
        except OSError:
            return False
        else:
            return stat.S_ISDIR(st.st_mode)

    @ioerror_to_oserror
    def mkdir(self, pathname):
        self.sftp.mkdir(pathname)
        
    @ioerror_to_oserror
    def makedirs(self, pathname):
        parent = os.path.dirname(pathname)
        if parent and parent != pathname and not self.exists(parent):
            self.makedirs(parent)
        self.mkdir(pathname)

    @ioerror_to_oserror
    def rmdir(self, pathname):
        self.sftp.rmdir(pathname)
        
    @ioerror_to_oserror
    def remove(self, pathname):
        self.sftp.remove(pathname)

    @ioerror_to_oserror
    def rename(self, old, new):
        if self.exists(new):
            self.remove(new)
        self.sftp.rename(old, new)
    
    @ioerror_to_oserror
    def lstat(self, pathname):
        return self.sftp.lstat(pathname)

    @ioerror_to_oserror
    def chown(self, pathname, uid, gid):
        self.sftp.chown(pathname, uid, gid)
        
    @ioerror_to_oserror
    def chmod(self, pathname, mode):
        self.sftp.chmod(pathname, mode)
        
    @ioerror_to_oserror
    def lutimes(self, pathname, atime, mtime):
        # FIXME: This does not work for symlinks!
        # Sftp does not have a way of doing that. This means if the restore
        # target is over sftp, symlinks and their targets will have wrong
        # mtimes.
        if getattr(self, 'lutimes_warned', False):
            logging.warning('lutimes used over SFTP, this does not work '
                            'against symlinks (warning appears only first '
                            'time)')
            self.lutimes_warned = True
        self.sftp.utime(pathname, (atime, mtime))

    def link(self, existing_path, new_path):
        raise obnamlib.AppException('Cannot hardlink on SFTP. Sorry.')

    def readlink(self, symlink):
        return self.sftp.readlink(symlink)

    @ioerror_to_oserror
    def symlink(self, source, destination):
        self.sftp.symlink(source, destination)

    def open(self, pathname, mode):
        return self.sftp.file(pathname, mode)

    def cat(self, pathname):
        f = self.open(pathname, 'r')
        chunks = []
        while True:
            # 32 KiB is the chunk size that gives me the fastest speed
            # for sftp transfers. I don't know why the size matters.
            chunk = f.read(32 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
            self.bytes_read += len(chunk)
        f.close()
        return ''.join(chunks)

    def write_file(self, pathname, contents):
        if self.exists(pathname):
            raise OSError(errno.EEXIST, 'File exists', pathname)
        self._write_helper(pathname, 'wx', contents)

    def _tempfile(self, dirname):
        '''Generate a filename that does not exist.
        
        This is _not_ as safe as tempfile.mkstemp. Plenty of race
        conditions. But seems to be as good as SFTP will allow.
        
        '''
        
        while True:
            i = random.randint(0, 2**64-1)
            basename = 'tmp.%x' % i
            pathname = os.path.join(dirname, basename)
            if not self.exists(pathname):
                return pathname

    def overwrite_file(self, pathname, contents, make_backup=True):
        dirname = os.path.dirname(pathname)
        tempname = self._tempfile(dirname)
        self._write_helper(tempname, 'wx', contents)

        # Rename existing to have a .bak suffix. If _that_ file already
        # exists, remove that.
        bak = pathname + ".bak"
        try:
            self.remove(bak)
        except OSError:
            pass
        if self.exists(pathname):
            self.rename(pathname, bak)
        self.rename(tempname, pathname)
        if not make_backup:
            try:
                self.remove(bak)
            except OSError:
                pass
        
    def _write_helper(self, pathname, mode, contents):
        dirname = os.path.dirname(pathname)
        if dirname and not self.exists(dirname):
            self.makedirs(dirname)
        f = self.open(pathname, mode)
        chunk_size = 32 * 1024
        for pos in range(0, len(contents), chunk_size):
            chunk = contents[pos:pos + chunk_size]
            f.write(chunk)
            self.bytes_written += len(chunk)
        f.close()


class SftpPlugin(obnamlib.ObnamPlugin):

    def enable(self):
        self.app.fsf.register('sftp', SftpFS)

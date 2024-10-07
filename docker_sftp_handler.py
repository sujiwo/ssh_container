'''
Created on Oct 4, 2024

@author: sujiwo
'''

import os
import errno
from paramiko import SFTPHandle, SFTPServer
from paramiko.sftp import SFTP_OP_UNSUPPORTED, SFTP_OK


class Docker_SFTP_Handle (SFTPHandle):
    def __init__(self, si, flags=0):
        super().__init__(flags)
        self.__tell = None
        self.interface = si
    
    def close(self):
        pass
    
    # XXX: Use /bin/dd to read & write data
    # please use coreutils' dd
    # not Busybox' dd
    def write(self, offset, data):
        ddcmd = ['/bin/dd',
                 'of={}'.format(self.filename),
                 'seek={}B'.format(offset),
                 'count={}B'.format(len(data))]
        handle = self.interface.exec_write(ddcmd)
        handle[1].send(data)
        if self.__tell is None:
            self.__tell = offset
        else:
            self.__tell += len(data)
        return SFTP_OK
    
    def read(self, offset, length):
        ddcmd = ['/bin/dd',
                 'if={}'.format(self.filename),
                 'skip={}B'.format(offset),
                 'count={}B'.format(length)]
        outs = self.interface.exec_collect(ddcmd)
        if outs[0]!=0:
            return SFTPServer.convert_errno(errno.EPERM)
        return bytes(outs[1])
    
    def stat(self):
        return self.interface.stat(self.filename)

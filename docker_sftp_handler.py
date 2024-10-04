'''
Created on Oct 4, 2024

@author: sujiwo
'''

import os
import errno
from paramiko import SFTPHandle, SFTPServer


class Docker_SFTP_Handle (SFTPHandle):
    def __init__(self, si, flags=0):
        self.interface = si
        pass
    
    def close(self):
        pass
    
    # XXX: Use /bin/dd to read & write data
    # please use coreutils' dd
    # not Busybox' dd
    def write(self, offset, data):
        pass
    
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

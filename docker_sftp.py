'''
Created on Sep 30, 2024

@author: sujiwo
'''

import os
from pathlib import Path
import docker
from paramiko import ServerInterface, SFTPServerInterface, SFTPServer, SFTPAttributes, \
    SFTPHandle, SFTP_OK, AUTH_SUCCESSFUL, OPEN_SUCCEEDED
    
    
statcmd = ['/bin/stat', '-c',
           '%n %u %g %U %G %f %s %X %Y']
    

def parse_ls(raw_output, target_dir='/'):
    lines = raw_output.split('\n')
    for l in lines:
        if len(l)>0:
            pass

def parse_terse_stats(raw_output):
    lines = raw_output.split(b'\n')
    lines.pop()
    attributes = []
    for l in lines:
        els = l.split(b' ')
        attr = SFTPAttributes()
        attr.filename = os.path.basename( els[0].decode('utf-8') )
        attr.st_size = int(els[6])
        attr.st_uid = int(els[1])
        attr.st_gid = int(els[2])
        attr.st_mode = int(els[5], 16)
        attr.st_atime = int(els[7])
        attr.st_mtime = int(els[8])
        attributes.append(attr)
    return attributes


class Docker_SFTP_Handle (SFTPHandle):
    def __init__(self, flags=0):
        pass
    
    # XXX: Use /bin/dd to read & write data
    def write(self, offset, data):
        pass
    
    def read(self, offset, length):
        pass
    
    # def stat


class Docker_SFTP_Server (SFTPServerInterface):
    
    def __init__(self, server, *args, **kwargs):
        self.container = server.container
        
    def session_started(self):
        SFTPServerInterface.session_started(self)
        
    def session_ended(self):
        SFTPServerInterface.session_ended(self)
        
    def canonicalize(self, path):
        return SFTPServerInterface.canonicalize(self, path)
    
    def list_folder(self, path):
        buffer = self.exec_collect(['/bin/ls', path])
        lines = buffer.split(b'\n')
        lines.pop()
        for i in range(len(lines)):
            lines[i] = path+'/'+lines[i].decode('utf-8')
        buffer = self.exec_collect([*statcmd, *lines])
        fst = parse_terse_stats(buffer)
        return fst
    
    # XXX: should also return exit status
    def exec_collect(self, cmds):
        # cmds must be in unicode, but output will in bytes
        outs = self.container.exec_run(cmds, stream=True)
        buffer = bytearray()
        for c in outs.output:
            buffer += c
        return buffer
    
    def stat(self, path):
        path = self.realpath(path).rstrip()
        buffer = self.exec_collect([*statcmd, path])
        fst = parse_terse_stats(buffer)
        return fst[0]
    
    def realpath(self, path):
        buffer = self.exec_collect(['/bin/realpath', path])
        return buffer.decode('utf-8')
    
    def open(self, path, flags, attr):
        path = os.path.realpath(path)
        
        pass
    
    

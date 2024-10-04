'''
Created on Sep 30, 2024

@author: sujiwo
'''

import os
import errno
from pathlib import Path
import docker
from paramiko import ServerInterface, SFTPServerInterface, SFTPServer, SFTPAttributes, \
    SFTPHandle, SFTP_OK, AUTH_SUCCESSFUL, OPEN_SUCCEEDED
from docker_sftp_handler import Docker_SFTP_Handle 
    
    
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
        o = self.exec_collect(['/bin/ls', path])
        if o[0]!=0 :
            return SFTPServer.convert_errno(o[0])
        buffer = o[1]
        lines = buffer.split(b'\n')
        lines.pop()
        for i in range(len(lines)):
            lines[i] = path+'/'+lines[i].decode('utf-8')
        buffer = self.exec_collect([*statcmd, *lines])[1]
        fst = parse_terse_stats(buffer)
        return fst
    
    # XXX: should also return exit status
    def exec_collect(self, cmds):
        output = [0, bytearray()]
        # cmds must be in unicode, but output will in bytes
        outs = self.container.exec_run(cmds, stream=True, stdout=True, stderr=False)
        if outs[0] is None:
            output[0] = 0
        else:
            output[0] = outs[0]
        for c in outs.output:
            output[1] += c
        return output
    
    def stat(self, path):
        path = os.path.realpath(path)
        out = self.exec_collect([*statcmd, path])
        if out[0]!=0:
            return SFTPServer.convert_errno(out[0])
        fst = parse_terse_stats(out[1])
        return fst[0]
    
    def lstat(self, path):
        return self.stat(path)
    
    def realpath(self, path):
        buffer = self.exec_collect(['/bin/realpath', path])
        return buffer.decode('utf-8')
    
    def open(self, path, flags, attr):
        path = os.path.realpath(path)

        # Check if file already exist
        # | Command | Description              |
        # |---------|--------------------------|
        # | -e      | File/directory exists    |
        # | -f      | is a file                |
        # | -d      | is a directory           |
        # | -s      | File size greater than 0 |
        # | -L      | is a link                |
        # | -S      | is a socket              |
        
        outs = self.exec_collect('[ -e "$PATH" ]')[0] 
        if outs != 0:
            if flags & os.O_RDONLY:
                return SFTPServer.convert_errno(errno.ENOENT)
        hdl = Docker_SFTP_Handle(self, flags)
        hdl.filename = path
        return hdl
    

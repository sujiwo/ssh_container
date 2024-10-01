'''
Created on Sep 30, 2024

@author: sujiwo
'''
import os
import docker
from paramiko import ServerInterface, SFTPServerInterface, SFTPServer, SFTPAttributes, \
    SFTPHandle, SFTP_OK, AUTH_SUCCESSFUL, OPEN_SUCCEEDED
    

class Docker_SFTP_Handle (SFTPHandle):
    pass


class Docker_SFTP_Server (SFTPServerInterface):
    def __init__(self, server):
        self.dockercli = server.containerName
    
    def list_folder(self, path):
        return SFTPServerInterface.list_folder(self, path)
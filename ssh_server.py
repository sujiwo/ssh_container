#!/usr/bin/python3

import os
import paramiko
import socket
import sys
import threading
import traceback
import selectors
from docker import DockerClient
from docker_sftp import *


CWD = os.path.dirname(os.path.realpath(__file__))
HOSTKEY = paramiko.RSAKey(filename='/home/sujiwo/.ssh/servers/server_rsa.key')
SSH_BANNER = "SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.3"
dockerCli = DockerClient('ssh://eowyn.local')

# TODO: Replace threading with multiprocessing

class Server(paramiko.ServerInterface):
    # dockerHost = 
    containerName = 'jp1'
    
    def __init__(self, _cli):
        self.dockerCli = _cli
        self.event = threading.Event()
        self.container = None
        self.shellRequest = False
        
    def get_allowed_auths(self, username):
        return 'password'
        
    def check_channel_request(self, kind, chanid):
        if kind=='session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
    
    def check_auth_password(self, username, password):
        if (username=='whoami') and (password=='secret'):
            self.container = self.dockerCli.containers.get(self.containerName)
            return paramiko.AUTH_SUCCESSFUL
        # XXX: Perform user authorization from here 
        
    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        channel.set_combine_stderr(True)
        self.stdouterr = channel.makefile_stderr()
        self.stdin = channel.makefile_stdin()
        self.width= width
        self.height = height
        return True
    
    def check_channel_shell_request(self, channel):
        _, self.dockersock = self.container.exec_run('/bin/bash -l', stdin=True, stdout=True, stderr=True, tty=True, socket=True)
        print("Logged in")
        self.event.set()
        self.shellRequest = True
        return True
    
    def shell_session(self, channel):
        poller = selectors.DefaultSelector()
        poller.register(channel.fileno(), selectors.EVENT_READ, 1)
        poller.register(self.dockersock.fileno(), selectors.EVENT_READ, 2)

        try:
            channel.send("Welcome to the my control server\r\n\r\n")
            run = True
            while run:
                events = poller.select()
                for key,_ in events:
                    if key.data==1:
                        cmd = channel.recv(1024)
                        if len(cmd)==0:
                            run = False
                            break
                        self.dockersock.send(cmd)
                    elif key.data==2:
                        cmd = self.dockersock.recv(1024)
                        if len(cmd)==0:
                            run = False
                            break
                        channel.send(cmd)

        except Exception as err:
            print('!!! Exception: {}: {}'.format(err.__class__, err))
            traceback.print_exc()
            try:
                channel.transport.close()
            except Exception:
                pass
    

def start_server(port, address):
    """Init and run the ssh server"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((address, port))
    except Exception as err:
        print('*** Bind failed: {}'.format(err))
        traceback.print_exc()
        sys.exit(1)

    threads = []
    while True:
        try:
            sock.listen(100)
            print('Listening for connection ...')
            client, addr = sock.accept()
        except Exception as err:
            print('*** Listen/accept failed: {}'.format(err))
            traceback.print_exc()
        new_thread = threading.Thread(target=handle_connection, args=(client, addr))
        new_thread.start()
        threads.append(new_thread)

    for thread in threads:
        thread.join()

def handle_connection(connection, addr):
    """Handle a new ssh connection"""
#    LOG.write("\n\nConnection from: " + addr[0] + "\n")
    print('Got a connection!')
    try:
        transport = paramiko.Transport(connection)
        transport.add_server_key(HOSTKEY)
        # Change banner to appear legit on nmap (or other network) scans
        transport.local_version = SSH_BANNER
        transport.set_subsystem_handler('sftp', paramiko.SFTPServer, Docker_SFTP_Server)
        server = Server(dockerCli)
        try:
            transport.start_server(server=server)
        except paramiko.SSHException:
            print('*** SSH negotiation failed.')
            raise Exception("SSH negotiation failed")
        # wait for auth
        chan = transport.accept(20)
        if chan is None:
            print('*** No channel.')
            raise Exception("No channel")
        
        server.event.wait(10)
        if server.shellRequest==True:
            server.shell_session(chan)        
            chan.close()

    except Exception as err:
        print('!!! Exception: {}: {}'.format(err.__class__, err))
        traceback.print_exc()
        try:
            transport.close()
        except Exception:
            pass

if __name__=='__main__':
    address = '127.0.0.1'
    port = 2222
    start_server(port, address)
    pass

    
    

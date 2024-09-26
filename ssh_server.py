#!/usr/bin/python3

import os
import paramiko
import socket
import sys
import threading
import traceback
import selectors
from docker import DockerClient


CWD = os.path.dirname(os.path.realpath(__file__))
HOSTKEY = paramiko.RSAKey(filename='/home/sujiwo/.ssh/servers/server_rsa.key')
SSH_BANNER = "SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.3"
dockerConn = DockerClient('ssh://172.17.69.69')


class Server(paramiko.ServerInterface):
    def __init__(self):
        self.event = threading.Event()
        
    def get_allowed_auths(self, username):
        return 'password'
        
    def check_channel_request(self, kind, chanid):
        if kind=='session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
    
    def check_auth_password(self, username, password):
        if (username=='whoami') and (password=='secret'):
            return paramiko.AUTH_SUCCESSFUL
        
    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        channel.set_combine_stderr(True)
        self.stdouterr = channel.makefile_stderr()
        self.stdin = channel.makefile_stdin()
        return True
    
    def check_channel_shell_request(self, channel):
        _, self.dockersock = dockerConn.containers.get('jp1').exec_run('/bin/bash', stdin=True, stdout=True, stderr=True, socket=True)
        self.event.set()
        return True
    
    # def check_channel_shell_request(self, channel):
    #     return True
    
    
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

def handle_connection(client, addr):
    """Handle a new ssh connection"""
#    LOG.write("\n\nConnection from: " + addr[0] + "\n")
    print('Got a connection!')
    try:
        transport = paramiko.Transport(client)
        transport.add_server_key(HOSTKEY)
        # Change banner to appear legit on nmap (or other network) scans
        transport.local_version = SSH_BANNER
        server = Server()
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
        if not server.event.is_set():
            print('*** Client never asked for a shell.')
            raise Exception("No shell request")
        
        poller = selectors.DefaultSelector()
        poller.register(chan.fileno(), selectors.EVENT_READ, 1)
        poller.register(server.dockersock.fileno(), selectors.EVENT_READ, 2)

        try:
            chan.send("Welcome to the my control server\r\n\r\n")
            run = True
            cmd = bytearray()
            while run:
                events = poller.select()
                for key,_ in events:
                    if key.data==1:
                        bt = chan.recv(1024)
                        chan.send(bt)
                        cmd = cmd+bt
                        if cmd.decode("utf-8").endswith("\r"):
                            chan.send("\r\n")
                            cmd = cmd.rstrip()
                            # XXX: Inefficient; should send bytes to shell
                            cmd = cmd.decode("utf-8")
                            print("Sending: "+cmd)
                            server.dockersock.send(cmd+"\n")
                            cmd = bytearray()
                    elif key.data==2:
                        bt = server.dockersock.recv(1024)
                        chan.send(bt)
                # XXX: Handle exit
                
#                 chan.send("$ ")
#                 command = ""
#                 while not command.endswith("\r"):
#                     transport = chan.recv(1024)
#                     # Echo input to psuedo-simulate a basic terminal
#                     chan.send(transport)
#                     command += transport.decode("utf-8")
#
#                 chan.send("\r\n")
#                 command = command.rstrip()
# #                LOG.write("$ " + command + "\n")
#                 print(command)
#                 if command == "exit":
#                     run = False
#                 else:
#                     handle_cmd(command, chan)

        except Exception as err:
            print('!!! Exception: {}: {}'.format(err.__class__, err))
            traceback.print_exc()
            try:
                transport.close()
            except Exception:
                pass

        chan.close()

    except Exception as err:
        print('!!! Exception: {}: {}'.format(err.__class__, err))
        traceback.print_exc()
        try:
            transport.close()
        except Exception:
            pass

def handle_cmd(cmd, chan):
    """Branching statements to handle and prepare a response for a command"""
    response = ""
    if cmd.startswith("sudo"):
        send_ascii("sudo.txt", chan)
        return
    elif cmd.startswith("ls"):
        response = "pw.txt"
    elif cmd.startswith("version"):
        response = "Super Amazing Awesome (tm) Shell v1.1"
    elif cmd.startswith("pwd"):
        response = "/home/clippy"
    elif cmd.startswith("cd"):
        send_ascii("cd.txt", chan)
        return
    elif cmd.startswith("cat"):
        send_ascii("cat.txt", chan)
        return
    elif cmd.startswith("rm"):
        send_ascii("bomb.txt", chan)
        response = "You blew up our files! How could you???"
    elif cmd.startswith("whoami"):
        send_ascii("wizard.txt", chan)
        response = "You are a wizard of the internet!"
    elif ".exe" in cmd:
        response = "Hmm, trying to access .exe files from an ssh terminal..... Your methods are unconventional"
    elif cmd.startswith("cmd"):
        response = "Command Prompt? We only use respectable shells on this machine.... Sorry"
    elif cmd == "help":
        send_ascii("help.txt", chan)
        return
    else:
        send_ascii("clippy.txt", chan)
        response = "Use the 'help' command to view available commands"

    # LOG.write(response + "\n")
    # LOG.flush()
    chan.send(response + "\r\n")

def send_ascii(filename, chan):
    """Print ascii from a file and send it to the channel"""
    with open('ascii/{}'.format(filename)) as text:
        chan.send("\r")
        for line in enumerate(text):
            # LOG.write(line[1])
            chan.send(line[1] + "\r")
    # LOG.flush()


if __name__=='__main__':
    address = '127.0.0.1'
    port = 2222
    start_server(port, address)
    pass

    
    
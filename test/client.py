import socket
import sys

HOST = "localhost"  # The remote host
PORT = 9999  # The same port as used by the server

address_info = socket.getaddrinfo(HOST, PORT, socket.AF_INET, socket.SOCK_STREAM)[0]

family, socket_type, proto, _, socket_address = address_info

sock = socket.socket(family, socket_type, proto)
sock.connect(socket_address)

with sock:
    while True:
        data_ = input("请输入: \n")

        sock.sendall(data_.encode("utf8"))

        data = sock.recv(1024)

        print('Received: ', data.decode("utf8"))

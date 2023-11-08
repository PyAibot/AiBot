import socket


def demo():
    address_info = socket.getaddrinfo(None, 3333, socket.AF_INET, socket.SOCK_STREAM)[0]
    family, socket_type, proto, _, socket_address = address_info
    __sock = socket.socket(family, socket_type, proto)
    __sock.listen(1)
    connection, client_address = __sock.accept()


if __name__ == '__main__':
    demo()

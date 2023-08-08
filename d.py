import socket
import threading
import time

HOST = "localhost"
PORT = 3333

address_info = socket.getaddrinfo(HOST, PORT, socket.AF_INET, socket.SOCK_STREAM)[0]

family, socket_type, proto, _, socket_address = address_info


def func(x):
    try:
        sock = socket.socket(family, socket_type, proto)
        sock.connect(socket_address)

        with sock:
            while True:
                data = sock.recv(1024)
                print(f'{x}-Received: ', data.decode("utf8"))
                time.sleep(500)
    except Exception as e:
        print(e)


if __name__ == '__main__':
    thread_list = []
    for i in range(200):
        t = threading.Thread(target=func, args=(i,))
        thread_list.append(t)

    for t in thread_list:
        t.start()

    for t in thread_list:
        t.join()

    print("END!")


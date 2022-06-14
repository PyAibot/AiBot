def _send_data(*args):
    args_len = ""
    args_text = ""

    for argv in args:
        args_text += str(argv)
        args_len += str(len(bytes(str(argv), "utf8")))
        args_len += "/"

    data = args_len.rstrip("/") + "\n" + args_text

    print(data)


if __name__ == '__main__':
    _send_data("hahah", 555, 201, 3333)
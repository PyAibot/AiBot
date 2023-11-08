import json
import random
import socket
import subprocess
import sys

from loguru import logger

from AiBot._utils import Log_Format


class WebBotBase:
    raise_err = False
    wait_timeout = 3  # seconds
    interval_timeout = 0.5  # seconds

    log_storage = False
    log_level = "INFO"
    log_size = 10  # MB

    log = logger

    if log_storage:
        log.add("./runtime.log", level=log_level.upper(), format=Log_Format,
                rotation=f'{log_size} MB',
                retention='0 days')

    def __init__(self, port):
        address_info = socket.getaddrinfo(None, port, socket.AF_INET, socket.SOCK_STREAM)[0]
        family, socket_type, proto, _, socket_address = address_info
        self.__sock = socket.socket(family, socket_type, proto)
        self.__sock.listen(1)
        connection, client_address = self.__sock.accept()

    @classmethod
    def build(cls, listen_port: int, local: bool = True, driver_params: dict = None) -> "WebBotBase":
        """
        :param listen_port: 脚本监听的端口
        :param local: 脚本是否部署在本地
        :param driver_params: Web 驱动启动参数
        :return:
        """
        if listen_port < 0 or listen_port > 65535:
            raise OSError("`listen_port` must be in 0-65535.")
        print("启动服务...")
        # 获取 IPv4 可用地址
        address_info = socket.getaddrinfo(None, listen_port, socket.AF_INET, socket.SOCK_STREAM, 0, socket.AI_PASSIVE)[
            0]
        *_, socket_address = address_info

        # 如果是本地部署，则自动启动 WebDriver.exe
        if local:
            default_params = {
                "serverIp": "127.0.0.1",
                "serverPort": listen_port,
                "browserName": "chrome",
                "debugPort": 0,
                "userDataDir": f"./UserData{random.randint(100000, 999999)}",
                "browserPath": None,
                "argument": None,
            }
            if driver_params:
                default_params.update(driver_params)
            default_params = json.dumps(default_params)
            try:
                subprocess.Popen(["WebDriver.exe", default_params])
                print("本地启动 WebDriver 成功，开始执行脚本")
            except FileNotFoundError as e:
                err_msg = "\n异常排除步骤：\n1. 检查 Aibote.exe 路径是否存在中文；\n2. 是否启动 Aibote.exe 初始化环境变量；\n3. 检查电脑环境变量是否初始化成功，环境变量中是否存在 %Aibote% 开头的；\n4. 首次初始化环境变量后，是否重启开发工具；\n5. 是否以管理员权限启动开发工具；\n"
                print("\033[92m", err_msg, "\033[0m")
                raise e
        else:
            print("等待驱动连接...")
        return WebBotBase(port)

    def __send_data(self, *args) -> str:
        args_len = ""
        args_text = ""

        for argv in args:
            if argv is None:
                argv = ""
            elif isinstance(argv, bool) and argv:
                argv = "true"
            elif isinstance(argv, bool) and not argv:
                argv = "false"

            argv = str(argv)
            args_text += argv
            args_len += str(len(argv)) + "/"

        data = (args_len.strip("/") + "\n" + args_text).encode("utf8")

        self.log.debug(rf"---> {data}")
        self.__sock.sendall(data)
        data_length, data = self.__sock.recv(65535).split(b"/", 1)

        while int(data_length) > len(data):
            data += self.__sock.recv(65535)
        self.log.debug(rf"<--- {data}")

        return data.decode("utf8").strip()

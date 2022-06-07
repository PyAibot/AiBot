import abc
import socket
import socketserver
import time

from pathlib import Path
from loguru import logger

LOG_PATH = Path(__file__).parent.resolve() / "logs"

# rotation 文件分割，可按时间或者大小分割
# retention 日志保留时间
# compression="zip" 压缩方式

# logger.add(LOG_PATH / 'runtime.log', rotation='100 MB', retention='15 days')  按大小分割，日志保留 15 天
# logger.add(LOG_PATH / 'runtime.log', rotation='1 week')  # rotation 按时间分割，每周分割一次

# 按时间分割，每日 12:00 分割一次，保留 15 天
logger.add(LOG_PATH / "runtime_{time}.log", rotation="12:00", retention="15 days")


def protect(*protected):
    """
    元类工厂，禁止类属性或方法被子类重写
    :param protected: 禁止重新的属性或方法
    :return:
    """

    class Protect(abc.ABCMeta):
        # 是否父类
        is_parent_class = True

        def __new__(mcs, name, bases, namespace):
            # 不是父类，需要检查属性是否被重写
            if not mcs.is_parent_class:
                attr_names = namespace.keys()
                for attr in protected:
                    if attr in attr_names:
                        raise AttributeError(f'Overriding of attribute `{attr}` not allowed.')

            # 首次调用后设置为 False
            mcs.is_parent_class = False
            return super().__new__(mcs, name, bases, namespace)

    return Protect


class ThreadingTCPServer(socketserver.ThreadingTCPServer):
    daemon_threads = True


class AiBotMain(socketserver.BaseRequestHandler, metaclass=protect("handle", "execute")):
    wait_timeout = None
    interval_timeout = None

    # TODO: 接收客户端数据的作用是什么？

    @logger.catch()
    def _send_data(self, *args) -> str:
        args_len = ""
        args_text = ""

        for argv in args:
            args_text += str(argv)
            args_len += str(len(bytes(str(argv), "utf8")))
            args_len += "/"

        data = args_len.rstrip("/") + "\n" + args_text

        logger.info(bytes(data, "utf8"))
        self.request.sendall(bytes(data, "utf8"))
        response = self.request.recv(1024).decode("utf8").strip()
        logger.info(response)
        return response

    def show_toast(self, text: str) -> bool:
        """
        Toast弹窗
        :param text: 弹窗内容
        :return:
        """
        response = self._send_data("showToast", text)
        return response.split("/")[-1] == "true"

    @staticmethod
    def sleep(seconds: float) -> None:
        """
        线程休眠
        :param seconds: 休眠时间
        :return:
        """
        return time.sleep(seconds)

    @classmethod
    def set_implicit_timeout(cls, wait_seconds: float, interval_seconds: float = 0.005) -> None:
        """
        设置找图色的隐式等待时间
        :param wait_seconds:  等待时间
        :param interval_seconds: 轮询时间，默认 5 毫秒
        :return:
        """
        cls.wait_timeout = wait_seconds
        cls.interval_timeout = interval_seconds

    def save_screenshot(self, image_name: str, region: list = None, algorithm: list = None):
        """
        保存截图
        :param image_name: 图片名称，保存在手机 /storage/emulated/0/Android/data/com.aibot.client/files/ 路径下；
        :param region:  截图区域，默认全屏；
        :param algorithm: 处理截图所用算法和参数，默认保存原图；
        :return:
        # 区域相关
        region = [0, 0, 0, 0] 按元素顺序分别代表：起点x、起点y、终点、终点y，最终得到一个矩形。
        # 算法相关
        algorithm = [0, 0, 0] # 按元素顺序分别代表：algorithm_type 算法类型、threshold 阈值、max_val 最大值。
        threshold 和 max_val 同为 255 时灰度处理.
        0   THRESH_BINARY      算法，当前点值大于阈值 threshold 时，取最大值 max_val，否则设置为 0；
        1   THRESH_BINARY_INV  算法，当前点值大于阈值 threshold 时，设置为 0，否则设置为最大值 max_val；
        2   THRESH_TOZERO      算法，当前点值大于阈值 threshold 时，不改变，否则设置为 0；
        3   THRESH_TOZERO_INV  算法，当前点值大于阈值 threshold 时，设置为 0，否则不改变；
        4   THRESH_TRUNC       算法，当前点值大于阈值 threshold 时，设置为阈值 threshold，否则不改变；
        5   ADAPTIVE_THRESH_MEAN_C      算法，自适应阈值；
        6   ADAPTIVE_THRESH_GAUSSIAN_C  算法，自适应阈值；
        """
        if image_name.find("/") != -1:
            raise ValueError("`image_ name` cannot contain `/`.")

        # 存储路径
        base_path = "/storage/emulated/0/Android/data/com.aibot.client/files/"
        # 截图区域 默认值
        left, top, right, bottom = [0, 0, 0, 0]
        # 算法 默认值
        algorithm_type, threshold, max_val = [0, 0, 0]

        if region:
            left, top, right, bottom = region

        if algorithm:
            algorithm_type, threshold, max_val = algorithm
            if algorithm_type in (5, 6):
                threshold = 127
                max_val = 255

        response = self._send_data("saveScreenshot", base_path + image_name, left, top, right, bottom,
                                   algorithm_type, threshold, max_val)

        return response.split("/")[-1] == "true"

    def handle(self) -> None:
        # 执行脚本
        self.script_main()

    @abc.abstractmethod
    def script_main(self):
        """脚本入口，由子类重写
        """

    @classmethod
    def execute(cls, listen_port):
        """
        多线程启动 Socket 服务，执行脚本
        :return:
        """

        if listen_port < 0 or listen_port > 65535:
            raise OSError("`listen_port` must be in 0-65535.")

        # 获取 IPv4 可用地址
        address_info = socket.getaddrinfo(None, listen_port, socket.AF_INET, socket.SOCK_STREAM, 0, socket.AI_PASSIVE)[
            0]
        *args, socket_address = address_info

        # 启动 Socket 服务
        sock = ThreadingTCPServer(socket_address, cls, bind_and_activate=True)
        sock.serve_forever()


class AiBotTestScript(AiBotMain):
    def script_main(self):
        self.show_toast("连接成功, 3S后开始截图")
        self.sleep(3)
        resp = self.save_screenshot("test2.png", algorithm=[2, 100, 200])
        self.show_toast("截图成功")
        while True:
            self.sleep(5)
            self.show_toast("恭喜发财")


if __name__ == '__main__':
    AiBotTestScript.execute(3333)

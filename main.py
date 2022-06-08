import abc
import socket
import socketserver
import time

from pathlib import Path
from collections import namedtuple
from typing import Union, List, Optional, Tuple

from loguru import logger

LOG_PATH = Path(__file__).parent.resolve() / "logs"

# rotation 文件分割，可按时间或者大小分割
# retention 日志保留时间
# compression="zip" 压缩方式

# logger.add(LOG_PATH / 'runtime.log', rotation='100 MB', retention='15 days')  按大小分割，日志保留 15 天
# logger.add(LOG_PATH / 'runtime.log', rotation='1 week')  # rotation 按时间分割，每周分割一次

# 按时间分割，每日 12:00 分割一次，保留 15 天
logger.add(LOG_PATH / "runtime_{time}.log", rotation="12:00", retention="15 days")

Point = namedtuple("Point", ["x", "y"])

Region = Tuple[int, int, int, int]
Algorithm = Tuple[int, int, int]
SubColors = List[Tuple[int, int, str]]


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
    wait_timeout = 1  # seconds
    interval_timeout = 0.5  # seconds

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
        return response.split("/", 1)[-1]

    def show_toast(self, text: str) -> bool:
        """
        Toast弹窗
        :param text: 弹窗内容；
        :return:
        """
        response = self._send_data("showToast", text)
        return response == "true"

    @classmethod
    def set_implicit_timeout(cls, wait_seconds: float, interval_seconds: float = 0.005) -> None:
        """
        设置找图色的隐式等待时间
        :param wait_seconds:  等待时间；
        :param interval_seconds: 轮询时间，默认 5 毫秒；
        :return:
        """
        cls.wait_timeout = wait_seconds
        cls.interval_timeout = interval_seconds

    def save_screenshot(self, image_name: str, region: Region = None, algorithm: Algorithm = None) -> Tuple[bool, str]:
        """
        保存截图
        :param image_name: 图片名称，保存在手机 /storage/emulated/0/Android/data/com.aibot.client/files/ 路径下；
        :param region: 截图区域，默认全屏；
        :param algorithm: 处理截图所用算法和参数，默认保存原图；
        :return:

        # 区域相关参数
        region = [0, 0, 0, 0] 按元素顺序分别代表：起点x、起点y、终点、终点y，最终得到一个矩形。
        # 算法相关参数
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

        if response == "true":
            return True, base_path + image_name

        return False, ""

    def get_color(self, point: Union[Point, Tuple[int, int]]) -> str:
        """
        获取指定坐标点的色值，返回颜色字符串，例如：#008577，失败时返回空字符串
        :param point: 坐标点；
        :return:
        """
        response = self._send_data("getColor", point[0], point[1])
        if response == "null":
            return ""
        return response

    # TODO: 未经测试
    def find_color(self, color: str, sub_colors: SubColors = None, region: Region = None, similarity: float = 0.9):
        """
        查找指定色值的坐标点
        :param color: 颜色字符串，必须以 # 开头，例如：#008577；
        :param sub_colors: 辅助定位的其他颜色；
        :param region: 在指定区域内找色，默认全屏；
        :param similarity: 相似度，0-1 的浮点数，默认 0.9；
        :return:
        """
        # 截图区域 默认值
        left, top, right, bottom = [0, 0, 0, 0]

        if region:
            left, top, right, bottom = region

        if sub_colors:
            sub_colors_str = ""
            for sub_color in sub_colors:
                offset_x, offset_y, color_str = sub_color
                sub_colors_str += str(offset_x) + "/" + str(offset_y) + "/" + color_str + "\n"

            # 去除最后一个 \n
            sub_colors_str = sub_colors_str.strip()
        else:
            sub_colors_str = "null"

        end_time = time.time() + self.wait_timeout

        while time.time() < end_time:
            response = self._send_data("findColor", color, sub_colors_str, left, top, right, bottom, similarity)

            # 找色失败
            if response == "-1.0|-1.0":
                time.sleep(self.interval_timeout)
            else:
                # 找色成功
                x, y = response.split("|")
                return True, Point(x=int(x), y=int(y))

        # 超时
        return False, Point(x=-1, y=-1)

    # TODO: 未经测试
    def find_image(self, image_path, region: Region = None, algorithm: Algorithm = None,
                   similarity: float = 0.9) -> Tuple[bool, Point]:
        """
        寻找图片坐标，在当前屏幕中寻找给定图片的坐标
        :param image_path: 图片的绝对路径；
        :param region: 从指定区域中找图，默认全屏；
        :param algorithm: 处理屏幕截图所用的算法，默认原图，注意：给定图片处理时所用的算法，应该和此方法的算法一致；
        :param similarity: 相似度，0-1 的浮点数，默认 0.9；
        :return:

        region 与 algorithm 参数，和 self.save_screenshot() 方法的同名参数一致，此处不再赘述；
        """
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

        end_time = time.time() + self.wait_timeout

        while time.time() < end_time:
            response = self._send_data("findImage", image_path, left, top, right, bottom, similarity,
                                       algorithm_type, threshold, max_val)

            # 找图失败
            if response == "-1.0|-1.0":
                time.sleep(self.interval_timeout)
            else:
                # 找图成功，返回图片左上角坐标
                x, y = response.split("|")
                return True, Point(x=int(x), y=int(y))

        # 超时
        return False, Point(x=-1, y=-1)

    # TODO: 未经测试
    def find_images_by_opencv(self, image_path, region: Region = None, algorithm: Algorithm = None,
                              similarity: float = 0.9, multi: int = 1) -> Tuple[bool, List[Point]]:
        """
        寻找图片坐标，在当前屏幕中寻找给定图片的坐标；
        与 self.find_image() 基本一致，采用 OpenCV 算法，并且可找多个目标。
        :param image_path: 图片的绝对路径；
        :param region: 从指定区域中找图，默认全屏；
        :param algorithm: 处理屏幕截图所用的算法，默认原图，注意：给定图片处理时所用的算法，应该和此方法的算法一致；
        :param similarity: 相似度，0-1 的浮点数，默认 0.9；
        :param multi: 目标数量，默认为 1，找到 1 个目标后立即结束；
        :return:

        region 与 algorithm 参数，和 self.save_screenshot() 方法的同名参数一致，此处不再赘述；
        """
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

        end_time = time.time() + self.wait_timeout

        while time.time() < end_time:
            response = self._send_data("findImage", image_path, left, top, right, bottom, similarity,
                                       algorithm_type, threshold, max_val)

            # 找图失败
            if response == "-1.0|-1.0":
                time.sleep(self.interval_timeout)
            else:
                # 找图成功，返回图片左上角坐标

                # 分割出多个图片的坐标
                image_points = response.split("/")

                point_list = []

                for point_str in image_points:
                    x, y = point_str.split("|")
                    point_list.append(Point(x=int(x), y=int(y)))

                return True, point_list
        # 超时
        return False, []

    # 未经测试
    def find_dynamic_image(self, interval_time, region: Region = None) -> Tuple[bool, List[Point]]:
        """
        找动态图，对比同一张图在不同时刻是否发生变化，返回多个坐标点
        :param interval_time: 前后时刻的间隔时间；
        :param region: 在指定区域找图，默认全屏；
        :return:
        """
        # 指定区域 默认值
        left, top, right, bottom = [0, 0, 0, 0]

        if region:
            left, top, right, bottom = region

        end_time = time.time() + self.wait_timeout

        while time.time() < end_time:
            response = self._send_data("findAnimation", interval_time, left, top, right, bottom)

            # 找图失败
            if response == "-1.0|-1.0":
                time.sleep(self.interval_timeout)
            else:
                # 找图成功，返回图片左上角坐标

                # 分割出多个图片的坐标
                image_points = response.split("/")

                point_list = []

                for point_str in image_points:
                    x, y = point_str.split("|")
                    point_list.append(Point(x=int(x), y=int(y)))

                return True, point_list

        # 超时
        return False, []

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
        self.show_toast("连接成功")
        _path = "/Users/chenxun/PycharmProjects/Aibot/7BA630FA96C38F241B0EA32F86D213EA.jpg"
        image_path = self.find_image(_path, similarity=0.5)
        print(image_path)

        while True:
            time.sleep(5)
            self.show_toast("恭喜发财")


if __name__ == '__main__':
    AiBotTestScript.execute(3333)

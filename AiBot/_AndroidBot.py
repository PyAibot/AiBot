import abc
import json
import socket
import socketserver
import sys
import threading
import time
import re
from ast import literal_eval
from typing import Optional, Dict, List, Tuple, Union

from loguru import logger

from ._utils import _protect, _Region, _Algorithm, _SubColors


# _LOG_PATH = Path(__file__).parent.resolve() / "logs"

# # rotation 文件分割，可按时间或者大小分割
# # retention 日志保留时间
# # compression="zip" 压缩方式
#
# # logger.add(LOG_PATH / 'runtime.log', rotation='100 MB', retention='15 days')  按大小分割，日志保留 15 天
# # logger.add(LOG_PATH / 'runtime.log', rotation='1 week')  # rotation 按时间分割，每周分割一次
#
# # 按时间分割，每日 12:00 分割一次，保留 15 天
# logger.add(_LOG_PATH / "runtime_{time}.log", rotation="12:00", retention="15 days")

class _Point:
    def __init__(self, x, y, driver: "AndroidBotMain"):
        self.x = x
        self.y = y
        self.__driver = driver

    def click(self, offset_x: float = 0, offset_y: float = 0):
        """
        点击坐标
        :param offset_x: 坐标 x 轴偏移量；
        :param offset_y: 坐标 y 轴偏移量；
        :return:
        """
        self.__driver.click(self, offset_x=offset_x, offset_y=offset_y)

    def get_points_center(self, other_point: "_Point") -> "_Point":
        """
        获取两个坐标点的中间坐标
        :param other_point: 其他的坐标点
        :return:
        """
        return self.__class__(x=self.x + (other_point.x - self.x) / 2, y=self.y + (other_point.y - self.y) / 2,
                              driver=self.__driver)

    def __getitem__(self, item):
        if item == 0:
            return self.x
        elif item == 1:
            return self.y
        else:
            raise IndexError("list index out of range")

    def __repr__(self):
        return f"Point(x={self.x}, y={self.y})"


_Point_Tuple = Union[_Point, Tuple[int, int]]


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class AndroidBotMain(socketserver.BaseRequestHandler, metaclass=_protect("handle", "execute")):
    raise_err = False

    wait_timeout = 3  # seconds
    interval_timeout = 0.5  # seconds

    log_path = ""
    log_level = "INFO"
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | " \
                 "<level>{level: <8}</level> | " \
                 "{thread.name: <8} | " \
                 "<cyan>{module}.{function}:{line}</cyan> | " \
                 "<level>{message}</level>"  # 日志内容

    # 基础存储路径
    _base_path = "/storage/emulated/0/Android/data/com.aibot.client/files/"

    def __init__(self, request, client_address, server):
        self._lock = threading.Lock()
        self.log = logger

        self.log.remove()
        self.log.add(sys.stdout, level=self.log_level.upper(), format=self.log_format)

        if self.log_path:
            self.log.add(self.log_path, level=self.log_level.upper(), rotation="12:00", retention="15 days",
                         format=self.log_format)

        super().__init__(request, client_address, server)

    def __send_data(self, *args) -> str:
        args_len = ""
        args_text = ""

        for argv in args:
            argv = str(argv)
            args_text += argv
            args_len += str(len(bytes(argv, 'utf8'))) + "/"

        data = (args_len.strip("/") + "\n" + args_text).encode("utf8")

        with self._lock:
            self.log.debug(rf"---> {data}")
            self.request.sendall(data)
            response = self.request.recv(65535)
            if response == b"":
                raise ConnectionAbortedError(f"{self.client_address[0]}:{self.client_address[1]} 客户端断开链接。")
            data_length, data = response.split(b"/", 1)
            while int(data_length) > len(data):
                data += self.request.recv(65535)
            self.log.debug(rf"<--- {data}")

        return data.decode("utf8").strip()

    def __push_file(self, func_name: str, to_path: str, file: bytes):
        func_name = bytes(func_name, "utf8")
        to_path = bytes(to_path, "utf8")

        str_data = ""
        str_data += str(len(func_name)) + "/"  # func_name 字节长度
        str_data += str(len(to_path)) + "/"  # to_path 字节长度
        str_data += str(len(file)) + "\n"  # file 字节长度

        bytes_data = bytes(str_data, "utf8")
        bytes_data += func_name
        bytes_data += to_path
        bytes_data += file

        with self._lock:
            self.log.debug(rf"---> {bytes_data}")
            self.request.sendall(bytes_data)
            response = self.request.recv(65535)
            if response == b"":
                raise ConnectionAbortedError(f"{self.client_address[0]}:{self.client_address[1]} 客户端断开链接。")
            data_length, data = response.split(b"/", 1)
            while int(data_length) > len(data):
                data += self.request.recv(65535)
            self.log.debug(rf"<--- {data}")

        return data.decode("utf8").strip()

    def __pull_file(self, *args) -> bytes:
        args_len = ""
        args_text = ""

        for argv in args:
            argv = str(argv)
            args_text += argv
            args_len += str(len(bytes(argv, 'utf8'))) + "/"

        data = (args_len.strip("/") + "\n" + args_text).encode("utf8")

        with self._lock:
            self.log.debug(rf"---> {data}")
            self.request.sendall(data)
            response = self.request.recv(65535)
            if response == b"":
                raise ConnectionAbortedError(f"{self.client_address[0]}:{self.client_address[1]} 客户端断开链接。")
            data_length, data = response.split(b"/", 1)
            while int(data_length) > len(data):
                data += self.request.recv(65535)
            self.log.debug(rf"<--- {data}")

        return data

    def save_screenshot(self, image_name: str, region: _Region = None, algorithm: _Algorithm = None) -> Optional[str]:
        """
        保存截图，返回图片地址(手机中)或者 None
        :param image_name: 图片名称，保存在手机 /storage/emulated/0/Android/data/com.aibot.client/files/ 路径下；
        :param region: 截图区域，默认全屏；
        :param algorithm: 处理截图所用算法和参数，默认保存原图；
        :return:

        # 区域相关参数
        region = (0, 0, 0, 0) 按元素顺序分别代表：起点x、起点y、终点x、终点y，最终得到一个矩形。
        # 算法相关参数
        algorithm = (0, 0, 0) # 按元素顺序分别代表：algorithm_type 算法类型、threshold 阈值、max_val 最大值。
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
            raise ValueError("`image_name` cannot contain `/`.")

        if not region:
            region = [0, 0, 0, 0]

        if not algorithm:
            algorithm_type, threshold, max_val = [0, 0, 0]
        else:
            algorithm_type, threshold, max_val = algorithm
            if algorithm_type in (5, 6):
                threshold = 127
                max_val = 255

        response = self.__send_data("saveScreenshot", self._base_path + image_name, *region,
                                    algorithm_type, threshold, max_val)
        if response == "true":
            return self._base_path + image_name
        return None

    def save_element_screenshot(self, image_name, xpath) -> Optional[str]:
        """
        保存元素截图，返回图片地址(手机中)或者 None
        :return:
        """
        rect = self.get_element_rect(xpath)
        if rect is None:
            return None
        return self.save_screenshot(image_name, region=(rect[0].x, rect[0].y, rect[1].x, rect[1].y))

    # #############
    #   色值相关   #
    # #############
    def get_color(self, point: _Point_Tuple) -> Optional[str]:
        """
        获取指定坐标点的色值，返回色值字符串(#008577)或者 None
        :param point: 坐标点；
        :return:
        """
        response = self.__send_data("getColor", point[0], point[1])
        if response == "null":
            return None
        return response

    def find_color(self, color: str, sub_colors: _SubColors = None, region: _Region = None, similarity: float = 0.9,
                   wait_time: float = None, interval_time: float = None, raise_err: bool = None) -> Optional[_Point]:
        """
        获取指定色值的坐标点，返回坐标或者 None
        :param color: 颜色字符串，必须以 # 开头，例如：#008577；
        :param sub_colors: 辅助定位的其他颜色；
        :param region: 在指定区域内找色，默认全屏；
        :param similarity: 相似度，0-1 的浮点数，默认 0.9；
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :param raise_err: 超时是否抛出异常；
        :return:

        # 区域相关参数
        region = (0, 0, 0, 0) 按元素顺序分别代表：起点x、起点y、终点x、终点y，最终得到一个矩形。
        # 算法相关参数
        algorithm = (0, 0, 0) # 按元素顺序分别代表：algorithm_type 算法类型、threshold 阈值、max_val 最大值。
        threshold 和 max_val 同为 255 时灰度处理.
        0   THRESH_BINARY      算法，当前点值大于阈值 threshold 时，取最大值 max_val，否则设置为 0；
        1   THRESH_BINARY_INV  算法，当前点值大于阈值 threshold 时，设置为 0，否则设置为最大值 max_val；
        2   THRESH_TOZERO      算法，当前点值大于阈值 threshold 时，不改变，否则设置为 0；
        3   THRESH_TOZERO_INV  算法，当前点值大于阈值 threshold 时，设置为 0，否则不改变；
        4   THRESH_TRUNC       算法，当前点值大于阈值 threshold 时，设置为阈值 threshold，否则不改变；
        5   ADAPTIVE_THRESH_MEAN_C      算法，自适应阈值；
        6   ADAPTIVE_THRESH_GAUSSIAN_C  算法，自适应阈值；
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        if raise_err is None:
            interval_time = self.raise_err

        if not region:
            region = [0, 0, 0, 0]

        if sub_colors:
            sub_colors_str = ""
            for sub_color in sub_colors:
                offset_x, offset_y, color_str = sub_color
                sub_colors_str += f"{offset_x}/{offset_y}/{color_str}\n"
            # 去除最后一个 \n
            sub_colors_str = sub_colors_str.strip()
        else:
            sub_colors_str = "null"

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data("findColor", color, sub_colors_str, *region, similarity)
            # 找色失败
            if response == "-1.0|-1.0":
                time.sleep(interval_time)
            else:
                # 找色成功
                x, y = response.split("|")
                return _Point(x=float(x), y=float(y), driver=self)
        # 超时
        if raise_err:
            raise TimeoutError("`find_color` 操作超时。")
        return None

    # def compare_color(self):
    #     """比较指定坐标点的颜色值"""
    #     raise NotImplementedError()

    # #############
    #   找图相关   #
    # #############
    def find_image(self, image_name, region: _Region = None, algorithm: _Algorithm = None, similarity: float = 0.9,
                   wait_time: float = None, interval_time: float = None, raise_err: bool = None) -> Optional[_Point]:
        """
        寻找图片坐标，在当前屏幕中寻找给定图片中心点的坐标，返回坐标或者 None
        :param image_name: 图片名称（手机中）；
        :param region: 从指定区域中找图，默认全屏；
        :param algorithm: 处理屏幕截图所用的算法，默认原图，注意：给定图片处理时所用的算法，应该和此方法的算法一致；
        :param similarity: 相似度，0-1 的浮点数，默认 0.9；
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :param raise_err: 超时是否抛出异常；
        :return:

        # 区域相关参数
        region = (0, 0, 0, 0) 按元素顺序分别代表：起点x、起点y、终点x、终点y，最终得到一个矩形。
        # 算法相关参数
        algorithm = (0, 0, 0) # 按元素顺序分别代表：algorithm_type 算法类型、threshold 阈值、max_val 最大值。
        threshold 和 max_val 同为 255 时灰度处理.
        0   THRESH_BINARY      算法，当前点值大于阈值 threshold 时，取最大值 max_val，否则设置为 0；
        1   THRESH_BINARY_INV  算法，当前点值大于阈值 threshold 时，设置为 0，否则设置为最大值 max_val；
        2   THRESH_TOZERO      算法，当前点值大于阈值 threshold 时，不改变，否则设置为 0；
        3   THRESH_TOZERO_INV  算法，当前点值大于阈值 threshold 时，设置为 0，否则不改变；
        4   THRESH_TRUNC       算法，当前点值大于阈值 threshold 时，设置为阈值 threshold，否则不改变；
        5   ADAPTIVE_THRESH_MEAN_C      算法，自适应阈值；
        6   ADAPTIVE_THRESH_GAUSSIAN_C  算法，自适应阈值；
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        if raise_err is None:
            interval_time = self.raise_err

        if not region:
            region = [0, 0, 0, 0]

        if not algorithm:
            algorithm_type, threshold, max_val = [0, 0, 0]
        else:
            algorithm_type, threshold, max_val = algorithm
            if algorithm_type in (5, 6):
                threshold = 127
                max_val = 255

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data("findImage", self._base_path + image_name, *region, similarity,
                                        algorithm_type, threshold, max_val)
            # 找图失败
            if response == "-1.0|-1.0":
                time.sleep(interval_time)
            else:
                # 找图成功，返回图片左上角坐标
                x, y = response.split("|")
                return _Point(x=float(x), y=float(y), driver=self)
        # 超时
        if raise_err:
            raise TimeoutError("`find_image` 操作超时。")
        return None

    def find_image_by_opencv(self, image_name, region: _Region = None, algorithm: _Algorithm = None,
                             similarity: float = 0.9, wait_time: float = None, interval_time: float = None,
                             raise_err: bool = None) -> Optional[_Point]:
        """
        寻找图片坐标，在当前屏幕中寻找给定图片中心点的坐标，返回图片坐标或者 None
        与 self.find_image() 基本一致，采用 OpenCV 算法
        :param image_name: 图片名称（手机中）；
        :param region: 从指定区域中找图，默认全屏；
        :param algorithm: 处理屏幕截图所用的算法，默认原图，注意：给定图片处理时所用的算法，应该和此方法的算法一致；
        :param similarity: 相似度，0-1 的浮点数，默认 0.9；
        :param wait_time: 等待时间，默认取 self.wait_timeout
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout
        :param raise_err: 超时是否抛出异常；
        :return:

        # 区域相关参数
        region = (0, 0, 0, 0) 按元素顺序分别代表：起点x、起点y、终点x、终点y，最终得到一个矩形。
        # 算法相关参数
        algorithm = (0, 0, 0) # 按元素顺序分别代表：algorithm_type 算法类型、threshold 阈值、max_val 最大值。
        threshold 和 max_val 同为 255 时灰度处理.
        0   THRESH_BINARY      算法，当前点值大于阈值 threshold 时，取最大值 max_val，否则设置为 0；
        1   THRESH_BINARY_INV  算法，当前点值大于阈值 threshold 时，设置为 0，否则设置为最大值 max_val；
        2   THRESH_TOZERO      算法，当前点值大于阈值 threshold 时，不改变，否则设置为 0；
        3   THRESH_TOZERO_INV  算法，当前点值大于阈值 threshold 时，设置为 0，否则不改变；
        4   THRESH_TRUNC       算法，当前点值大于阈值 threshold 时，设置为阈值 threshold，否则不改变；
        5   ADAPTIVE_THRESH_MEAN_C      算法，自适应阈值；
        6   ADAPTIVE_THRESH_GAUSSIAN_C  算法，自适应阈值；
        """
        result = self.find_images_by_opencv(image_name, region, algorithm, similarity, 1, wait_time, interval_time,
                                            raise_err)
        if not result:
            return None
        return result[0]

    def find_images_by_opencv(self, image_name, region: _Region = None, algorithm: _Algorithm = None,
                              similarity: float = 0.9, multi: int = 1, wait_time: float = None,
                              interval_time: float = None, raise_err: bool = None) -> List[_Point]:
        """
        寻找图片坐标，在当前屏幕中寻找给定图片中心点的坐标，返回坐标列表
        与 self.find_image() 基本一致，采用 OpenCV 算法，并且可找多个目标。
        :param image_name: 图片名称（手机中）；
        :param region: 从指定区域中找图，默认全屏；
        :param algorithm: 处理屏幕截图所用的算法，默认原图，注意：给定图片处理时所用的算法，应该和此方法的算法一致；
        :param similarity: 相似度，0-1 的浮点数，默认 0.9；
        :param multi: 目标数量，默认为 1，找到 1 个目标后立即结束；
        :param wait_time: 等待时间，默认取 self.wait_timeout
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout
        :param raise_err: 超时是否抛出异常；
        :return:

        # 区域相关参数
        region = (0, 0, 0, 0) 按元素顺序分别代表：起点x、起点y、终点x、终点y，最终得到一个矩形。
        # 算法相关参数
        algorithm = (0, 0, 0) # 按元素顺序分别代表：algorithm_type 算法类型、threshold 阈值、max_val 最大值。
        threshold 和 max_val 同为 255 时灰度处理.
        0   THRESH_BINARY      算法，当前点值大于阈值 threshold 时，取最大值 max_val，否则设置为 0；
        1   THRESH_BINARY_INV  算法，当前点值大于阈值 threshold 时，设置为 0，否则设置为最大值 max_val；
        2   THRESH_TOZERO      算法，当前点值大于阈值 threshold 时，不改变，否则设置为 0；
        3   THRESH_TOZERO_INV  算法，当前点值大于阈值 threshold 时，设置为 0，否则不改变；
        4   THRESH_TRUNC       算法，当前点值大于阈值 threshold 时，设置为阈值 threshold，否则不改变；
        5   ADAPTIVE_THRESH_MEAN_C      算法，自适应阈值；
        6   ADAPTIVE_THRESH_GAUSSIAN_C  算法，自适应阈值；
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        if raise_err is None:
            interval_time = self.raise_err

        if not region:
            region = [0, 0, 0, 0]

        if not algorithm:
            algorithm_type, threshold, max_val = [0, 0, 0]
        else:
            algorithm_type, threshold, max_val = algorithm
            if algorithm_type in (5, 6):
                threshold = 127
                max_val = 255

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data("matchTemplate", self._base_path + image_name, *region, similarity,
                                        algorithm_type, threshold, max_val, multi)
            # 找图失败
            if response == "-1.0|-1.0":
                time.sleep(interval_time)
            else:
                # 找图成功，返回图片左上角坐标
                # 分割出多个图片的坐标
                image_points = response.split("/")
                point_list = []
                for point_str in image_points:
                    x, y = point_str.split("|")
                    point_list.append(_Point(x=float(x), y=float(y), driver=self))
                return point_list
        # 超时
        if raise_err:
            raise TimeoutError("`find_images_by_opencv` 操作超时。")
        return []

    def find_dynamic_image(self, interval_ti: int, region: _Region = None, wait_time: float = None,
                           interval_time: float = None, raise_err: bool = None) -> List[_Point]:
        """
        找动态图，对比同一张图在不同时刻是否发生变化，返回坐标列表
        :param interval_ti: 前后时刻的间隔时间，单位毫秒；
        :param region: 在指定区域找图，默认全屏；
        :param wait_time: 等待时间，默认取 self.wait_timeout
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout
        :param raise_err: 超时是否抛出异常；
        :return:

        # 区域相关参数
        region = (0, 0, 0, 0) 按元素顺序分别代表：起点x、起点y、终点x、终点y，最终得到一个矩形。
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        if raise_err is None:
            interval_time = self.raise_err

        if not region:
            region = [0, 0, 0, 0]

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data("findAnimation", interval_ti, *region)
            # 找图失败
            if response == "-1.0|-1.0":
                time.sleep(interval_time)
            else:
                # 找图成功，返回图片左上角坐标
                # 分割出多个图片的坐标
                image_points = response.split("/")
                point_list = []
                for point_str in image_points:
                    x, y = point_str.split("|")
                    point_list.append(_Point(x=float(x), y=float(y), driver=self))
                return point_list
        # 超时
        if raise_err:
            raise TimeoutError("`find_dynamic_image` 操作超时。")
        return []

    # ################
    #   坐标操作相关   #
    # ################
    def click(self, point: _Point_Tuple, offset_x: float = 0, offset_y: float = 0) -> bool:
        """
        点击坐标
        :param point: 坐标；
        :param offset_x: 坐标 x 轴偏移量；
        :param offset_y: 坐标 y 轴偏移量；
        :return:
        """
        return self.__send_data("click", point[0] + offset_x, point[1] + offset_y) == "true"

    def double_click(self, point: _Point_Tuple, offset_x: float = 0, offset_y: float = 0) -> bool:
        """
        双击坐标
        :param point: 坐标；
        :param offset_x: 坐标 x 轴偏移量；
        :param offset_y: 坐标 y 轴偏移量；
        :return:
        """
        return self.__send_data("doubleClick", point[0] + offset_x, point[1] + offset_y) == "true"

    def long_click(self, point: _Point_Tuple, duration: float, offset_x: float = 0, offset_y: float = 0) -> bool:
        """
        长按坐标
        :param point: 坐标；
        :param duration: 按住时长，单位秒；
        :param offset_x: 坐标 x 轴偏移量；
        :param offset_y: 坐标 y 轴偏移量；
        :return:
        """
        return self.__send_data("longClick", point[0] + offset_x, point[1] + offset_y, duration * 1000) == "true"

    def swipe(self, start_point: _Point_Tuple, end_point: _Point_Tuple, duration: float) -> bool:
        """
        滑动坐标
        :param start_point: 起始坐标；
        :param end_point: 结束坐标；
        :param duration: 滑动时长，单位秒；
        :return:
        """
        return self.__send_data("swipe", start_point[0], start_point[1], end_point[0], end_point[1],
                                duration * 1000) == "true"

    def gesture(self, gesture_path: List[_Point_Tuple], duration: float) -> bool:
        """
        执行手势
        :param gesture_path: 手势路径，由一系列坐标点组成
        :param duration: 手势执行时长, 单位秒
        :return:
        """

        gesture_path_str = ""
        for point in gesture_path:
            gesture_path_str += f"{point[0]}/{point[1]}/\n"
        gesture_path_str = gesture_path_str.strip()

        return self.__send_data("dispatchGesture", gesture_path_str, duration) == "true"

    def press(self, point: _Point_Tuple, duration: float) -> bool:
        """
        手指按下
        :param point: 坐标
        :param duration: 持续时间
        :return:
        """
        return self.__send_data("press", point[0], point[1], duration * 1000) == "true"

    def move(self, point: _Point_Tuple, duration: float) -> bool:
        """
        手指移动
        :param point: 坐标
        :param duration: 持续时间
        :return:
        """
        return self.__send_data("move", point[0], point[1], duration * 1000) == "true"

    def release(self) -> bool:
        """手指抬起"""
        return self.__send_data("release") == "true"

    # ##############
    #   OCR 相关   #
    ################
    @staticmethod
    def __parse_ocr(text: str) -> list:
        """
        解析 OCR 识别出出来的信息
        :param text:
        :return:
        """
        pattern = re.compile(r'(\[\[\[).+?(\)])')
        matches = pattern.finditer(text)

        text_info_list = []
        for match in matches:
            result_str = match.group()
            text_info = literal_eval(result_str)
            text_info_list.append(text_info)

        return text_info_list

    def __ocr_server(self, region: _Region = None, scale: float = 1.0) -> list:
        """
        OCR 服务，通过 OCR 识别屏幕中文字
        :param region:
        :param scale:
        :return:
        """
        if not region:
            region = [0, 0, 0, 0]

        response = self.__send_data("ocr", *region, scale)
        if response == "null" or response == "":
            return []
        return self.__parse_ocr(response)

    def get_text(self, region: _Region = None, scale: float = 1.0) -> List[str]:
        """
        通过 OCR 识别屏幕中的文字，返回文字列表
        :param region: 识别区域，默认全屏；
        :param scale: 图片缩放率，默认为 1.0，1.0 以下为缩小，1.0 以上为放大；
        :return:
        """
        text_info_list = self.__ocr_server(region, scale)
        text_list = []
        for text_info in text_info_list:
            text = text_info[-1][0]
            text_list.append(text)
        return text_list

    def find_text(self, text: str, region: _Region = None, scale: float = 1.0) -> List[_Point]:
        """
        查找文字所在的坐标，返回坐标列表（坐标是文本区域中心位置）
        :param text: 要查找的文字；
        :param region: 识别区域，默认全屏；
        :param scale: 图片缩放率，默认为 1.0，1.0 以下为缩小，1.0 以上为放大；
        :return:
        """
        if not region:
            region = [0, 0, 0, 0]

        # scale 仅支持区域识别
        if region[2] == 0:
            scale = 1.0

        text_info_list = self.__ocr_server(region, scale)

        text_points = []
        for text_info in text_info_list:
            if text in text_info[-1][0]:
                points, words_tuple = text_info

                left, top, right, bottom = points

                # 文本区域起点坐标
                start_x = left[0]
                start_y = left[1]
                # 文本区域终点坐标
                end_x = right[0]
                end_y = right[1]
                # 文本区域中心点据左上角的偏移量
                # 可能指定文本只是部分文本，要计算出实际位置(x轴)
                words: str = words_tuple[0]
                width = end_x - start_x

                # 单字符宽度
                single_word_width = width / len(words)
                # 文本在整体文本的起始位置
                pos = words.find(text)

                offset_x = pos * single_word_width + len(text) * single_word_width / 2
                offset_y = (end_y - start_y) / 2

                # [ { x: 108, y: 1153 } ]

                # 计算文本区域中心坐标
                if region[2] != 0:  # 缩放
                    text_point = _Point(
                        x=float(region[0] + (start_x + offset_x) / scale),
                        y=float(region[1] + (start_y + offset_y) / scale),
                        driver=self
                    )
                else:
                    text_point = _Point(
                        x=float(region[0] + (start_x + offset_x) * 2),
                        y=float(region[1] + (start_y + offset_y) * 2),
                        driver=self
                    )
                text_points.append(text_point)

        return text_points

    # #############
    #   元素操作   #
    ###############
    def get_element_rect(self, xpath: str, wait_time: float = None, interval_time: float = None,
                         raise_err: bool = None) -> Optional[Tuple[_Point, _Point]]:
        """
        获取元素位置，返回元素区域左上角和右下角坐标
        :param xpath: xpath 路径
        :param wait_time: 等待时间，默认取 self.wait_timeout
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout
        :param raise_err: 超时是否抛出异常；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        if raise_err is None:
            interval_time = self.raise_err

        end_time = time.time() + wait_time
        while time.time() < end_time:
            data = self.__send_data("getElementRect", xpath)
            # 失败
            if data == "-1|-1|-1|-1":
                time.sleep(interval_time)
            # 成功
            else:
                start_x, start_y, end_x, end_y = data.split("|")
                return _Point(x=float(start_x), y=float(start_y), driver=self), _Point(x=float(end_x), y=float(end_y),
                                                                                       driver=self)
        # 超时
        if raise_err:
            raise TimeoutError("`get_element_rect` 操作超时。")
        return None

    def get_element_desc(self, xpath: str, wait_time: float = None, interval_time: float = None,
                         raise_err: bool = None) -> Optional[str]:
        """
        获取元素描述
        :param xpath: xpath 路径
        :param wait_time: 等待时间，默认取 self.wait_timeout
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout
        :param raise_err: 超时是否抛出异常；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        if raise_err is None:
            interval_time = self.raise_err

        end_time = time.time() + wait_time
        while time.time() < end_time:
            data = self.__send_data("getElementDescription", xpath)
            # 失败
            if data == "null":
                time.sleep(interval_time)
            # 成功
            else:
                return data
        # 超时
        if raise_err:
            raise TimeoutError("`get_element_desc` 操作超时。")
        return None

    def get_element_text(self, xpath: str, wait_time: float = None, interval_time: float = None,
                         raise_err: bool = None) -> Optional[str]:
        """
        获取元素文本
        :param xpath: xpath 路径
        :param wait_time: 等待时间，默认取 self.wait_timeout
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout
        :param raise_err: 超时是否抛出异常；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        if raise_err is None:
            interval_time = self.raise_err

        end_time = time.time() + wait_time
        while time.time() < end_time:
            data = self.__send_data("getElementText", xpath)
            # 失败
            if data == "null":
                time.sleep(interval_time)
            # 成功
            else:
                return data
        # 超时
        if raise_err:
            raise TimeoutError("`get_element_text` 操作超时。")
        return None

    def set_element_text(self, xpath: str, text: str, wait_time: float = None, interval_time: float = None,
                         raise_err: bool = None) -> bool:
        """
        设置元素文本
        :param xpath:
        :param text:
        :param wait_time: 等待时间，默认取 self.wait_timeout
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout
        :param raise_err: 超时是否抛出异常；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        if raise_err is None:
            interval_time = self.raise_err

        end_time = time.time() + wait_time
        while time.time() < end_time:
            # 失败
            if self.__send_data("setElementText", xpath, text) != "true":
                time.sleep(interval_time)
            # 成功
            else:
                return True
        # 超时
        if raise_err:
            raise TimeoutError("`set_element_text` 操作超时。")
        return False

    def click_element(self, xpath: str, wait_time: float = None, interval_time: float = None,
                      raise_err: bool = None) -> bool:
        """
        点击元素
        :param xpath:
        :param wait_time: 等待时间，默认取 self.wait_timeout
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout
        :param raise_err: 超时是否抛出异常；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        if raise_err is None:
            interval_time = self.raise_err

        end_time = time.time() + wait_time
        while time.time() < end_time:
            # 失败
            if self.__send_data("clickElement", xpath) != "true":
                time.sleep(interval_time)
            # 成功
            else:
                return True
        # 超时
        if raise_err:
            raise TimeoutError("`click_element` 操作超时。")
        return False

    def click_any_elements(self, xpath_list: List[str], wait_time: float = None, interval_time: float = None,
                           raise_err: bool = None) -> bool:
        """
        遍历点击列表中的元素，直到任意一个元素返回 True
        :param xpath_list: xpath 列表
        :param wait_time: 等待时间，默认取 self.wait_timeout
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout
        :param raise_err: 超时是否抛出异常；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        if raise_err is None:
            interval_time = self.raise_err

        end_time = time.time() + wait_time
        while time.time() < end_time:
            for xpath in xpath_list:
                result = self.click_element(xpath, wait_time=0.05, interval_time=0.01)
                if result:
                    return True
            time.sleep(interval_time)

        if raise_err:
            raise TimeoutError("`click_any_elements` 操作超时。")
        return False

    def scroll_element(self, xpath: str, direction: int = 0) -> bool:
        """
        滚动元素，0 向上滑动，1 向下滑动
        :param xpath: xpath 路径
        :param direction: 滚动方向，0 向上滑动，1 向下滑动
        :return:
        """
        return self.__send_data("scrollElement", xpath, direction) == "true"

    def element_not_exists(self, xpath: str, wait_time: float = None, interval_time: float = None,
                           raise_err: bool = None) -> bool:
        """
        元素是否不存在
        :param xpath: xpath 路径
        :param wait_time: 等待时间，默认取 self.wait_timeout
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout
        :param raise_err: 超时是否抛出异常；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        if raise_err is None:
            interval_time = self.raise_err

        end_time = time.time() + wait_time
        while time.time() < end_time:
            # 存在
            if self.__send_data("existsElement", xpath) == "true":
                time.sleep(interval_time)
            # 不存在
            else:
                return True
        # 超时
        if raise_err:
            raise TimeoutError("`element_not_exists` 操作超时。")
        return False

    def element_exists(self, xpath: str, wait_time: float = None, interval_time: float = None,
                       raise_err: bool = None) -> bool:
        """
        元素是否存在
        :param xpath: xpath 路径
        :param wait_time: 等待时间，默认取 self.wait_timeout
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout
        :param raise_err: 超时是否抛出异常；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        if raise_err is None:
            interval_time = self.raise_err

        end_time = time.time() + wait_time
        while time.time() < end_time:
            # 失败
            if self.__send_data("existsElement", xpath) != "true":
                time.sleep(interval_time)
            # 成功
            else:
                return True
        # 超时
        if raise_err:
            raise TimeoutError("`element_exists` 操作超时。")
        return False

    def any_elements_exists(self, xpath_list: List[str], wait_time: float = None, interval_time: float = None,
                            raise_err: bool = None) -> Optional[str]:
        """
        遍历列表中的元素，只要任意一个元素存在就返回 True
        :param xpath_list: xpath 列表
        :param wait_time: 等待时间，默认取 self.wait_timeout
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout
        :param raise_err: 超时是否抛出异常；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        if raise_err is None:
            interval_time = self.raise_err

        end_time = time.time() + wait_time
        while time.time() < end_time:
            for xpath in xpath_list:
                result = self.element_exists(xpath, wait_time=0.05, interval_time=0.01)
                if result:
                    return xpath
            time.sleep(interval_time)

        if raise_err:
            raise TimeoutError("`any_elements_exists` 操作超时。")
        return None

    def element_is_selected(self, xpath: str) -> bool:
        """
        元素是否存在
        :param xpath: xpath 路径
        :return:
        """
        return self.__send_data("isSelectedElement", xpath) == "true"

    def click_element_by_slide(self, xpath, distance: int = 1000, duration: float = 0.5, direction: int = 1,
                               count: int = 999, end_flag_xpath: str = None, wait_time: float = 600,
                               interval_time: float = 0.5, raise_err: bool = None) -> bool:
        """
        滑动列表，查找并点击指定元素
        :param xpath:
        :param distance: 滑动距离，默认 1000
        :param duration: 滑动时间，默认 0.5 秒
        :param direction: 滑动方向，默认为 1； 1=上滑，2=下滑
        :param count: 滑动次数
        :param end_flag_xpath: 结束标志 xpath
        :param wait_time: 等待时间，默认 10 分钟
        :param interval_time: 轮询间隔时间，默认 0.5 秒
        :param raise_err: 超时是否抛出异常；
        :return:
        """
        if raise_err is None:
            interval_time = self.raise_err

        if direction == 1:
            _end_point = (500, 300)
            _start_point = (500, _end_point[1] + distance)
        elif direction == 2:
            _start_point = (500, 300)
            _end_point = (500, _start_point[1] + distance)
        else:
            raise RuntimeError(f"未知方向：{direction}")

        end_time = time.time() + wait_time
        current_count = 0
        while time.time() < end_time and current_count < count:
            if self.click_element(xpath, wait_time=1, interval_time=0.01):
                return True

            if self.element_exists(end_flag_xpath, wait_time=1, interval_time=0.01):
                return False

            self.swipe(_start_point, _end_point, duration)
            current_count += 1
            time.sleep(interval_time)

        if raise_err:
            raise TimeoutError("`click_element_by_slide` 操作超时。")
        return False

    # #############
    #   文件传输   #
    # #############
    def push_file(self, origin_path: str, to_path: str) -> bool:
        """
        将电脑文件传输到手机端
        :param origin_path: 源文件路径
        :param to_path: 目标存储路径
        :return:

        ex:
        origin_path: /
        to_path: /storage/emulated/0/Android/data/com.aibot.client/files/code479259.png
        """
        if not to_path.startswith("/storage/emulated/0/"):
            to_path = "/storage/emulated/0/" + to_path

        with open(origin_path, "rb") as file:
            data = file.read()

        return self.__push_file("pushFile", to_path, data) == "true"

    def pull_file(self, remote_path: str, local_path: str) -> bool:
        """
        将手机文件传输到电脑端
        :param remote_path: 手机端文件路径
        :param local_path: 电脑本地文件存储路径
        :return:

        ex:
        remote_path: /storage/emulated/0/Android/data/com.aibot.client/files/code479259.png
        local_path: /
        """
        if not remote_path.startswith("/storage/emulated/0/"):
            remote_path = "/storage/emulated/0/" + remote_path

        data = self.__pull_file("pullFile", remote_path)
        if data == b"null":
            return False

        with open(local_path, "wb") as file:
            file.write(data)
        return True

    # #############
    #   设备操作   #
    # #############

    def start_app(self, name: str, wait_time: float = None, interval_time: float = None) -> bool:
        """
        启动 APP
        :param name: APP名字或者包名
        :param wait_time: 等待时间，默认取 self.wait_timeout
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        end_time = time.time() + wait_time
        while time.time() < end_time:
            # 失败
            if self.__send_data("startApp", name) != "true":
                time.sleep(interval_time)
            # 成功
            else:
                return True
        # 超时
        return False

    def get_device_ip(self) -> str:
        """
        获取设备IP地址
        :return:
        """
        return self.client_address[0]

    def get_android_id(self) -> str:
        """
        获取 Android 设备 ID
        :return:
        """
        return self.__send_data("getAndroidId")

    def get_window_size(self) -> Dict[str, float]:
        """
        获取屏幕大小
        :return:
        """
        width, height = self.__send_data("getWindowSize").split("|")
        return {"width": float(width), "height": float(height)}

    def get_image_size(self, image_path) -> Dict[str, float]:
        """
        获取图片大小
        :param image_path: 图片路径；
        :return:
        """
        width, height = self.__send_data("getImageSize", image_path).split("|")
        return {"width": float(width), "height": float(height)}

    def show_toast(self, text: str) -> bool:
        """
        Toast 弹窗
        :param text: 弹窗内容；
        :return:
        """
        return self.__send_data("showToast", text) == "true"

    def send_keys(self, text: str) -> bool:
        """
        发送文本，需要打开 AiBot 输入法
        :param text: 文本内容
        :return:
        """
        return self.__send_data("sendKeys", text) == "true"

    def send_vk(self, vk: int) -> bool:
        """
        发送文本，需要打开 AiBot 输入法
        :param vk: 虚拟键值
        :return:

        虚拟键值按键对照表 https://blog.csdn.net/yaoyaozaiye/article/details/122826340
        """
        return self.__send_data("sendVk", vk) == "true"

    # def write_android_file(self):
    #     """TODO"""
    #     raise NotImplementedError()
    #
    # def read_android_file(self):
    #     """TODO"""
    #     raise NotImplementedError()

    def back(self) -> bool:
        """
        返回
        :return:
        """
        return self.__send_data("back") == "true"

    def home(self) -> bool:
        """
        返回桌面
        :return:
        """
        return self.__send_data("home") == "true"

    def recent_tasks(self) -> bool:
        """
        显示最近任务
        :return:
        """
        return self.__send_data("recents") == "true"

    def open_uri(self, uri: str) -> bool:
        """
        唤起 app
        :param uri: app 唤醒协议
        :return:

        open_uri("alipayqr://platformapi/startapp?saId=10000007")
        """
        return self.__send_data("openUri", uri) == "true"

    def call_phone(self, mobile: str) -> bool:
        """
        拨打电话
        :param mobile: 手机号码
        :return:
        """
        return self.__send_data("callPhone", mobile) == "true"

    def send_msg(self, mobile, text) -> bool:
        """
        发送短信
        :param mobile: 手机号码
        :param text: 短信内容
        :return:
        """
        return self.__send_data("sendMsg", mobile, text) == "true"

    def get_activity(self) -> str:
        """
        获取活动页
        :return:
        """
        return self.__send_data("getActivity")

    def get_package(self) -> str:
        """
        获取包名
        :return:
        """
        return self.__send_data("getPackage")

    def set_clipboard_text(self, text: str) -> bool:
        """
        设置剪切板文本
        :param text:
        :return:
        """
        return self.__send_data("setClipboardText", text) == "true"

    def get_clipboard_text(self) -> str:
        """
        获取剪切板内容
        :return:
        """
        return self.__send_data("getClipboardText")

    # ##############
    #   控件与参数   #
    # ##############
    def create_text_view(self, _id: int, text: str, x: int, y: int, width: int = 400, height: int = 60):
        """
        创建文本框控件
        :param _id:  控件ID，不可与其他控件重复
        :param text:  控件文本
        :param x:  控件在屏幕上x坐标
        :param y:  控件在屏幕上y坐标
        :param width:  控件宽度，默认 400
        :param height:  控件高度，默认 60
        :return:
        """
        return self.__send_data("createTextView", _id, text, x, y, width, height)

    def create_edit_view(self, _id: int, text: str, x: int, y: int, width: int = 400, height: int = 150):
        """
        创建编辑框控件
        :param _id:  控件ID，不可与其他控件重复
        :param text:  控件文本
        :param x:  控件在屏幕上x坐标
        :param y:  控件在屏幕上y坐标
        :param width:  控件宽度，默认 400
        :param height:  控件高度，默认 150
        :return:
        """
        return self.__send_data("createEditText", _id, text, x, y, width, height)

    def create_check_box(self, _id: int, text: str, x: int, y: int, width: int = 400, height: int = 60):
        """
        创建复选框控件
        :param _id:  控件ID，不可与其他控件重复
        :param text:  控件文本
        :param x:  控件在屏幕上x坐标
        :param y:  控件在屏幕上y坐标
        :param width:  控件宽度，默认 400
        :param height:  控件高度，默认 60
        :return:
        """
        return self.__send_data("createCheckBox", _id, text, x, y, width, height)

    def create_web_view(self, _id: int, url: str, x: int = -1, y: int = -1, width: int = -1, height: int = -1) -> bool:
        """
        创建WebView控件
        :param _id: 控件ID，不可与其他控件重复
        :param url: 加载的链接
        :param x: 控件在屏幕上 x 坐标，值为 -1 时自动填充宽高
        :param y: 控件在屏幕上 y 坐标，值为 -1 时自动填充宽高
        :param width: 控件宽度，值为 -1 时自动填充宽高
        :param height: 控件高度，值为 -1 时自动填充宽高
        :return:
        """
        return self.__send_data("createWebView", _id, url, x, y, width, height) == "true"

    def clear_script_widget(self) -> bool:
        """
        清除脚本控件
        :return:
        """
        return self.__send_data("clearScriptControl") == "true"

    def get_script_params(self) -> Optional[dict]:
        """
        获取脚本参数
        :return:
        """
        response = self.__send_data("getScriptParam")
        if response == "null":
            return None
        try:
            params = json.loads(response)
        except Exception as e:
            self.show_toast("获取脚本参数异常!")
            raise e
        return params

    # ##########
    #   其他   #
    ############
    def handle(self) -> None:
        # 设置阻塞模式
        # self.request.setblocking(False)

        # 设置缓冲区
        # self.request.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65535)
        self.request.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024)  # 发送缓冲区 10M

        # 执行脚本
        self.script_main()

    @abc.abstractmethod
    def script_main(self):
        """脚本入口，由子类重写
        """

    @classmethod
    def execute(cls, listen_port: int):
        """
        多线程启动 Socket 服务，执行脚本
        :return:
        """

        if listen_port < 0 or listen_port > 65535:
            raise OSError("`listen_port` must be in 0-65535.")
        print("启动服务...")
        # 获取 IPv4 可用地址
        address_info = socket.getaddrinfo(None, listen_port, socket.AF_INET, socket.SOCK_STREAM, 0, socket.AI_PASSIVE)[
            0]
        *_, socket_address = address_info

        # 启动 Socket 服务
        sock = _ThreadingTCPServer(socket_address, cls, bind_and_activate=True)
        sock.serve_forever()

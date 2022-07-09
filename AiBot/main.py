import abc
import copy
import os
import socket
import socketserver
import sys
import time
import re

from ast import literal_eval
from collections import namedtuple
from pathlib import Path
from typing import Union, List, Optional, Tuple, Dict

from loguru import logger

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

Point = namedtuple("Point", ["x", "y"])

_Point = Union[Point, Tuple[int, int]]
_Region = Tuple[int, int, int, int]
_Algorithm = Tuple[int, int, int]
_SubColors = List[Tuple[int, int, str]]


def _protect(*protected):
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


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class AiBotMain(socketserver.BaseRequestHandler, metaclass=_protect("handle", "execute")):
    wait_timeout = 3  # seconds
    interval_timeout = 0.5  # seconds

    log_path = ""
    log_level = "INFO"

    def __init__(self, request, client_address, server):
        self.log = logger

        if self.log_path:
            self.log.add(self.log_path, level=self.log_level.upper(), rotation="12:00",
                         retention="15 days")
        else:
            self.log.remove()
            self.log.add(sys.stdout, level=self.log_level.upper())

        super().__init__(request, client_address, server)

    def __send_data(self, *args) -> str:
        args_len = ""
        args_text = ""

        for argv in args:
            argv = str(argv)
            args_text += argv
            args_len += str(len(bytes(argv, 'utf8'))) + "/"

        data = (args_len.strip("/") + "\n" + args_text).encode("utf8")

        self.log.debug(rf"---> {data}")
        self.request.sendall(data)

        data_length, data = self.request.recv(65535).split(b"/", 1)

        self.log.debug(rf"<--- {data}")

        while int(data_length) > len(data):
            data += self.request.recv(65535)

        return data.decode("utf8").strip()

    def __send_file(self, func_name: str, to_path: str, file: bytes):
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

        self.request.sendall(bytes_data)

        response = self.request.recv(65535)

        data_length, data = response.split(b"/", 1)

        while int(data_length) > len(data):
            data += self.request.recv(65535)

        return data.decode("utf8").strip()

    def __pull_file(self, *args) -> bytes:
        args_len = ""
        args_text = ""

        for argv in args:
            argv = str(argv)
            args_text += argv
            args_len += str(len(bytes(argv, 'utf8'))) + "/"

        data = (args_len.strip("/") + "\n" + args_text).encode("utf8")

        self.request.sendall(data)

        data_length, data = self.request.recv(65535).split(b"/", 1)

        while int(data_length) > len(data):
            data += self.request.recv(65535)

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
            raise ValueError("`image_ name` cannot contain `/`.")

        # 基础存储路径
        base_path = "/storage/emulated/0/Android/data/com.aibot.client/files/"

        if not region:
            region = [0, 0, 0, 0]

        if not algorithm:
            algorithm_type, threshold, max_val = [0, 0, 0]
        else:
            algorithm_type, threshold, max_val = algorithm
            if algorithm_type in (5, 6):
                threshold = 127
                max_val = 255

        response = self.__send_data("saveScreenshot", base_path + image_name, *region,
                                    algorithm_type, threshold, max_val)
        if response == "true":
            return base_path + image_name
        return None

    # #############
    #   色值相关   #
    # #############
    def get_color(self, point: _Point) -> Optional[str]:
        """
        获取指定坐标点的色值，返回色值字符串(#008577)或者 None
        :param point: 坐标点；
        :return:
        """
        response = self.__send_data("getColor", point[0], point[1])
        if response == "null":
            return None
        return response

    def find_color(self, color: str, sub_colors: _SubColors = None, region: _Region = None,
                   similarity: float = 0.9) -> Optional[Point]:
        """
        获取指定色值的坐标点，返回坐标或者 None
        :param color: 颜色字符串，必须以 # 开头，例如：#008577；
        :param sub_colors: 辅助定位的其他颜色；
        :param region: 在指定区域内找色，默认全屏；
        :param similarity: 相似度，0-1 的浮点数，默认 0.9；
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

        end_time = time.time() + self.wait_timeout
        while time.time() < end_time:
            response = self.__send_data("findColor", color, sub_colors_str, *region, similarity)
            # 找色失败
            if response == "-1.0|-1.0":
                time.sleep(self.interval_timeout)
            else:
                # 找色成功
                x, y = response.split("|")
                return Point(x=float(x), y=float(y))
        # 超时
        return None

    # def compare_color(self):
    #     """比较指定坐标点的颜色值"""
    #     raise NotImplementedError()

    # #############
    #   找图相关   #
    # #############
    def find_image(self, image_path, region: _Region = None, algorithm: _Algorithm = None,
                   similarity: float = 0.9) -> Optional[Point]:
        """
        寻找图片坐标，在当前屏幕中寻找给定图片的坐标，返回坐标或者 None
        :param image_path: 图片的绝对路径；
        :param region: 从指定区域中找图，默认全屏；
        :param algorithm: 处理屏幕截图所用的算法，默认原图，注意：给定图片处理时所用的算法，应该和此方法的算法一致；
        :param similarity: 相似度，0-1 的浮点数，默认 0.9；
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
        if not region:
            region = [0, 0, 0, 0]

        if not algorithm:
            algorithm_type, threshold, max_val = [0, 0, 0]
        else:
            algorithm_type, threshold, max_val = algorithm
            if algorithm_type in (5, 6):
                threshold = 127
                max_val = 255

        end_time = time.time() + self.wait_timeout
        while time.time() < end_time:
            response = self.__send_data("findImage", image_path, *region, similarity,
                                        algorithm_type, threshold, max_val)
            # 找图失败
            if response == "-1.0|-1.0":
                time.sleep(self.interval_timeout)
            else:
                # 找图成功，返回图片左上角坐标
                x, y = response.split("|")
                return Point(x=float(x), y=float(y))
        # 超时
        return None

    def find_image_by_opencv(self, image_path, region: _Region = None, algorithm: _Algorithm = None,
                             similarity: float = 0.9) -> Optional[Point]:
        """
        寻找图片坐标，在当前屏幕中寻找给定图片的坐标，返回图片坐标或者 None
        与 self.find_image() 基本一致，采用 OpenCV 算法
        :param image_path: 图片的绝对路径；
        :param region: 从指定区域中找图，默认全屏；
        :param algorithm: 处理屏幕截图所用的算法，默认原图，注意：给定图片处理时所用的算法，应该和此方法的算法一致；
        :param similarity: 相似度，0-1 的浮点数，默认 0.9；
        :param multi: 目标数量，默认为 1，找到 1 个目标后立即结束；
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
        result = self.find_images_by_opencv(image_path, region, algorithm, similarity, multi=1)
        if not result:
            return None
        return result[0]

    def find_images_by_opencv(self, image_path, region: _Region = None, algorithm: _Algorithm = None,
                              similarity: float = 0.9, multi: int = 1) -> List[Point]:
        """
        寻找图片坐标，在当前屏幕中寻找给定图片的坐标，返回坐标列表
        与 self.find_image() 基本一致，采用 OpenCV 算法，并且可找多个目标。
        :param image_path: 图片的绝对路径；
        :param region: 从指定区域中找图，默认全屏；
        :param algorithm: 处理屏幕截图所用的算法，默认原图，注意：给定图片处理时所用的算法，应该和此方法的算法一致；
        :param similarity: 相似度，0-1 的浮点数，默认 0.9；
        :param multi: 目标数量，默认为 1，找到 1 个目标后立即结束；
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
        if not region:
            region = [0, 0, 0, 0]

        if not algorithm:
            algorithm_type, threshold, max_val = [0, 0, 0]
        else:
            algorithm_type, threshold, max_val = algorithm
            if algorithm_type in (5, 6):
                threshold = 127
                max_val = 255

        end_time = time.time() + self.wait_timeout
        while time.time() < end_time:
            response = self.__send_data("findImage", image_path, *region, similarity,
                                        algorithm_type, threshold, max_val, multi)
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
                    point_list.append(Point(x=float(x), y=float(y)))
                return point_list
        # 超时
        return []

    def find_dynamic_image(self, interval_time, region: _Region = None) -> List[Point]:
        """
        找动态图，对比同一张图在不同时刻是否发生变化，返回坐标列表
        :param interval_time: 前后时刻的间隔时间；
        :param region: 在指定区域找图，默认全屏；
        :return:

        # 区域相关参数
        region = (0, 0, 0, 0) 按元素顺序分别代表：起点x、起点y、终点x、终点y，最终得到一个矩形。
        """
        if not region:
            region = [0, 0, 0, 0]

        end_time = time.time() + self.wait_timeout
        while time.time() < end_time:
            response = self.__send_data("findAnimation", interval_time, *region)
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
                    point_list.append(Point(x=float(x), y=float(y)))
                return point_list
        # 超时
        return []

    # ################
    #   坐标操作相关   #
    # ################
    def click(self, point: _Point) -> bool:
        """
        点击坐标
        :param point: 坐标；
        :return:
        """
        return self.__send_data("click", point[0], point[1]) == "true"

    def long_click(self, point: _Point, duration: float) -> bool:
        """
        长按坐标
        :param point: 坐标；
        :param duration: 按住时长，单位秒；
        :return:
        """
        return self.__send_data("longClick", point[0], point[1], duration * 1000) == "true"

    def swipe(self, start_point: _Point, end_point: _Point, duration: float) -> bool:
        """
        滑动坐标
        :param start_point: 起始坐标；
        :param end_point: 结束坐标；
        :param duration: 滑动时长，单位秒；
        :return:
        """
        return self.__send_data("swipe", start_point[0], start_point[1], end_point[0], end_point[1],
                                duration * 1000) == "true"

    def gesture(self, gesture_path: List[_Point], duration: float) -> bool:
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

    def __ocr_server(self, host: str, region: _Region = None, scale: float = 1.0) -> list:
        """
        OCR 服务，通过 OCR 识别屏幕中文字
        :param host:
        :param region:
        :param scale:
        :return:
        """
        if not region:
            region = [0, 0, 0, 0]

        response = self.__send_data("ocr", host, *region, scale)
        if response == "null" or response == "":
            return []
        return self.__parse_ocr(response)

    def get_text(self, host: str, region: _Region = None, scale: float = 1.0) -> List[str]:
        """
        通过 OCR 识别屏幕中的文字，返回文字列表
        :param host: OCR 服务地址；
        :param region: 识别区域，默认全屏；
        :param scale: 图片缩放率，默认为 1.0，1.0 以下为缩小，1.0 以上为放大；
        :return:
        """
        text_info_list = self.__ocr_server(host, region, scale)
        text_list = []
        for text_info in text_info_list:
            text = text_info[-1][0]
            text_list.append(text)
        return text_list

    def find_text(self, host: str, text: str, region: _Region = None, scale: float = 1.0) -> List[Point]:
        """
        查找文字所在的坐标，返回坐标列表（坐标是文本区域中心位置）
        :param host: OCR 服务地址；
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

        text_info_list = self.__ocr_server(host, region, scale)

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
                    text_point = Point(
                        x=int(region[0] + (start_x + offset_x) / scale),
                        y=int(region[1] + (start_y + offset_y) / scale)
                    )
                else:
                    text_point = Point(
                        x=int(region[0] + (start_x + offset_x) * 2),
                        y=int(region[1] + (start_y + offset_y) * 2)
                    )
                text_points.append(text_point)

        return text_points

    # #############
    #   元素操作   #
    ###############
    def get_element_rect(self, xpath: str) -> Optional[Tuple[Point, Point]]:
        """
        获取元素位置，返回元素区域左上角和右下角坐标
        :param xpath: xpath 路径
        :return:
        """
        data = self.__send_data("getElementRect", xpath)
        if data == "-1|-1|-1|-1":
            return None
        start_x, start_y, end_x, end_y = data.split("|")
        return Point(x=start_x, y=start_y), Point(x=end_x, y=end_y)

    def get_element_text(self, xpath: str) -> Optional[str]:
        """
        获取元素文本
        :param xpath: xpath 路径
        :return:
        """
        data = self.__send_data("getElementText", xpath)
        if data == "null":
            return None
        return data

    def set_element_text(self, xpath: str, text: str) -> bool:
        """
        设置元素文本
        :param xpath:
        :param text:
        :return:
        """
        return self.__send_data("setElementText", xpath, text) == "true"

    def click_element(self, xpath: str) -> bool:
        """
        点击元素
        :param xpath:
        :return:
        """
        return self.__send_data("clickElement", xpath) == "true"

    def scroll_element(self, xpath: str, direction: int = 0) -> bool:
        """
        滚动元素，0 向上滑动，1 向下滑动
        :param xpath: xpath 路径
        :param direction: 滚动方向，0 向上滑动，1 向下滑动
        :return:
        """
        return self.__send_data("scrollElement", xpath, direction) == "true"

    # #############
    #   文件传输   #
    # #############
    def push_file(self, origin_path: str, to_path: str) -> bool:
        """
        将电脑文件传输到手机端
        :param origin_path: 源文件路径
        :param to_path: 目标存储路径
        :return:
        """
        to_path = "/storage/emulated/0/" + to_path

        with open(origin_path, "rb") as file:
            data = file.read()

        return self.__send_file("pushFile", to_path, data) == "true"

    def pull_file(self, remote_path: str, local_path: str) -> bool:
        """
        将手机文件传输到电脑端
        :param remote_path: 手机端文件路径
        :param local_path: 电脑本地文件存储路径
        :return:
        """
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

    def start_app(self, name: str) -> bool:
        """
        启动 APP
        :param name: APP名字或者包名
        :return:
        """
        return self.__send_data("startApp", name) == "true"

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
        response = self.__send_data("showToast", text)
        return response == "true"

    def send_keys(self, text: str) -> bool:
        """
        发送文本，需要打开 AiBot 输入法
        :param text: 文本内容
        :return:
        """
        return self.__send_data("sendKeys", text) == "true"

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

    def recent_tasks(self):
        """
        显示最近任务
        :return:
        """
        return self.__send_data("recents") == "true"

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
        # 脚本执行完毕后，阻塞
        self.request.recv(1024)

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
        *_, socket_address = address_info

        # 启动 Socket 服务
        sock = _ThreadingTCPServer(socket_address, cls, bind_and_activate=True)
        sock.serve_forever()

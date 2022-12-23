import abc
import socket
import socketserver
import subprocess
import sys
import threading
import time
import re
from ast import literal_eval
from typing import Optional, List, Tuple

from loguru import logger

from ._utils import _protect, _Point, _Region, _Algorithm, _SubColors


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class WinBotMain(socketserver.BaseRequestHandler, metaclass=_protect("handle", "execute")):
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

        with self._lock:
            self.log.debug(rf"->-> {data}")
            self.request.sendall(data)
            response = self.request.recv(65535)
            if response == b"":
                raise ConnectionAbortedError(f"{self.client_address[0]}:{self.client_address[1]} 客户端断开链接。")
            data_length, data = response.split(b"/", 1)
            while int(data_length) > len(data):
                data += self.request.recv(65535)
            self.log.debug(rf"<-<- {data}")

        return data.decode("utf8").strip()

    # #############
    #   窗口操作   #
    # #############
    def find_window(self, class_name: str = None, window_name: str = None) -> Optional[str]:
        """
        查找窗口句柄，仅查找顶级窗口，不包含子窗口
        :param class_name: 窗口类名
        :param window_name: 窗口名
        :return:
        """
        response = self.__send_data("findWindow", class_name, window_name)
        if response == "null":
            return None
        return response

    def find_windows(self, class_name: str = None, window_name: str = None) -> List[str]:
        """
        查找窗口句柄数组，仅查找顶级窗口，不包含子窗口
        class_name 和 window_name 都为 None，则返回所有窗口句柄
        :param class_name: 窗口类名
        :param window_name: 窗口名
        :return:
        """
        response = self.__send_data("findWindows", class_name, window_name)
        if response == "null":
            return []
        return response.split("|")

    def find_sub_window(self, hwnd: str, class_name: str = None, window_name: str = None) -> Optional[str]:
        """
        查找子窗口句柄
        :param hwnd: 当前窗口句柄
        :param class_name: 窗口类名
        :param window_name: 窗口名
        :return:
        """
        response = self.__send_data("findSubWindow", hwnd, class_name, window_name)
        if response == "null":
            return None
        return response

    def find_parent_window(self, hwnd: str) -> Optional[str]:
        """
        查找父窗口句柄
        :param hwnd: 当前窗口句柄
        :return:
        """
        response = self.__send_data("findParentWindow", hwnd)
        if response == "null":
            return None
        return response

    def get_window_name(self, hwnd: str) -> Optional[str]:
        """
        获取窗口名称
        :param hwnd: 当前窗口句柄
        :return:
        """
        response = self.__send_data("getWindowName", hwnd)
        if response == "null":
            return None
        return response

    def show_window(self, hwnd: str, show: bool) -> bool:
        """
        显示/隐藏窗口
        :param hwnd: 当前窗口句柄
        :param show: 是否显示窗口
        :return:
        """
        return self.__send_data("showWindow", hwnd, show) == "true"

    def set_window_top(self, hwnd: str, top: bool = True) -> bool:
        """
        设置窗口到最顶层
        :param hwnd: 当前窗口句柄
        :param top: 是否置顶，True 置顶， False 取消置顶
        :return:
        """
        return self.__send_data("setWindowTop", hwnd, top) == "true"

    # #############
    #   键鼠操作   #
    # #############
    def move_mouse(self, hwnd: str, x: float, y: float, mode: bool = False, ele_hwnd: str = "0") -> bool:
        """
        移动鼠标
        :param hwnd: 当前窗口句柄
        :param x: 横坐标
        :param y: 纵坐标
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作
        :param ele_hwnd: 元素句柄，如果 mode=True 且目标控件有单独的句柄，则需要通过 get_element_window 获得元素句柄，指定 ele_hwnd 的值(极少应用窗口由父窗口响应消息，则无需指定);
        :return:
        """
        return self.__send_data("moveMouse", hwnd, x, y, mode, ele_hwnd) == "true"

    def scroll_mouse(self, hwnd: str, x: float, y: float, count: int, mode: bool = False) -> bool:
        """
        滚动鼠标
        :param hwnd: 当前窗口句柄
        :param x: 横坐标
        :param y: 纵坐标
        :param count: 鼠标滚动次数, 负数下滚鼠标, 正数上滚鼠标
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作
        :return:
        """
        return self.__send_data("rollMouse", hwnd, x, y, count, mode) == "true"

    def click_mouse(self, hwnd: str, x: float, y: float, typ: int, mode: bool = False, ele_hwnd: str = "0") -> bool:
        """
        鼠标点击
        :param hwnd: 当前窗口句柄
        :param x: 横坐标
        :param y: 纵坐标
        :param typ: 点击类型，单击左键:1 单击右键:2 按下左键:3 弹起左键:4 按下右键:5 弹起右键:6 双击左键:7 双击右键:8
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作
        :param ele_hwnd: 元素句柄，如果 mode=True 且目标控件有单独的句柄，则需要通过 get_element_window 获得元素句柄，指定 ele_hwnd 的值(极少应用窗口由父窗口响应消息，则无需指定);
        :return:
        """
        return self.__send_data("clickMouse", hwnd, x, y, typ, mode, ele_hwnd) == "true"

    def send_keys(self, text: str) -> bool:
        """
        输入文本
        :param text: 输入的文本
        :return:
        """
        return self.__send_data("sendKeys", text) == "true"

    def send_keys_by_hwnd(self, hwnd: str, text: str) -> bool:
        """
        后台输入文本(杀毒软件可能会拦截)
        :param hwnd: 窗口句柄
        :param text: 输入的文本
        :return:
        """
        return self.__send_data("sendKeysByHwnd", hwnd, text) == "true"

    def send_vk(self, vk: int, typ: int) -> bool:
        """
        输入虚拟键值(VK)
        :param vk: VK键值
        :param typ: 输入类型，按下弹起:1 按下:2 弹起:3
        :return:
        """
        return self.__send_data("sendVk", vk, typ) == "true"

    def send_vk_by_hwnd(self, hwnd: str, vk: int, typ: int) -> bool:
        """
        后台输入虚拟键值(VK)
        :param hwnd: 窗口句柄
        :param vk: VK键值
        :param typ: 输入类型，按下弹起:1 按下:2 弹起:3
        :return:
        """
        return self.__send_data("sendVkByHwnd", hwnd, vk, typ) == "true"

    # #############
    #   图色操作   #
    # #############
    def save_screenshot(self, hwnd: str, save_path: str, region: _Region = None, algorithm: _Algorithm = None,
                        mode: bool = False) -> bool:
        """
        截图
        :param hwnd: 窗口句柄；
        :param save_path: 图片存储路径；
        :param region: 截图区域，默认全屏；
        :param algorithm: 处理截图所用算法和参数，默认保存原图；
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作；
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

        return self.__send_data("saveScreenshot", hwnd, save_path, *region, algorithm_type, threshold, max_val,
                                mode) == "true"

    def get_color(self, hwnd: str, x: float, y: float, mode: bool = False) -> Optional[str]:
        """
        获取指定坐标点的色值，返回色值字符串(#008577)或者 None
        :param hwnd: 窗口句柄；
        :param x: x 坐标；
        :param y: y 坐标；
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作；
        :return:
        """
        response = self.__send_data("getColor", hwnd, x, y, mode)
        if response == "null":
            return None
        return response

    def find_color(self, hwnd: str, color: str, sub_colors: _SubColors = None, region: _Region = None,
                   similarity: float = 0.9, mode: bool = False, wait_time: float = None,
                   interval_time: float = None):
        """
        获取指定色值的坐标点，返回坐标或者 None
        :param hwnd: 窗口句柄；
        :param color: 颜色字符串，必须以 # 开头，例如：#008577；
        :param sub_colors: 辅助定位的其他颜色；
        :param region: 在指定区域内找色，默认全屏；
        :param similarity: 相似度，0-1 的浮点数，默认 0.9；
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作；
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
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
            response = self.__send_data("findColor", hwnd, color, sub_colors_str, *region, similarity, mode)
            # 找色失败
            if response == "-1.0|-1.0":
                time.sleep(interval_time)
            else:
                # 找色成功
                x, y = response.split("|")
                return _Point(x=float(x), y=float(y))
        # 超时
        return None

    def find_images(self, hwnd: str, image_path: str, region: _Region = None, algorithm: _Algorithm = None,
                    similarity: float = 0.9, mode: bool = False, multi: int = 1, wait_time: float = None,
                    interval_time: float = None) -> List[_Point]:
        """
        寻找图片坐标，在当前屏幕中寻找给定图片中心点的坐标，返回坐标列表
        :param hwnd: 窗口句柄；
        :param image_path: 图片的绝对路径；
        :param region: 从指定区域中找图，默认全屏；
        :param algorithm: 处理屏幕截图所用的算法，默认原图，注意：给定图片处理时所用的算法，应该和此方法的算法一致；
        :param similarity: 相似度，0-1 的浮点数，默认 0.9；
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作；
        :param multi: 返回图片数量，默认1张；
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
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
            response = self.__send_data("findImage", hwnd, image_path, *region, similarity, algorithm_type,
                                        threshold,
                                        max_val, multi, mode)
            # 找图失败
            if response in ["-1.0|-1.0", "-1|-1"]:
                time.sleep(interval_time)
                continue
            else:
                # 找图成功，返回图片左上角坐标
                # 分割出多个图片的坐标
                image_points = response.split("/")
                point_list = []
                for point_str in image_points:
                    x, y = point_str.split("|")
                    point_list.append(_Point(x=float(x), y=float(y)))
                return point_list
        # 超时
        return []

    def find_dynamic_image(self, hwnd: str, interval_ti: int, region: _Region = None, mode: bool = False,
                           wait_time: float = None, interval_time: float = None) -> List[_Point]:
        """
        找动态图，对比同一张图在不同时刻是否发生变化，返回坐标列表
        :param hwnd: 窗口句柄；
        :param interval_ti: 前后时刻的间隔时间，单位毫秒；
        :param region: 在指定区域找图，默认全屏；
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作；
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        if not region:
            region = [0, 0, 0, 0]

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data("findAnimation", hwnd, interval_ti, *region, mode)
            # 找图失败
            if response == "-1.0|-1.0":
                time.sleep(interval_time)
                continue
            else:
                # 找图成功，返回图片左上角坐标
                # 分割出多个图片的坐标
                image_points = response.split("/")
                point_list = []
                for point_str in image_points:
                    x, y = point_str.split("|")
                    point_list.append(_Point(x=float(x), y=float(y)))
                return point_list
        # 超时
        return []

    # ##############
    #   OCR 相关   #
    # ##############
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

    def __ocr_server(self, hwnd: str, region: _Region = None, mode: bool = False) -> list:
        """
        OCR 服务，通过 OCR 识别屏幕中文字
        :param hwnd:
        :param region:
        :param mode:
        :return:
        """
        if not region:
            region = [0, 0, 0, 0]

        response = self.__send_data("ocr", hwnd, *region, mode)
        if response == "null" or response == "":
            return []
        return self.__parse_ocr(response)

    def __ocr_server_by_file(self, image_path: str, region: _Region = None) -> list:
        """
        OCR 服务，通过 OCR 识别屏幕中文字
        :param image_path:
        :param region:
        :return:
        """
        if not region:
            region = [0, 0, 0, 0]

        response = self.__send_data("ocrByFile", image_path, *region)
        if response == "null" or response == "":
            return []
        return self.__parse_ocr(response)

    def get_text(self, hwnd_or_image_path: str, region: _Region = None, mode: bool = False) -> List[str]:
        """
        通过 OCR 识别窗口/图片中的文字，返回文字列表
        :param hwnd_or_image_path: 窗口句柄或者图片路径；
        :param region: 识别区域，默认全屏；
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作；
        :return:
        """
        if hwnd_or_image_path.isdigit():
            # 句柄
            text_info_list = self.__ocr_server(hwnd_or_image_path, region, mode)
        else:
            # 图片
            text_info_list = self.__ocr_server_by_file(hwnd_or_image_path, region)

        text_list = []
        for text_info in text_info_list:
            text = text_info[-1][0]
            text_list.append(text)
        return text_list

    def find_text(self, hwnd_or_image_path: str, text: str, region: _Region = None, mode: bool = False) -> List[_Point]:
        """
        通过 OCR 识别窗口/图片中的文字，返回文字列表
        :param hwnd_or_image_path: 识别区域，默认全屏；
        :param text: 要查找的文字；
        :param region: 识别区域，默认全屏；
        :param mode: 操作模式，后台 true，前台 false, 默认前台操作；
        :return:
        """
        if not region:
            region = [0, 0, 0, 0]

        if hwnd_or_image_path.isdigit():
            # 句柄
            text_info_list = self.__ocr_server(hwnd_or_image_path, region, mode)
        else:
            # 图片
            text_info_list = self.__ocr_server_by_file(hwnd_or_image_path, region)

        text_points = []
        for text_info in text_info_list:
            if text in text_info[-1][0]:
                points, words_tuple = text_info

                left, _, right, _ = points

                # 文本区域起点坐标
                start_x = left[0]
                start_y = left[1]
                # 文本区域终点坐标
                end_x = right[0]
                end_y = right[1]
                # 文本区域中心点据左上角的偏移量
                # 可能指定文本只是部分文本，要计算出实际位置(x轴)
                width = end_x - start_x
                height = end_y - start_y
                words: str = words_tuple[0]

                # 单字符宽度
                single_word_width = width / len(words)
                # 文本在整体文本的起始位置
                pos = words.find(text)

                offset_x = single_word_width * (pos + len(text) / 2)
                offset_y = height / 2

                # 计算文本区域中心坐标
                text_point = _Point(
                    x=float(region[0] + start_x + offset_x),
                    y=float(region[1] + start_y + offset_y),
                )
                text_points.append(text_point)

        return text_points

    # ##############
    #   元素操作   #
    # ##############

    def get_element_name(self, hwnd: str, xpath: str, wait_time: float = None, interval_time: float = None) \
            -> Optional[str]:
        """
        获取元素名称
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data("getElementName", hwnd, xpath)
            if response == "null":
                time.sleep(interval_time)
                continue
            else:
                return response
        # 超时
        return None

    def get_element_value(self, hwnd: str, xpath: str, wait_time: float = None, interval_time: float = None) \
            -> Optional[str]:
        """
        获取元素文本
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data("getElementValue", hwnd, xpath)
            if response == "null":
                time.sleep(interval_time)
                continue
            else:
                return response
        # 超时
        return None

    def get_element_rect(self, hwnd: str, xpath: str, wait_time: float = None, interval_time: float = None) \
            -> Optional[Tuple[_Point, _Point]]:
        """
        获取元素矩形，返回左上和右下坐标
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data("getElementRect", hwnd, xpath)
            if response == "-1|-1|-1|-1":
                time.sleep(interval_time)
                continue
            else:
                x1, y1, x2, y2 = response.split("|")
                return _Point(x=float(x1), y=float(y1)), _Point(x=float(x2), y=float(y2))
        # 超时
        return None

    def get_element_window(self, hwnd: str, xpath: str, wait_time: float = None, interval_time: float = None) \
            -> Optional[str]:
        """
        获取元素窗口句柄
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data("getElementWindow", hwnd, xpath)
            if response == "null":
                time.sleep(interval_time)
                continue
            else:
                return response
        # 超时
        return None

    def click_element(self, hwnd: str, xpath: str, typ: int, wait_time: float = None,
                      interval_time: float = None) -> bool:
        """
        获取元素窗口句柄
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :param typ: 操作类型，单击左键:1 单击右键:2 按下左键:3 弹起左键:4 按下右键:5 弹起右键:6 双击左键:7 双击右键:8
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data('clickElement', hwnd, xpath, typ)
            if response == "false":
                time.sleep(interval_time)
                continue
            else:
                return True
        # 超时
        return False

    def set_element_focus(self, hwnd: str, xpath: str, wait_time: float = None,
                          interval_time: float = None) -> bool:
        """
        设置元素作为焦点
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data('setElementFocus', hwnd, xpath)
            if response == "false":
                time.sleep(interval_time)
                continue
            else:
                return True
        # 超时
        return False

    def set_element_value(self, hwnd: str, xpath: str, value: str,
                          wait_time: float = None, interval_time: float = None) -> bool:
        """
        设置元素文本
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :param value: 要设置的内容
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data('setElementValue', hwnd, xpath, value)
            if response == "false":
                time.sleep(interval_time)
                continue
            else:
                return True
        # 超时
        return False

    def scroll_element(self, hwnd: str, xpath: str, horizontal: int, vertical: int,
                       wait_time: float = None, interval_time: float = None) -> bool:
        """
        滚动元素
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :param horizontal: 水平百分比 -1不滚动
        :param vertical: 垂直百分比 -1不滚动
        :param wait_time: 等待时间，默认取 self.wait_timeout；
        :param interval_time: 轮询间隔时间，默认取 self.interval_timeout；
        :return:
        """
        if wait_time is None:
            wait_time = self.wait_timeout

        if interval_time is None:
            interval_time = self.interval_timeout

        end_time = time.time() + wait_time
        while time.time() < end_time:
            response = self.__send_data('setElementScroll', hwnd, xpath, horizontal, vertical)
            if response == "false":
                time.sleep(interval_time)
                continue
            else:
                return True
        # 超时
        return False

    def close_window(self, hwnd: str, xpath: str) -> bool:
        """
        关闭窗口
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :return:
        """
        return self.__send_data('closeWindow', hwnd, xpath) == 'true'

    def set_element_state(self, hwnd: str, xpath: str, state: str) -> bool:
        """
        设置窗口状态
        :param hwnd: 窗口句柄
        :param xpath: 元素路径
        :param state: 0正常 1最大化 2 最小化
        :return:
        """
        return self.__send_data('setWindowState', hwnd, xpath, state) == 'true'

    # ###############
    #   系统剪切板   #
    # ###############
    def set_clipboard_text(self, text: str) -> bool:
        """
        设置剪切板内容
        :param text: 要设置的内容
        :return:
        """
        return self.__send_data("setClipboardText", text) == 'true'

    def get_clipboard_text(self) -> str:
        """
        设置剪切板内容
        :return:
        """
        return self.__send_data("getClipboardText")

    # #############
    #   启动进程   #
    # #############

    def start_process(self, cmd: str, show_window=True, is_wait=False) -> bool:
        """
        执行cmd命令
        :param cmd: 命令
        :param show_window: 是否显示窗口，默认显示
        :param is_wait: 是否等待程序结束， 默认不等待
        :return:
        """
        return self.__send_data("startProcess", cmd, show_window, is_wait) == "true"

    def download_file(self, url: str, file_path: str, is_wait: bool) -> bool:
        """
        下载文件
        :param url: 文件地址
        :param file_path: 文件保存的路径
        :param is_wait: 是否等待下载完成
        :return:
        """
        return self.__send_data("downloadFile", url, file_path, is_wait) == "true"

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
    def execute(cls, listen_port: int, local: bool = True):
        """
        多线程启动 Socket 服务
        :param listen_port: 脚本监听的端口
        :param local: 脚本是否部署在本地
        :return:
        """

        if listen_port < 0 or listen_port > 65535:
            raise OSError("`listen_port` must be in 0-65535.")
        print("启动服务...")
        # 获取 IPv4 可用地址
        address_info = socket.getaddrinfo(None, listen_port, socket.AF_INET, socket.SOCK_STREAM, 0, socket.AI_PASSIVE)[
            0]
        *_, socket_address = address_info

        # 如果是本地部署，则自动启动 WindowsDriver.exe
        if local:
            print("尝试本地启动 WindowsDriver ...")
            try:
                subprocess.Popen(["WindowsDriver.exe", "127.0.0.1", str(listen_port)])
            except FileNotFoundError as e:
                err_msg = """
                        异常排除步骤：
                        1. 检查 Aibote.exe 路径是否存在中文；
                        2. 是否启动 Aibote.exe 初始化环境变量；
                        3. 检查电脑环境变量是否初始化成功，环境变量中是否存在 %Aibote% 开头的；
                        4. 首次初始化环境变量后，是否重启开发工具；
                        5. 是否以管理员权限启动开发工具；
                        """
                print("\033[92m", err_msg, "\033[0m")
                raise e

        # 启动 Socket 服务
        sock = _ThreadingTCPServer(socket_address, cls, bind_and_activate=True)
        sock.serve_forever()

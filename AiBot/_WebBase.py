import json
import random
import socket
import subprocess
import threading
from typing import Optional, Tuple, Any, Literal

from loguru import logger

from ._utils import Point, _Point_Tuple


class WebBotBase:
    raise_err = False
    wait_timeout = 3  # seconds
    interval_timeout = 0.5  # seconds

    log_storage = False
    log_level = "INFO"
    log_size = 10  # MB
    log = logger

    def __init__(self, port):
        self._lock = threading.Lock()
        address_info = socket.getaddrinfo(None, port, socket.AF_INET, socket.SOCK_STREAM)[0]
        family, socket_type, proto, _, socket_address = address_info
        server = socket.socket(family, socket_type, proto)
        server.bind(socket_address)
        server.listen(1)
        print("WebSocket服务启动成功，等待客户端链接...")
        self.request, self.client_address = server.accept()
        print("WebSocket客户端链接成功")

    @classmethod
    def _build(cls, listen_port: int, local: bool = True, driver_params: dict = None) -> "WebBotBase":
        """
        :param listen_port: 脚本监听的端口
        :param local: 脚本是否部署在本地
        :param driver_params: Web 驱动启动参数
        :return:
        """
        if listen_port < 0 or listen_port > 65535:
            raise OSError("`listen_port` must be in 0-65535.")

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
                print("本地 WebDriver 客户端启动成功")
            except FileNotFoundError as e:
                err_msg = "\n异常排除步骤：\n1. 检查 Aibote.exe 路径是否存在中文；\n2. 是否启动 Aibote.exe 初始化环境变量；\n3. 检查电脑环境变量是否初始化成功，环境变量中是否存在 %Aibote% 开头的；\n4. 首次初始化环境变量后，是否重启开发工具；\n5. 是否以管理员权限启动开发工具；\n"
                print("\033[92m", err_msg, "\033[0m")
                raise e

        return WebBotBase(listen_port)

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
            args_len += str(len(bytes(argv, 'utf8'))) + "/"

        data = (args_len.strip("/") + "\n" + args_text).encode("utf8")

        try:
            with self._lock:
                self.log.debug(rf"->>> {data}")
                self.request.sendall(data)
                response = self.request.recv(65535)
                if response == b"":
                    raise ConnectionAbortedError(f"{self.client_address[0]}:{self.client_address[1]} 客户端断开链接。")
                data_length, data = response.split(b"/", 1)
                while int(data_length) > len(data):
                    data += self.request.recv(65535)
                self.log.debug(rf"<<<- {data}")

            return data.decode("utf8").strip()
        except Exception as e:
            self.log.error("send/read tcp data error: " + str(e))
            raise e

    #############
    # 页面和导航 #
    #############
    def goto(self, url: str) -> bool:
        """
        跳转页面

        :param url: url 地址
        :return:
        """
        return self.__send_data("goto", url) == "true"

    def new_page(self, url: str) -> bool:
        """
        新建 Tab 并跳转页面

        :param url: url 地址
        :return:
        """
        return self.__send_data("newPage", url) == "true"

    def back(self) -> bool:
        """
        后退

        :return:
        """
        return self.__send_data("back") == "true"

    def forward(self) -> bool:
        """
        前进

        :return:
        """
        return self.__send_data("forward") == "true"

    def refresh(self) -> bool:
        """
        刷新

        :return:
        """
        return self.__send_data("refresh") == "true"

    def save_screenshot(self, xpath: str = None) -> Optional[str]:
        """
        截图，返回 PNG 格式的 base64

        :param xpath: 元素路径，如果指定该参数则截取元素图片；
        :return: PNG 格式的 base64 的字符串或 None
        """
        if xpath is None:
            response = self.__send_data("takeScreenshot")
        else:
            response = self.__send_data("takeScreenshot", xpath)
        if response == "null":
            return None
        return response

    def get_current_page_id(self) -> Optional[str]:
        """
        获取当前页面 ID

        :return:
        """
        response = self.__send_data("getCurPageId")
        if response == "null":
            return None
        return response

    def get_all_page_id(self) -> list:
        """
        获取所有页面 ID

        :return:
        """
        response = self.__send_data("getAllPageId")
        if response == "null":
            return []
        return response.split("|")

    def switch_to_page(self, page_id: str) -> bool:
        """
        切换到指定页面

        :param page_id: page id
        :return:
        """
        return self.__send_data("switchPage", page_id) == "true"

    def close_current_page(self) -> bool:
        """
        关闭当前页面

        :return:
        """
        return self.__send_data("closePage") == "true"

    def get_current_url(self) -> Optional[str]:
        """
        获取当前页面 URL

        :return: 当前页面 URL 字符串或 None
        """
        response = self.__send_data("getCurrentUrl")
        if response == "webdriver error":
            return None
        return response

    def get_current_title(self) -> Optional[str]:
        """
        获取当前页面标题
        :return:
        """
        response = self.__send_data("getTitle")
        if response == "webdriver error":
            return None
        return response

    ###############
    # iframe 操作 #
    ###############

    def switch_to_frame(self, xpath) -> bool:
        """
        切换到指定 frame

        :param xpath: xpath 路径
        :return:
        """
        return self.__send_data("switchFrame", xpath) == "true"

    def switch_to_main_frame(self) -> bool:
        """
        切回主 frame

        :return:
        """
        return self.__send_data("switchMainFrame") == "true"

    ###########
    # 元素操作 #
    ###########
    def click_element(self, xpath: str) -> bool:
        """
        点击元素

        :param xpath: xpath 路径
        :return:
        """
        return self.__send_data("clickElement", xpath) == "true"

    def get_element_text(self, xpath: str) -> Optional[str]:
        """
        获取元素文本

        :param xpath: xpath 路径
        :return: 元素文本字符串或 None
        """
        response = self.__send_data("getElementText", xpath)
        if response == "null":
            return None
        return response

    def get_element_rect(self, xpath: str) -> Optional[Tuple[Point, Point]]:
        """
        获取元素矩形坐标

        :param xpath: xpath 路径
        :return: 元素矩形坐标或None
        """
        response = self.__send_data("getElementRect", xpath)
        if response == "null":
            return None
        rect: dict = json.loads(response)
        return (Point(x=float(rect.get("left")), y=float(rect.get("top"))),
                Point(x=float(rect.get("right")), y=float(rect.get("bottom"))))

    def get_element_attr(self, xpath: str, attr_name: str) -> Optional[str]:
        """
        获取元素的属性

        :param xpath: xpath 路径
        :param attr_name: 属性名称字符串
        :return:
        """
        response = self.__send_data("getElementAttribute", xpath, attr_name)
        if response == "null":
            return None
        return response

    def get_element_outer_html(self, xpath: str) -> Optional[str]:
        """
        获取元素的 outerHtml

        :param xpath: xpath 路径
        :return:
        """
        response = self.__send_data("getElementOuterHTML", xpath)
        if response == "null":
            return None
        return response

    def get_element_inner_html(self, xpath: str) -> Optional[str]:
        """
        获取元素的 innerHtml

        :param xpath: xpath 路径
        :return:
        """
        response = self.__send_data("getElementInnerHTML", xpath)
        if response == "null":
            return None
        return response

    def is_selected(self, xpath: str) -> bool:
        """
        元素是否已选中

        :param xpath: xpath 路径
        :return:
        """
        return self.__send_data("isSelected", xpath) == "true"

    def is_displayed(self, xpath: str) -> bool:
        """
        元素是否可见

        :param xpath: xpath 路径
        :return:
        """
        return self.__send_data("isDisplayed", xpath) == "true"

    def is_available(self, xpath: str) -> bool:
        """
        元素是否可用

        :param xpath: xpath 路径
        :return:
        """
        return self.__send_data("isEnabled", xpath) == "true"

    def clear_element(self, xpath: str) -> bool:
        """
        清除元素值

        :param xpath: xpath 路径
        :return:
        """
        return self.__send_data("clearElement", xpath) == "true"

    def set_element_focus(self, xpath: str) -> bool:
        """
        设置元素焦点

        :param xpath: xpath 路径
        :return:
        """
        return self.__send_data("setElementFocus", xpath) == "true"

    def upload_file_by_element(self, xpath: str, file_path: str) -> bool:
        """
        通过元素上传文件

        :param xpath:  元素 xpath 路径
        :param file_path: 文件路径
        :return:
        """
        return self.__send_data("uploadFile", xpath, file_path) == "true"

    def send_keys(self, xpath: str, value: str) -> bool:
        """
        输入值；如果元素不能设置焦点，应先 click_mouse 点击元素获得焦点后再输入

        :param xpath: 元素 xpath 路径
        :param value: 输入的内容
        :return:
        """
        return self.__send_data("sendKeys", xpath, value) == "true"

    def set_element_value(self, xpath: str, value: str) -> bool:
        """
        设置元素值

        :param xpath: 元素 xpath 路径
        :param value: 设置的内容
        :return:
        """
        return self.__send_data("setElementValue", xpath, value) == "true"

    def set_element_attr(self, xpath: str, attr_name: str, attr_value: str) -> bool:
        """
        设置元素属性

        :param xpath: 元素 xpath 路径
        :param attr_name: 属性名称
        :param attr_value: 属性值
        :return:
        """
        return self.__send_data("setElementAttribute", xpath, attr_name, attr_value) == "true"

    def send_vk(self, vk: str) -> bool:
        """
        输入值

        :param vk: 输入内容
        :return:
        """
        return self.__send_data("sendVk", vk) == "true"

    ###########
    # 键鼠操作 #
    ###########
    def click_mouse(self, point: _Point_Tuple, typ: int) -> bool:
        """
        点击鼠标

        :param point: 坐标点
        :param typ: 点击类型，单击左键:1 单击右键:2 按下左键:3 弹起左键:4 按下右键:5 弹起右键:6 双击左键:7
        :return:
        """
        return self.__send_data("clickMouse", point[0], point[1], typ) == "true"

    def move_mouse(self, point: _Point_Tuple) -> bool:
        """
        移动鼠标

        :param point: 坐标点
        :return:
        """
        return self.__send_data("moveMouse", point[0], point[1]) == "true"

    def scroll_mouse(self, offset_x: float, offset_y: float, x: float = 0, y: float = 0) -> bool:
        """
        滚动鼠标

        :param offset_x: 水平滚动条移动的距离
        :param offset_y: 垂直滚动条移动的距离
        :param x: 鼠标横坐标位置， 默认为0
        :param y: 鼠标纵坐标位置， 默认为0
        :return:
        """
        return self.__send_data("wheelMouse", offset_x, offset_y, x, y) == "true"

    def click_mouse_by_element(self, xpath: str, typ: int) -> bool:
        """
        根据元素位置点击鼠标(元素中心点)

        :param xpath: 元素 xpath 路径
        :param typ: 点击类型，单击左键:1 单击右键:2 按下左键:3 弹起左键:4 按下右键:5 弹起右键:6 双击左键:7
        :return:
        """
        return self.__send_data("clickMouseByXpath", xpath, typ) == "true"

    def move_to_element(self, xpath: str) -> bool:
        """
        移动鼠标到元素位置(元素中心点)

        :param xpath: 元素 xpath 路径
        :return:
        """
        return self.__send_data("moveMouseByXpath", xpath) == "true"

    def scroll_mouse_by_element(self, xpath: str, offset_x: float, offset_y: float) -> bool:
        """
        根据元素位置滚动鼠标

        :param xpath: 元素路径
        :param offset_x: 水平滚动条移动的距离
        :param offset_y: 垂直滚动条移动的距离
        :return:
        """
        return self.__send_data("wheelMouseByXpath", xpath, offset_x, offset_y) == "true"
    
    def touch_start(self, x: float, y: float) -> bool:
        """
        仿真模式 开始触屏

        :param offset_x: x 非Windows坐标，页面左上角为起始坐标，可以通过getElementRect 获取相关坐标
        :param offset_y: y 非Windows坐标，页面左上角为起始坐标，可以通过getElementRect 获取相关坐标
        :return:
        """
        return self.__send_data("touchStart", x, y) == "true"
    
    def touch_move(self, x: float, y: float) -> bool:
        """
        仿真模式 移动触屏

        :param offset_x: x 非Windows坐标，页面左上角为起始坐标，可以通过getElementRect 获取相关坐标
        :param offset_y: y 非Windows坐标，页面左上角为起始坐标，可以通过getElementRect 获取相关坐标
        :return:
        """
        return self.__send_data("touchMove", x, y) == "true"
    
    def touch_end(self, x: float, y: float) -> bool:
        """
        仿真模式 结束触屏

        :param offset_x: x 一般同最后一个触屏事件的坐标一致
        :param offset_y: y 一般同最后一个触屏事件的坐标一致
        :return:
        """
        return self.__send_data("touchEnd", x, y) == "true"

    #############
    #   Alert   #
    #############
    def click_alert(self, accept: bool, prompt_text: str = "") -> bool:
        """
        点击警告框

        :param accept: 确认或取消
        :param prompt_text: 可选参数，输入的警告框文本
        :return:
        """
        return self.__send_data("clickAlert", accept, prompt_text) == "true"

    def get_alert_text(self) -> Optional[str]:
        """
        获取警告框文本

        :return: 警告框文本字符串
        """
        response = self.__send_data("getAlertText")
        if response == "null":
            return None
        return response

    ###############
    #   窗口操作   #
    ###############
    def get_window_pos(self) -> Optional[dict]:
        """
        获取窗口位置和状态

        :return: 返回窗口左上角坐标点，宽度和高度，状态
        """
        response = self.__send_data("getWindowPos")
        if response == "null":
            return None
        resp: dict = json.loads(response)
        return {
            "pos": Point(x=float(resp.get("left")), y=float(resp.get("top"))),
            "size": {"width": float(resp.get("width")), "height": float(resp.get("height"))},
            "status": resp.get("windowState")
        }

    def set_window_pos(self, left: float, top: float, width: float, height: float, status) -> bool:
        """
        设置窗口位置和状态

        :param left: 窗口 x 坐标
        :param top: 窗口 y 坐标
        :param width: 宽度
        :param height: 高度
        :param status: 状态
        :return:
        """
        return self.__send_data("setWindowPos", status, left, top, width, height) == "true"

    def mobile_emulation(self, width: int, height: int, ua: str, _sys: Literal["Android", "iOS"], sys_version: str,
                         lang: str = "", tz: str = "", latitude: float = 0, longitude: float = 0,
                         accuracy: float = 0) -> bool:
        """
        模拟移动端浏览器

        :param width: 宽度
        :param height: 高度
        :param ua: 用户代理
        :param _sys: 系统
        :param sys_version: 系统版本
        :param lang: 语言
        :param tz: 时区
        :param latitude: 纬度
        :param longitude: 经度
        :param accuracy: 准确度
        :return:
        """
        return self.__send_data("mobileEmulation", width, height, ua, _sys, sys_version, lang, tz, latitude, longitude,
                                accuracy) == "true"

    ###############
    #   Cookies   #
    ###############

    def get_cookies(self, url: str) -> Optional[list]:
        """
        获取指定 url 的 Cookies

        :param url: url 字符串
        :return:
        """
        response = self.__send_data("getCookies", url)
        if response == "null":
            return None
        return json.loads(response)

    def get_all_cookies(self) -> Optional[list]:
        """
        获取所有的 Cookies

        :return: 列表格式的 cookies
        """
        response = self.__send_data("getAllCookies")
        if response == "null":
            return None
        return json.loads(response)

    def set_cookies(self, url: str, name: str, value: str, options: dict = None) -> bool:
        """
        设置指定 url 的 Cookies

        :param url: 要设置 Cookie 的域
        :param name: Cookie 名
        :param value: Cookie 值
        :param options: 其他属性
        :return:
        """
        default_options = {
            "domain": "",
            "path": "",
            "secure": False,
            "httpOnly": False,
            "sameSite": "",
            "expires": 0,
            "priority": "",
            "sameParty": False,
            "sourceScheme": "",
            "sourcePort": 0,
            "partitionKey": "",
        }
        if options:
            default_options.update(options)

        return self.__send_data("setCookie", name, value, url, *default_options.values()) == "true"

    def delete_cookies(self, name: str, url: str = "", domain: str = "", path: str = "") -> bool:
        """
        删除指定 Cookie

        :param name: 要删除的 Cookie 的名称
        :param url: 删除所有匹配 url 和 name 的 Cookie
        :param domain: 删除所有匹配 domain 和 name 的 Cookie
        :param path: 删除所有匹配 path 和 name 的 Cookie
        :return:
        """
        return self.__send_data("deleteCookies", name, url, domain, path) == "true"

    def delete_all_cookies(self) -> bool:
        """
        删除所有 Cookie

        :return:
        """
        return self.__send_data("deleteAllCookies") == "true"

    def clear_cache(self) -> bool:
        """
        清除缓存

        :return:
        """
        return self.__send_data("clearCache") == "true"

    ##############
    #   JS 注入   #
    ##############
    def execute_script(self, script: str) -> Optional[Any]:
        """
        注入执行 JS

        :param script: 要执行的 JS 代码
        :return: 假如注入代码有返回值，则返回此值，否则返回 None;

        Examples:

        result = execute_script('(()=>"aibote rpa")()')
        print(result)
        "aibote rpa"

        """
        response = self.__send_data("executeScript", script)
        if response == "null":
            return None
        return response

    #################
    #   浏览器操作   #
    #################
    def quit(self) -> bool:
        """
        退出浏览器

        :return:
        """
        return self.__send_data("closeBrowser") == "true"

    #################
    #   驱动程序相关   #
    #################
    def get_extend_param(self) -> Optional[str]:
        """
        获取WebDriver.exe 命令扩展参数

        :return: WebDriver 驱动程序的命令行["extendParam"] 字段的参数
        """
        return self.__send_data("getExtendParam")

    def close_driver(self) -> bool:
        """
        关闭WebDriver.exe驱动程序

        :return:
        """
        return self.__send_data("closeDriver") == "true"

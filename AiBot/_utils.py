import abc
import socket
import socketserver
from typing import Union, Tuple, List

Log_Format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | " \
             "<level>{level: <8}</level> | " \
             "{process.id} - {thread.id: <8} | " \
             "<cyan>{module}:{line}</cyan> | " \
             "<level>{message}</level>"  # 日志内容


class Point:
    def __init__(self, x: float, y: float, driver=None):
        self.x = x
        self.y = y
        self.__driver = driver

    def __getitem__(self, item):
        if item == 0:
            return self.x
        elif item == 1:
            return self.y
        else:
            raise IndexError("list index out of range")

    def __repr__(self):
        return f"Point(x={self.x}, y={self.y})"

    def click(self, offset_x: float = 0, offset_y: float = 0):
        """
        点击坐标

        :param offset_x: 坐标 x 轴偏移量
        :param offset_y: 坐标 y 轴偏移量
        :return:
        """
        return self.__driver.click(self, offset_x=offset_x, offset_y=offset_y)

    def get_points_center(self, other_point: "Point") -> "Point":
        """
        获取两个坐标点的中间坐标

        :param other_point: 其他的坐标点
        :return: Point
        """
        return self.__class__(x=self.x + (other_point.x - self.x) / 2, y=self.y + (other_point.y - self.y) / 2,
                              driver=self.__driver)


class Point2s:
    """
    代替 Point 元组
    """

    def __init__(self, p1: Point, p2: Point):
        self.p1 = p1
        self.p2 = p2

    def __getitem__(self, item):
        if item == 0:
            return self.p1
        elif item == 1:
            return self.p2
        else:
            raise IndexError("list index out of range")

    def __repr__(self):
        return f"({self.p1}, {self.p2})"

    def click(self, offset_x: float = 0, offset_y: float = 0) -> bool:
        """
        点击元素的中心坐标

        :param offset_x:
        :param offset_y:
        :return:
        """
        return self.central_point().click(offset_x=offset_x, offset_y=offset_y)

    def central_point(self) -> Point:
        """
        获取元素的中心坐标

        :return:
        """
        return self.p1.get_points_center(self.p2)


_Point_Tuple = Union[Point, Tuple[float, float]]
_Region = Tuple[float, float, float, float]
_Algorithm = Tuple[int, int, int]
_SubColors = List[Tuple[int, int, str]]


def _protect(*protected):
    """
    元类工厂，禁止类属性或方法被子类重写

    :param protected: 禁止重写的属性或方法
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


def get_local_ip() -> str:
    """
    获取局域网IP
    :return:
    """
    try:
        # 创建一个UDP套接字
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接外部地址（这里使用百度的DNS服务器）
        sock.connect(('114.114.114.114', 80))
        # 获取本地IP地址
        local_ip = sock.getsockname()[0]
        # 关闭套接字连接
        sock.close()
        return local_ip
    except socket.error:
        return "0.0.0.0"

# ## AiBot 使用方法说明

# 0. 下载 AiBot 库：pip install AiBot.py

# 1. 导入 AiBotMain 类
import time

from AiBot import AiBotMain


# 2. 自定义一个脚本类，继承 AiBotMain
class CustomScript(AiBotMain):
    # 3. 设置等待参数
    # 3.1 设置等待时间
    wait_timeout = 3
    # 3.2 设置重试间隔时长
    interval_timeout = 0.5

    # 4. 重写方法，编写脚本
    # 注意：此方法是脚本执行入口
    def script_main(self):
        self.show_toast("连接成功")
        path = r"D:\PycharmProjects\AiBot\test\单标签.png"
        result = self.push_file(path, "/4.png")
        print(result)
        while True:
            self.show_toast("恭喜发财")
            time.sleep(5)


# 6. 启动服务，执行脚本
if __name__ == '__main__':
    # 监听 3333 号端口
    CustomScript.execute(3333)

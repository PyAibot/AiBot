import time

from AiBot import AiBotMain


class CustomScript(AiBotMain):

    def script_main(self):
        self.show_toast("连接成功")
        while True:
            time.sleep(5)
            self.show_toast("恭喜发财")


if __name__ == '__main__':
    # 监听 3333 号端口
    CustomScript.execute(3333)

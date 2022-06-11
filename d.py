import time

from main import AiBotMain


class AiBotTestScript(AiBotMain):
    def script_main(self):
        self.show_toast("连接成功")
        result = self.get_android_id()
        print(result)
        while True:
            time.sleep(5)
            self.show_toast("恭喜发财")


if __name__ == '__main__':
    AiBotTestScript.execute(3333)

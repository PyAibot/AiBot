import time

from AiBot import AiBotMain


class CustomScript(AiBotMain):

    def script_main(self):
        self.show_toast("连接成功")
        print(self.get_package())
        self.create_check_box(100, "是否恢复理智", 1080, 1920, 0, 10, 400, 100)
        self.create_exit_view(110, "药剂恢复次数", 1080, 1920, 0, 100, 400, 150)
        self.create_exit_view(120, "源石恢复次数", 1080, 1920, 0, 250, 400, 150)
        params = self.get_script_params()
        count = params.get("110")
        count = params.get("110")
        count = params.get("110")
        print("理智恢复次数: ", count)
        while True:
            time.sleep(5)
            self.show_toast("恭喜发财")


if __name__ == '__main__':
    # 监听 3333 号端口
    CustomScript.execute(3333)

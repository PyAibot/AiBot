import time

from AiBot import AiBotMain


class CustomScript(AiBotMain):

    def script_main(self):
        self.show_toast("连接成功")
        self.create_exit_view(100, "理智恢复次数", 1080, 1920, 0, 10, 400, 150)
        self.create_check_box(110, "是否使用源石", 1080, 1920, 500, 10, 400, 150)
        params = self.get_script_params()
        restore_count = params.get("100")
        print("理智恢复次数: ",  restore_count)
        is_use_ys = params.get("110")
        print("是否使用源石: ",  is_use_ys)
        while True:
            time.sleep(5)
            self.show_toast("恭喜发财")


if __name__ == '__main__':
    # 监听 3333 号端口
    CustomScript.execute(3333)

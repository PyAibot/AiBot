import time

from AiBot import AndroidBotMain


class CustomAndroidScript(AndroidBotMain):

    def script_main(self):
        # self.show_toast("连接成功")
        # self.create_text_view(90, "配置参数：", 0, 0)
        # self.create_edit_view(100, "理智恢复次数", 0, 60)
        # self.create_check_box(110, "是否使用源石", 500, 120)
        # params = self.get_script_params()
        # restore_count = params.get("100")
        # is_use_ys = params.get("110")
        # print("理智恢复次数: ", restore_count)
        # print("是否使用源石: ", is_use_ys)
        # while True:
        #     time.sleep(5)
        #     self.show_toast("恭喜发财")
        xpath = "com.aibot.client/android.widget.EditText@text=192.168.68.195"
        points = self.get_element_rect(xpath)
        result = self.press(points[0].get_points_center(points[1]), 3)
        print(result)
        time.sleep(3)


if __name__ == '__main__':
    # 监听 3333 号端口
    CustomAndroidScript.execute(3333)

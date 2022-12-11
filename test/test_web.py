import time

from AiBot import WebBotMain


class CustomWebScript(WebBotMain):
    log_level = "DEBUG"

    def script_main(self):
        self.goto("https://www.baidu.com")
        time.sleep(3)
        self.new_page("https://www.qq.com")
        time.sleep(3)

        result = self.execute_script('(()=>"aibote rpa")()')
        print(result)  # aibote rpa


if __name__ == '__main__':
    # 监听 6666 号端口
    CustomWebScript.execute(9999)

import time

from AiBot import WebBotMain


class CustomWebScript(WebBotMain):
    log_level = "DEBUG"

    def script_main(self):
        print(111)

        while True:
            time.sleep(5)
            print(666)


if __name__ == '__main__':
    # 监听 6666 号端口
    CustomWebScript.execute(9999)

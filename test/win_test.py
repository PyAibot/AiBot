import time

from AiBot import WinBotMain


def main():
    driver = WinBotMain.build(3333)
    r = driver.find_window("TXGuiFoundation")
    print(r)

    r = driver.find_windows(window_name="Ai-Bot 2群等9个会话")
    print(r)
    print(len(r))

    result = driver.find_text("525178", "闲聊群1")
    print(result)


if __name__ == '__main__':
    main()

import time

from AiBot import WinBotMain


def main():
    driver = WinBotMain.build(3333)
    r = driver.find_window("TXGuiFoundation")
    print(r)

    r = driver.find_windows(window_name="Ai-Bot 2群等9个会话")
    print(r)
    print(len(r))

    result = driver.show_window("2688664", True)
    print(result)

    result = driver.find_images("65826", "D:/Aibote/Picture/windows/666.png")
    print(result)


if __name__ == '__main__':
    main()

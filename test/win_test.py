import time

from AiBot import WinBotMain


def main():
    driver = WinBotMain.build(3333)
    r = driver.find_window("TXGuiFoundation")
    print(r)

    r = driver.find_windows(window_name="Ai-Bot 2群等9个会话")
    print(r)
    print(len(r))

    driver.show_window("2688664", True)

    driver.scroll_mouse("2688664", 100, 100, 1)


if __name__ == '__main__':
    main()

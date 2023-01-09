from datetime import datetime, timedelta

import httpx

Cookies = {
    # "_uab_collina": "167240209731858523176669",
    "JSESSIONID": "131DEE9D27EE5FBB4B283ADC596C2670",
    # "tk": "d_draofzx9nCEW27nW8CLG2yAynxSsN5oam3komy_4wtyv1v0",
    # "guidesStatus": "off",
    # "highContrastMode": "defaltMode",
    # "cursorStatus": "off",
    # "_jc_save_fromStation": "%u4E0A%u6D77%2CSHH",
    # "_jc_save_toStation": "%u7800%u5C71%2CDKH",
    # "_jc_save_wfdc_flag": "dc",
    # "BIGipServerotn": "1691943178.64545.0000",
    # "BIGipServerpassport": "904397066.50215.0000",
    # "RAIL_EXPIRATION": "1673044028557",
    # "RAIL_DEVICEID": "VuhG-yFMLjvzAWghgcAcXGia3Ntwe1t0fda2iQ_Tb99SS5c6IE_CfqUkzzXRgOuW62ACcTechOzPFD5PBqna0K6czixcNAJMY2M5mNLcmyapaTsogbRGwZ5DEamGMPljYZPgDjPsW6mUJr8NnckpMbnmXwrTcKUM",
    # "route": "9036359bb8a8a461c164a04f8f50b252",
    # "_jc_save_toDate": "2023-01-03",
    # "uKey": "8d9861491530d3d1ebf3167907d252e3eebcc9b935318d089a9a25c6b06cd3b1",
    # "current_captcha_type": "Z",
    # "fo": "8jz7wbdxala6g9cdnyisxI4hOf8fxHck-W_zlAawc9NLBaMIBNnKR4DUwRYI9KczoMeXiUzv1o3H3ZLatoOXLwNxLGVPc7v_Oz2HJ_INMsdCQx2be_4S-ElX4_LZ68aK2BebcvHTG8KMCx24oXEqG-Bk7aD3HRivIgdTquFlQOus3I424m5IBLbngck",
    # "_jc_save_fromDate": "2023-01-04",
}


def query_ticket(date: str = "2023-01-04", from_station: str = "SHH", to_station: str = "DKH"):
    """
    余票查询
    :param date:
    :param from_station:
    :param to_station:
    :return:
    """
    url = f"https://kyfw.12306.cn/otn/leftTicket/query"
    params = {
        "leftTicketDTO.train_date": date,
        "leftTicketDTO.from_station": from_station,
        "leftTicketDTO.to_station": to_station,
        "purpose_codes": "ADULT"  # 0X00-学生 ADULT-成人
    }
    response = httpx.get(url, params=params, cookies=Cookies)
    if response.status_code == 200:
        resp = response.json()
        station_map = resp["data"]["map"]
        tickets_result = resp["data"]["result"]

        for ticket_info in tickets_result:
            lis = ticket_info.split("|")
            x = lis[0]  # ？
            x = lis[1]  # 预定按钮
            x = lis[2]  # 列车号
            x = lis[3]  # 车次  G1920
            x = lis[4]  # 始发站  AOH
            x = lis[5]  # 终点站
            x = lis[6]  # 出发站
            x = lis[7]  # 到达站
            x = lis[8]  # 出发时刻  09:20
            x = lis[9]  # 到达时刻  13:04
            x = lis[10]  # 乘车用时  03:44
            x = lis[11]  # 能否购买  Y-可，N-不可，IS_TIME_NOT_BUY-调整/停运/暂停发售
            x = lis[12]  # ？
            x = lis[13]  # 乘车日期  20230104
            x = lis[14]  # ？
            x = lis[15]  # ？
            x = lis[16]  # 出发车站次序  01 表示始发站
            x = lis[17]  # 到达车站次序  09 表示第9站
            x = lis[18]  # 是否可凭身份证进站  1-可以 0-不可以
            x = lis[19]  # ？
            x = lis[20]  # ？
            x = lis[21]  # 高级软卧
            x = lis[22]  # 其他
            x = lis[23]  # 软卧，一等卧
            x = lis[24]  # 软卧
            x = lis[25]  # 特等座？
            x = lis[26]  # 无座
            x = lis[27]  # ？
            x = lis[28]  # 硬卧，二等卧
            x = lis[29]  # 硬座
            x = lis[30]  # 二等座
            x = lis[31]  # 一等座
            x = lis[32]  # 商务特等座
            x = lis[33]  # 动卧

            x = lis[34]  # 查询车票价格时的 seat_types 字段
            x = lis[35]  # ？
            x = lis[36]  # ？

            train_code = lis[3]  # 车次
            # start_station = station_map[lis[4]]  # 始发站  AOH
            # end_station = station_map[lis[5]]  # 终点站
            from_station = station_map[lis[6]]  # 出发站
            to_station = station_map[lis[7]]  # 到达站
            _start_date = lis[13][:4] + "-" + lis[13][4:6] + "-" + lis[13][6:8]
            start_time = datetime.fromisoformat(_start_date + " " + lis[8])  # 出发时刻 2023-01-04 09:20
            total_time = lis[10]  # 乘车用时 03:44
            _hours, _minutes = total_time.split(":")
            _hours = _hours.removeprefix("0")
            _minutes = _minutes.removeprefix("0")
            end_time = start_time + timedelta(hours=_hours, minutes=_minutes)  # 到达时刻 2023-01-04 13:50
            can_buy = lis[11] == "Y"  # 能否购买  Y-可，N-不可，IS_TIME_NOT_BUY-调整/停运/暂停发售

    return response


if __name__ == '__main__':
    query_ticket()

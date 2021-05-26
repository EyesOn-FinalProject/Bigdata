import paho.mqtt.client as mqtt
import requests, xmltodict, json
import pandas as pd
import paho.mqtt.publish as publish
import threading
import time

"""
on_connect는 subscriber가 브로커에 연결하면서 호출할 함수
rc가 0이면 정상접속이 됐다는 의미
경로 설정 체크하고, 실행하기!
"""

# 전역변수
key = 'AT98N5LWRAir0I67tVgrf6Vfnio9LCMcwusSbOjmdkEpSOGyobdyAq9cb41G6O4pgTp6Jcmpv8e87bplMNY7tQ%3D%3D'
radius = 100  # 범위 (넓히면 여러 정류장 인식 됨.)
data1 = pd.read_csv('C:\\hju\\PYTHONexam\\data\\busnumber_to_busRouteid.csv') # 경로 설정

# 전역변수로 NULL값
target_stId = None
target_stationName = None
target_arsId = None
target_msgStation = None
target_busRouteId = None
target_ord = None
arrival = None
arrival2 = None
busLicenseNum = None
nextstation = None
finalArrival = None
msgFinal = None

# 빅데이터 함수
#  함수 생성 ===================================================================================================
def position(x, y, r):
    url = f'http://ws.bus.go.kr/api/rest/stationinfo/getStationByPos?ServiceKey={key}&tmX={x}&tmY={y}&radius={r}'  # 서울특별시_정류소정보조회 서비스 中 7_getStaionsByPosList
    content = requests.get(url).content
    dict = xmltodict.parse(content)

    # 첫번째 정류장이라 설정
    target_stId = int(dict['ServiceResult']['msgBody']['itemList'][0]['stationId'])
    target_stationName = str(dict['ServiceResult']['msgBody']['itemList'][0]['stationNm'])
    target_arsId = str(dict['ServiceResult']['msgBody']['itemList'][0]['arsId'])
    msgStation = "현재 인식된 정류장은 " + target_stationName + " 입니다."

    return (target_stId, target_stationName, target_arsId, msgStation)

def ordSearch(target_bus, target_arsId):
    try:
        target_busRouteId = data1[data1['busNumber'] == target_bus].iloc[0]['busRouteId']
        url = f'http://ws.bus.go.kr/api/rest/busRouteInfo/getStaionByRoute?ServiceKey={key}&busRouteId={target_busRouteId}'  # 서울특별시_노선정보조회 서비스 中 1_getStaionsByRouteList
        content = requests.get(url).content
        dict = xmltodict.parse(content)
        # target_arsId = arsId 넘버가 일치하는 버스의 seq(=ord) 구하기
        alist = []
        for i in range(0, len(dict['ServiceResult']['msgBody']['itemList'])):
            alist.append(dict['ServiceResult']['msgBody']['itemList'][i]['arsId'])
        # 인덱스 값이 곧 seq 값
        target_ord = alist.index(target_arsId) + 1
        return (target_busRouteId, target_ord)

    except:
        occurError = "error"
        errorMsg = "해당 버스번호가 존재하지 않습니다."

        return (occurError, errorMsg)
# 에러날 수 있는 요소: 1) 아예 버스 번호가 없는 경우, 2) 해당 정류소에 없는 버스 번호.

def arriveMessage(target_stId, target_busRouteId, target_ord):
    url = f'http://ws.bus.go.kr/api/rest/arrive/getArrInfoByRoute?ServiceKey=' \
          f'{key}&stId={target_stId}&busRouteId={target_busRouteId}&ord={target_ord}'  # 서울특별시_버스도착정보조회 서비스 中 2_getArrInfoByRouteList
    content = requests.get(url).content
    dict = xmltodict.parse(content)

    arrival = dict['ServiceResult']['msgBody']['itemList']['arrmsg1']
    arrival2 = dict['ServiceResult']['msgBody']['itemList']['arrmsg2']
    busLicenseNum = dict['ServiceResult']['msgBody']['itemList']['plainNo1']
    nextstation = dict['ServiceResult']['msgBody']['itemList']['stationNm1']

    return (arrival, arrival2, busLicenseNum, nextstation)


def noticeOneMinute(arrival):
    freeTime = 90  # 스마트 글래스 켜지기 시작하는 시간 (협의하여 결정, 실제 코드가 돌아가고 사용자에게 전달될때까지 시스템에서 소요되는 시간이 어느정도인지 고려해야 할듯)
    indexMinute = arrival.find('분')
    indexSecond = arrival.find('초')
    # find 이용 시, 문자열이 없으면 -1 리턴되는것을 이용
    if indexMinute == -1:
        k = 0
    elif indexSecond == -1:
        k = int(arrival[0:indexMinute]) * 60 - freeTime
    else:
        k = int(arrival[0:indexMinute]) * 60 + int(arrival[indexMinute + 1:indexSecond]) - freeTime

    print("sleep 전")
    time.sleep(k)
    print("sleep 후")
    finalResult = arriveMessage(target_stId, target_busRouteId, target_ord)

    global finalArrival, msgFinal

    if finalResult[0] == "곧 도착":
        global finalArrival, msgFinal
        finalArrival = "잠시 후"
        msgFinal = "버스가 " + str(finalArrival) + " 도착합니다. 탑승을 준비해주세요. "
    else:
        global finalArrival, msgFinal
        finalArrival = finalResult[0]
        msgFinal = "버스가 " + str(finalArrival) + " 도착합니다. 탑승을 준비해주세요. "

    #함수 내에서 퍼블리쉬 할 수 있는지 확인하여 추가하기
    return (finalArrival, msgFinal)

def noticeOneMinute_thread():
    thread=threading.Thread(target=noticeOneMinute, args=(arrival,))
    thread.daemon = True
    thread.start()

def on_connect(client, userdata, flags, rc):
    print("connect.." + str(rc))
    if rc == 0:
        client.subscribe("eyeson/#")
    else:
        print("연결실패")


# 메시지가 도착됐을때 처리할 일들 - 여러가지 장비 제어하기, Mongodb에 저장
def on_message(client, userdata, msg):
    myval = msg.payload.decode("utf-8")
    myval = myval.replace(" ", "")
    myval = myval.split("/")
    print(myval)
    if myval[0] == "riding":
        uuid = myval[1]
        busNum = myval[2]
        latitude = myval[3]  # 위도
        longitude = myval[4]  # 경도

        station = position(longitude, latitude, radius)  # 튜플

        target_stId = station[0]  # 밑 함수에서 쓰임.
        target_stationName = station[1]
        target_arsId = station[2]
        target_msgStation = station[3]
        print(target_stId)  # 정류장 ID
        print(target_stationName)  # 정류장 이름
        print(target_arsId)  # 정류장 고유번호
        print(target_msgStation)  # 사용자에게 주는 메시지

        # ===================================================================================================

        target_bus = busNum  # busNum, str 형태로 해야됨. -> 엑셀이 str 형태

        result_ordSearch = ordSearch(target_bus, target_arsId)
        target_busRouteId = result_ordSearch[0]
        target_ord = result_ordSearch[1]
        print(target_busRouteId)
        print(target_ord)

        # 에러 시 멈추고, 사용자에게 전해주는 코드 작성하기.
        if target_busRouteId == "error":
            aaa = 1
            busFindStatus = "bigData/error/"
            publish.single("eyeson/busTime", busFindStatus + uuid, hostname="15.164.46.54")  # 데이터 전송
        else:
            result_arriveMessage = arriveMessage(target_stId, target_busRouteId, target_ord)
            arrival = result_arriveMessage[0]
            arrival2 = result_arriveMessage[1]
            busLicenseNum = result_arriveMessage[2]
            nextstation = result_arriveMessage[3]
            busFindStatus = "bigData/ok/"

            print(arrival)  # 첫 번째 버스 도착 예정 시간
            print(arrival2)  # 두 번째 버스 도착 예정 시간
            print(busLicenseNum)  # 버스 차량 번호
            print(nextstation)  # 다음 정류장
            publish.single("eyeson/busTime", busFindStatus + uuid + "/" + busNum + "/" + arrival,
                           hostname="15.164.46.54")  # 데이터 전송
            time.sleep(2)
            noticeOneMinute_thread()
            # publish.single("eyeson/busTime", "bigData/ok/" + uuid + "/" + msgFinal,
            #                hostname="15.164.46.54")  # 데이터 전송
            # print(finalArrival)
            # print(msgFinal)


mqttClient = mqtt.Client()  # 클라이언트 객체 생성
# 브로커에 연결이되면 내가 정의해놓은 on_connect함수가 실행되도록 등록
mqttClient.on_connect = on_connect

# 브로커에서 메시지가 전달되면 내가 등록해 놓은 on_message함수가 실행
mqttClient.on_message = on_message

# 브로커에 연결하기
mqttClient.connect("15.164.46.54", 1883, 60)

# 토픽이 전달될때까지 수신대기
mqttClient.loop_forever()

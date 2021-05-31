import paho.mqtt.client as mqtt
import requests, xmltodict, json
import pandas as pd
import paho.mqtt.publish as publish
import threading
import time
import re
from urllib.parse import urlparse

"""
on_connect는 subscriber가 브로커에 연결하면서 호출할 함수
rc가 0이면 정상접속이 됐다는 의미
경로 설정 체크하고, 실행하기!
"""

# 전역변수
key = 'AT98N5LWRAir0I67tVgrf6Vfnio9LCMcwusSbOjmdkEpSOGyobdyAq9cb41G6O4pgTp6Jcmpv8e87bplMNY7tQ%3D%3D'
radius = 100  # 범위 (넓히면 여러 정류장 인식 됨.)
data1 = pd.read_csv('C:\\hju\\PYTHONexam\\data\\busnumber_to_busRouteid.csv') # 경로 설정

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
    target_msgStation = "현재 인식된 정류장은 " + target_stationName + " 입니다."

    return (target_stId, target_stationName, target_arsId, target_msgStation)

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

def arriveMessage(target_stId, target_busRouteId, target_ord):
    url = f'http://ws.bus.go.kr/api/rest/arrive/getArrInfoByRoute?ServiceKey=' \
          f'{key}&stId={target_stId}&busRouteId={target_busRouteId}&ord={target_ord}'  # 서울특별시_버스도착정보조회 서비스 中 2_getArrInfoByRouteList
    content = requests.get(url).content
    dict = xmltodict.parse(content)

    arrival = dict['ServiceResult']['msgBody']['itemList']['arrmsg1']
    arrival2 = dict['ServiceResult']['msgBody']['itemList']['arrmsg2']
    busLicenseNum = dict['ServiceResult']['msgBody']['itemList']['plainNo1']
    busLicenseNum = busLicenseNum[-4:]

    if arrival == "곧 도착":
        msgArrival = "전 정류장에서 출발하여 1분 이내 도착합니다."
    else:
        index_minute = arrival.find('분')
        msgArrival = "약 " + arrival[0:index_minute+1] + " 후 도착합니다. 승차 직전 다시 알림을 주겠습니다."

    return (arrival, arrival2, busLicenseNum, msgArrival)

def noticeOneMinute(arrival, uuid, target_stId, target_busRouteId, target_ord):
    freeTime = 60  # 여유시간
    indexMinute = arrival.find('분')
    indexSecond = arrival.find('초')
    # find 이용 시, 문자열이 없으면 -1 리턴되는것을 이용
    if indexMinute == -1:
        k = 0
    elif indexSecond == -1:
        k = int(arrival[0:indexMinute]) * 60 - freeTime
    else:
        k = int(arrival[0:indexMinute]) * 60 + int(arrival[indexMinute + 1:indexSecond]) - freeTime

    waiting_stId = target_stId
    waiting_busRouteId = target_busRouteId
    waiting_ord = target_ord
    print("sleep 전")
    print(arrival, "인데", k, "초 기다려야 함")
    time.sleep(k)
    print("sleep 후")
    finalResult = arriveMessage(waiting_stId, waiting_busRouteId, waiting_ord)
    ### global finalArrival, msgFinal ###
    if finalResult[0] == "곧 도착":
        finalArrival = "잠시 후"
        time.sleep(3) # 음성인식 안겹치게 3초 추가
        msgFinal = "버스가 " + str(finalArrival) + " 도착합니다."
    else:
        finalArrival = finalResult[0]
        msgFinal = "버스가 " + str(finalArrival) + " 도착합니다."

    print("직전에 다시 예상한 도착시간:", finalArrival)
    print("직전 사용자 알림:", msgFinal)

    publish.single("eyeson/" + uuid, "bigData/last/" + msgFinal,
                   hostname="15.164.46.54")  # 데이터 전송

    return (finalArrival, msgFinal)

def noticeOneMinute_thread(arrival, uuid,  target_stId, target_busRouteId, target_ord):
    thread=threading.Thread(target=noticeOneMinute, args=(arrival, uuid,  target_stId, target_busRouteId, target_ord))
    thread.daemon = True
    thread.start()

# 목적지명 기능 관련 함수

def allBusnum(target_arsId):
    busList = []
    url = f'http://ws.bus.go.kr/api/rest/stationinfo/getStationByUid?ServiceKey={key}&arsId={target_arsId}'
    content = requests.get(url).content
    dict = xmltodict.parse(content)

    for i in range(0, len(dict['ServiceResult']['msgBody']['itemList'])):
        busList.append(dict['ServiceResult']['msgBody']['itemList'][i]['busRouteId'])

    return busList # 특정 정류장에 오는 모든 버스

def theBusnum(arrivalStation, busList):
    thebuslist = []

    for i in range(0, len(busList)):
        url = f'http://ws.bus.go.kr/api/rest/busRouteInfo/getStaionByRoute?ServiceKey={key}&busRouteId={busList[i]}'
        content = requests.get(url).content
        dict = xmltodict.parse(content)

        buslinelist = []  # 특정 버스의 노선 목록
        for i in range(0, len(dict['ServiceResult']['msgBody']['itemList'])):
            buslinelist.append(dict['ServiceResult']['msgBody']['itemList'][i]['stationNm'])

        if arrivalStation in buslinelist:
            thebuslist.append(dict['ServiceResult']['msgBody']['itemList'][i]['busRouteId'])

    return thebuslist  # arrivalStation 경유하는 버스 ID

# 비정상 상황에서도 오류가 나지않고, 빈 리스트로 리턴됨 -> 후 에러처리에 사용됨.
def searchLicenseNum(arrivalStation, busList):
    busplain = []

    for i in range(0, len(busList)):
        url = f'http://ws.bus.go.kr/api/rest/arrive/getArrInfoByRouteAll?ServiceKey={key}&busRouteId={busList[i]}'
        content = requests.get(url).content
        dict = xmltodict.parse(content)

        buslinelists = []  # 특정 버스의 노선 목록
        for i in range(0, len(dict['ServiceResult']['msgBody']['itemList'])):
            buslinelists.append(dict['ServiceResult']['msgBody']['itemList'][i]['stNm'])

        if arrivalStation in buslinelists:
            busplain.append(dict['ServiceResult']['msgBody']['itemList'][i]['plainNo1'])

    return busplain


def waiting(target_arsId, thebuslist):
    url = f'http://ws.bus.go.kr/api/rest/stationinfo/getStationByUid?ServiceKey={key}&arsId={target_arsId}'
    content = requests.get(url).content
    dict = xmltodict.parse(content)

    waitingBusnum = []
    waitingTime = []
    for i in range(0, len(dict['ServiceResult']['msgBody']['itemList'])):
        if dict['ServiceResult']['msgBody']['itemList'][i]['busRouteId'] in thebuslist:
            x = dict['ServiceResult']['msgBody']['itemList'][i]['rtNm']
            y = dict['ServiceResult']['msgBody']['itemList'][i]['arrmsg1']
            waitingBusnum.append(x)
            waitingTime.append(y)
    return(waitingBusnum, waitingTime) # 버스 번호, 남은 시간

def waitdeep(a):
    x = []
    for i in a:
        if i == '곧 도착':
            i = 0
            x.append(i)
        elif i == '운행종료':
            i = 9999
            x.append(i)
        else:
            i = i.split('[')[0]
            index_first = i.find('분')
            index_two = i.find('초')
            i_essence = i[0:index_first]
            if index_two == -1:
                i_decimal = 0
            else:
                i_decimal = i[index_first+1:index_two]
            i = float(i_essence) * 1 + float(i_decimal) * 0.01
            x.append(float(i))
    return x

def on_connect(client, userdata, flags, rc):
    print("connect.." + str(rc))
    if rc == 0:
        client.subscribe("eyeson/#")
    else:
        print("연결실패")


# 메시지가 도착됐을때 처리할 일들 - 여러가지 장비 제어하기, Mongodb에 저장
def on_message(client, userdata, msg):
    try:
        myval = msg.payload.decode("utf-8")
        myval = myval.replace(" ", "")
        myval = myval.split("/")
        mytopic = msg.topic.split("/")
        print(myval)
        uuid = mytopic[1]
        print(uuid)
        msg = None
        # try except에서 1보다 작은게 들어올 때 오류나는 문제 해결.
        if myval[0] == "android":
            if myval[1] == "busTime":
                target_stId = int(myval[2])
                target_busRouteId = int(myval[3])
                target_ord = int(myval[4])
                resultBusTime = arriveMessage(target_stId, target_busRouteId, target_ord)
                msgArrival = resultBusTime[3]
                indexsin = msgArrival.find("승")
                msgArrival = msgArrival[0:indexsin]
                print(msgArrival)
                publish.single("eyeson/" + uuid, "bigData/busTime/" + msgArrival, hostname="15.164.46.54")

            if myval[1] == "busStation":
                print("들어옴")
                latitude = myval[2]  # 위도
                longitude = myval[3]  # 경도
                station = position(longitude, latitude, radius)  # 튜플
                print("돌아감")
                target_stationName = station[1]
                print(target_stationName)
                print(uuid)
                publish.single("eyeson/" +uuid, "bigData/busStation/" + target_stationName, hostname="15.164.46.54")


            if myval[1] == "riding":
                busNum = myval[2] ## 버스번호 or 목적지명
                latitude = myval[3]  # 위도
                longitude = myval[4]  # 경도

                station = position(longitude, latitude, radius)  # 튜플

                target_stId = station[0]  # 밑 함수에서 쓰임.
                target_stationName = station[1]
                target_arsId = station[2]
                target_msgStation = station[3]
                print("정류장 ID:", target_stId)  # 정류장 ID
                print("정류장 이름:", target_stationName)  # 정류장 이름
                print("정류장 고유번호:",target_arsId)  # 정류장 고유번호
                print("사용자 메시지:", target_msgStation)  # 사용자에게 주는 메시지

                # 여기까지는 두 가지 모두 똑같음
                # ===================================================================================================
                target_bus = busNum  # str, 버스번호 or 목적지명 들어옴

                result_ordSearch = ordSearch(target_bus, target_arsId)
                target_busRouteId = result_ordSearch[0]
                target_ord = result_ordSearch[1]
                print("버스 고유번호:",target_busRouteId)
                print("해당 정류장 순번:",target_ord)

                # 에러 시 멈추고, 사용자에게 전해주는 코드 작성하기.
                if target_busRouteId == "error":
                    print("버스번호가 아님. 목적지명이거나 정류장에 없는 버스번호임")

                    busList = allBusnum(target_arsId)
                    print("출발 정류장에 들어오는 모든 버스: ", busList)

                    arrivalStation = target_bus # ex) 당산역 , or 오류나는 데이터. (잘못된 정류장 명 또는 버스 번호)
                    thebuslist = theBusnum(arrivalStation, busList)
                    print("도착 정류장에 해당하는 모든 버스: ", thebuslist)

                    if thebuslist == []:
                        publish.single("eyeson/" + uuid,
                                       "bigData/error/",
                                       hostname="15.164.46.54")  # 데이터 전송

                    else:
                        print("오류없이 잘 빠져나옴. 마지막 else단계")
                        waitingBusnum, waitingTime = waiting(target_arsId, thebuslist)
                        # print("후보 버스 리스트: ", waitingBusnum)
                        # print("후보 버스들의 남은 시간: ", waitingTime)

                        x = waitdeep(waitingTime)
                        destinationBus = waitingBusnum[(x.index(min(x)))]
                        destinationBusArrival = waitingTime[(x.index(min(x)))]
                        print("가장 빨리오는 버스 (최종):", destinationBus)
                        print("최종 버스 도착시간:", destinationBusArrival)

                        target_bus = destinationBus  # str, 버스번호 or 목적지명 들어옴
                        print("가장 빠른 버스 찾고 타켓버스로 지정", target_bus)

                        result_ordSearch = ordSearch(target_bus, target_arsId)
                        target_busRouteId = result_ordSearch[0]
                        target_ord = result_ordSearch[1]
                        # print("버스 고유번호:", target_busRouteId)
                        # print("해당 정류장 순번:", target_ord)

                        result_arriveMessage = arriveMessage(target_stId, target_busRouteId, target_ord)
                        arrival = result_arriveMessage[0]
                        arrival2 = result_arriveMessage[1]
                        busLicenseNum = result_arriveMessage[2]
                        msgArrival = result_arriveMessage[3]
                        busFindStatus = "bigData/ok/"

                        print("도착예정시간:", arrival)  # 첫 번째 버스 도착 예정 시간
                        print("두번째 버스 도착 예정 시간:", arrival2)  # 두 번째 버스 도착 예정 시간
                        print("차량 번호:", busLicenseNum)  # 버스 차량 번호
                        print("사용자 메시지:", msgArrival)
                        print("버스넘버 확인", destinationBus)

                        publish.single("eyeson/" + uuid,
                                       busFindStatus + destinationBus + "/" + msgArrival + "/" + busLicenseNum + "/" + target_stationName + "/" + str(target_stId)  + "/" + str(target_busRouteId) + "/" + str(target_ord),
                                       hostname="15.164.46.54")  # 데이터 전송
                        time.sleep(1)
                        noticeOneMinute_thread(arrival, uuid, target_stId, target_busRouteId, target_ord)


                else:
                    result_arriveMessage = arriveMessage(target_stId, target_busRouteId, target_ord)
                    # global 지움
                    arrival = result_arriveMessage[0]
                    arrival2 = result_arriveMessage[1]
                    busLicenseNum = result_arriveMessage[2]
                    msgArrival = result_arriveMessage[3]
                    busFindStatus = "bigData/ok/"

                    print("도착예정시간:",arrival)  # 첫 번째 버스 도착 예정 시간
                    print("두번째 버스 도착 예정 시간:",arrival2)  # 두 번째 버스 도착 예정 시간
                    print("차량 번호:",busLicenseNum)  # 버스 차량 번호
                    print("사용자 메시지:", msgArrival)

                    publish.single("eyeson/" + uuid, busFindStatus + busNum + "/" + msgArrival + "/" + busLicenseNum + "/" + target_stationName + "/" + str(target_stId)  + "/" + str(target_busRouteId) + "/" + str(target_ord), hostname="15.164.46.54")  # 데이터 전송
                    time.sleep(1)
                    noticeOneMinute_thread(arrival, uuid, target_stId, target_busRouteId, target_ord)
    except:
        pass


mqttClient = mqtt.Client()  # 클라이언트 객체 생성
# 브로커에 연결이되면 내가 정의해놓은 on_connect함수가 실행되도록 등록
mqttClient.on_connect = on_connect

# 브로커에서 메시지가 전달되면 내가 등록해 놓은 on_message함수가 실행
mqttClient.on_message = on_message

# 브로커에 연결하기
mqttClient.connect("15.164.46.54", 1883, 60)

# 토픽이 전달될때까지 수신대기
mqttClient.loop_forever()

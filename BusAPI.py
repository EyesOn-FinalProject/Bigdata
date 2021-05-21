# 라이브러리
import requests, xmltodict, json
import pandas as pd
import time

# 함수 생성 ===================================================================================================
def position(x, y, r):
    url = f'http://ws.bus.go.kr/api/rest/stationinfo/getStationByPos?ServiceKey={key}&tmX={x}&tmY={y}&radius={r}' # 서울특별시_정류소정보조회 서비스 中 7_getStaionsByPosList
    content = requests.get(url).content
    dict = xmltodict.parse(content)

    # 첫번째 정류장이라 설정
    target_stId = int(dict['ServiceResult']['msgBody']['itemList'][0]['stationId'])
    target_stationName = str(dict['ServiceResult']['msgBody']['itemList'][0]['stationNm'])
    target_arsId = str(dict['ServiceResult']['msgBody']['itemList'][0]['arsId'])
    msgStation = "현재 인식된 정류장은 " + target_stationName + " 입니다."

    return (target_stId, target_stationName, target_arsId, msgStation)
# 함수 호출 시 에러날 일은 없음.

def ordSearch(target_bus, target_arsId):
    try:
        target_busRouteId = data1[data1['busNumber'] == target_bus].iloc[0]['busRouteId']
        url = f'http://ws.bus.go.kr/api/rest/busRouteInfo/getStaionByRoute?ServiceKey={key}&busRouteId={target_busRouteId}' # 서울특별시_노선정보조회 서비스 中 1_getStaionsByRouteList
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
          f'{key}&stId={target_stId}&busRouteId={target_busRouteId}&ord={target_ord}' # 서울특별시_버스도착정보조회 서비스 中 2_getArrInfoByRouteList
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

    time.sleep(k)
    finalResult = arriveMessage(target_stId, target_busRouteId, target_ord)
    finalArrival = finalResult[0]
    msgFinal = "버스가 " + str(finalArrival) + " 도착합니다. 탑승을 준비해주세요. "

    return (finalArrival, msgFinal)
# ===================================================================================================
# MQTT를 통해 id, latitude, longitude, busNum 받음

# 공공 API 활용 KEY
key = 'kNSQvU5WeosgTXwCx1mTthdz93%2BlLXHKA7ZtzbuNArBuUVVP4akW5xsfp6R5JYuMH106DwcuJRTqXJHI4q%2BNjA%3D%3D'

# 사용자의 위치를 받아서 tmX, tmY 변수에 지정 우선 임시 지정)
tmX = 127.0557255 # 경도(double) = longitude 강남 07/37.5095603/127.0557255 (126.9233021, 37.55639751)
tmY = 37.5095603 # 위도(double) = latitude
radius = 100 # 범위 (넓히면 여러 정류장 인식 됨.)

station = position(tmX,tmY,radius) # 튜플

target_stId = station[0] # 밑 함수에서 쓰임.
target_stationName = station[1]
target_arsId = station[2]
target_msgStation = station[3]
print(target_stId) # 정류장 ID
print(target_stationName) # 정류장 이름
print(target_arsId) #정류장 고유번호
print(target_msgStation) # 사용자에게 주는 메시지

# ===================================================================================================
data1 = pd.read_csv('data/busnumber_to_busRouteid.csv')

# 음성인식을 통해 사용자가 5714번 탄다고 가정했음.
target_bus = '2415' # busNum, str 형태로 해야됨. -> 엑셀이 str 형태

result_ordSearch = ordSearch(target_bus, target_arsId)
target_busRouteId = result_ordSearch[0]
target_ord = result_ordSearch[1]
print(target_busRouteId)
print(target_ord)

# 에러 시 멈추고, 사용자에게 전해주는 코드 작성하기.
if target_busRouteId == "error":
    aaa = 1 # 다시 전송하는 코드 넣어야 할듯...?

result_arriveMessage = arriveMessage(target_stId, target_busRouteId, target_ord)
arrival = result_arriveMessage[0]
arrival2 = result_arriveMessage[1]
busLicenseNum = result_arriveMessage[2]
nextstation = result_arriveMessage[3]

print(arrival) # 첫 번째 버스 도착 예정 시간
print(arrival2) # 두 번째 버스 도착 예정 시간
print(busLicenseNum) # 버스 차량 번호
print(nextstation) # 다음 정류장

result_noticeOneMinute = noticeOneMinute(arrival) # 이거 돌아갈 때, 1분 남을때까지 해당 파일 실행되지않고, timesleep함을 기억
finalArrival = result_noticeOneMinute[0]
msgFinal = result_noticeOneMinute[1]
print(finalArrival)
print(msgFinal)

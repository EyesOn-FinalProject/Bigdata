# 라이브러리
import requests, xmltodict, json
import pandas as pd

# 공공 API 활용 KEY
key = 'kNSQvU5WeosgTXwCx1mTthdz93%2BlLXHKA7ZtzbuNArBuUVVP4akW5xsfp6R5JYuMH106DwcuJRTqXJHI4q%2BNjA%3D%3D'

# ===================================================================================================
# 사용자의 위치를 받아서 tmX, tmY 변수에 지정 (우선 임시 지정)
tmX = 126.9233021
tmY = 37.55639751
radius = 100 # 범위 (넓히면 여러 정류장 인식 됨.)

def position(x, y, r) :
    url = f'http://ws.bus.go.kr/api/rest/stationinfo/getStationByPos?ServiceKey={key}&tmX={x}&tmY={y}&radius={r}'
    content = requests.get(url).content
    dict = xmltodict.parse(content)

    # 첫번째 정류장이라 설정 (음성으로 "현재 인식된 정류장은 A 정류장 입니다." 라고 전해주기)
    target_stId = int(dict['ServiceResult']['msgBody']['itemList'][0]['stationId'])
    target_stationName = str(dict['ServiceResult']['msgBody']['itemList'][0]['stationNm'])
    target_arsId = str(dict['ServiceResult']['msgBody']['itemList'][0]['arsId'])

    return (target_stId, target_stationName, target_arsId)

station = position(tmX, tmY, radius)
target_stId = station[0]
target_stationName = station[1]
target_arsId = station[2]

print(target_stId)
print(target_stationName)
print(target_arsId)

# ===================================================================================================
data1 = pd.read_excel('data/busnumber_to_busRouteid.xlsx')

# 음성인식을 통해 사용자가 5714번 탄다고 가정했음.
target_bus = '5714' # str 형태로 해야됨. -> 엑셀이 str 형태

def busnumber(target_bus) :
    target_busRouteId = data1[data1['busNumber'] == target_bus].iloc[0]['busRouteId']
    return(target_busRouteId)

target_busRouteId = busnumber(target_bus)

print(target_busRouteId)

# ===================================================================================================
# 서울특별시_노선정보조회 서비스 中 1_getStaionsByRouteList
url = f'http://ws.bus.go.kr/api/rest/busRouteInfo/getStaionByRoute?ServiceKey={key}&busRouteId={target_busRouteId}'
content = requests.get(url).content
dict = xmltodict.parse(content)

# target_arsId = arsId 넘버가 일치하는 버스의 seq(=ord) 구하기
alist = []
for i in range(0, len(dict['ServiceResult']['msgBody']['itemList'])):
    alist.append(dict['ServiceResult']['msgBody']['itemList'][i]['arsId'])

# 인덱스 값이 곧 seq 값
target_ord = alist.index(target_arsId) + 1
print(target_ord)

# ===================================================================================================
# 서울특별시_버스도착정보조회 서비스 中 2_getArrInfoByRouteList
url = f'http://ws.bus.go.kr/api/rest/arrive/getArrInfoByRoute?ServiceKey=' \
      f'{key}&stId={target_stId}&busRouteId={target_busRouteId}&ord={target_ord}'

content = requests.get(url).content
dict = xmltodict.parse(content)

arrival = json.dumps(dict['ServiceResult']['msgBody']['itemList']['arrmsg1'], ensure_ascii = False)
arrival2 = json.dumps(dict['ServiceResult']['msgBody']['itemList']['arrmsg2'], ensure_ascii = False)
busplainnum = json.dumps(dict['ServiceResult']['msgBody']['itemList']['plainNo1'], ensure_ascii = False)
nextstation = json.dumps(dict['ServiceResult']['msgBody']['itemList']['stationNm1'], ensure_ascii = False)

jsonarrival = json.loads(arrival)
jsonarrival2 = json.loads(arrival2)
jsonbusplainnum = json.loads(busplainnum)
jsonnextstation = json.loads(nextstation)

print(jsonarrival)
print(jsonarrival2)
print(jsonbusplainnum)
print(jsonnextstation)
import paho.mqtt.publish as publish

id = "jaeung"

# 1안 테스트
busNum = "160"
latitude = "37.541111"
longitude = "126.948099"

#
# # 2안 테스트
# busNum = "당산역"
# latitude = "37.5563975089"
# longitude = "126.9233020723"

publish.single("eyeson/1234", "android/" + "riding/"  + busNum + "/" + latitude+ "/" + longitude , hostname="15.164.46.54")


# 1) 버스 번호 시나리오 테스트 데이터
# 37.541111, 126.948099 -> 마포역 정류장 ,  버스번호: (260,160,7016 등)


# 2) 목적지 시나리오 테스트 데이터
# ("당산역",  "37.5563975089", "126.9233020726")


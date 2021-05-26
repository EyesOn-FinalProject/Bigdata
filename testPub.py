import paho.mqtt.publish as publish

id = "jaeung"
busNum = "160"
latitude = "37.541111"
longitude = "126.948099"

# 37.541111, 126.948099 -> 마포역 (260,160,7016 등)

publish.single("eyeson/busData", "riding/" + id + "/" + busNum + "/" + latitude+ "/" + longitude , hostname="15.164.46.54")


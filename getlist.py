import requests
import json

url = "https://wx.nhsa.gov.cn/nhsa/api/drug/getlist"

headers = {
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Origin": "https://wx.nhsa.gov.cn",
    "Pragma": "no-cache",
    "Referer": "https://wx.nhsa.gov.cn/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "clientId": "",
    "remoteIp": "",
    "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
    "x_access_wxLogon": "%2Fpages%2FNRDL%2Findex%2Findex",
    "x_access_wxtoken": "",
}

cookies = {
    "acw_tc": "276082b217812343270776676ee83ec2fc1d50a2ef73d78880b7eb32b02797",
}

data = {
    "name": "",
    "drugTypeId": "",
    "categoryId": "",
    "kind": "",
    "pageSize": 10000,
    "pageNum": 1,
    "id": "",
}

response = requests.post(url, headers=headers, cookies=cookies, json=data)

# 保存响应 JSON 到文件
with open("response.json", "w", encoding="utf-8") as f:
    json.dump(response.json(), f, ensure_ascii=False, indent=2)

print(f"Status: {response.status_code}")
print(f"Response saved to response.json")
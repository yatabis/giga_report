import json
import os
from pprint import pprint

from bottle import run, route, request
import requests
from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
import chromedriver_binary

CAT = os.environ.get('CHANNEL_ACCESS_TOKEN')
HEADER = {'Content-Type': 'application/json', 'Authorization': f"Bearer {CAT}"}


def reply_text(text, token):
    ep = "https://api.line.me/v2/bot/message/reply"
    body = {'replyToken': token, 'messages': [{'type': 'text', 'text': text}]}
    return requests.post(ep, data=json.dumps(body, ensure_ascii=False).encode('utf-8'), headers=HEADER)


def fetch_giga():
    # options = Options()
    # options.binary_location = '/app/.apt/usr/bin/google-chrome'
    # options.add_argument('--headless')
    # options.add_argument('--disable-gpu')
    # driver = webdriver.Chrome(chrome_options=options)
    options= webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)

    driver.get(os.environ.get('LOGIN_URL'))
    driver.find_element_by_name('telnum').send_keys(os.environ.get('TEL_NUM'))
    driver.find_element_by_name('password').send_keys(os.environ.get('PASSWORD'))
    driver.find_element_by_xpath("//input[@value='ログインする']").click()
    # print([cookie['name'] for cookie in driver.get_cookies()])
    driver.find_element_by_xpath("//*[@id='use-data']/div/div/div[1]/p/img").click()
    gb = driver.find_element_by_xpath(
        "//*[@id='contents-body']/form/div[3]/div/div/div[2]/table/tbody/tr[2]/th/div/div[2]/span").text

    driver.close()
    driver.quit()

    return gb


@route('/callback', method='POST')
def callback():
    for event in request.json.get('events'):
        pprint(event)
        reply_token = event.get('replyToken', None)
        if event['type'] == 'message':
            message = event['message']
            if not message['type'] == 'text':
                reply_text('テキストメッセージ以外には対応していないよ！', reply_token)
            elif not message['text'] == "データ":
                reply_text('「データ」と言うとデータ残量を返すよ！', reply_token)
            else:
                reply_text("今月のデータ残量が知りたいんだね？\nわかった、調べてくるよ！\nちょっと待っててね！", reply_token)
                giga = fetch_giga()
                result = reply_text(f"おまたせ！\n今月のデータ残量は {giga} GBだよ!", reply_token)
                pprint(result)


if __name__ == '__main__':
    print(fetch_giga())
else:
    run(host='0.0.0.0', port=int(os.environ.get('PORT', 443)))

import json
import os
from pprint import pprint
import time

from bottle import run, route, request
import requests
from selenium import webdriver
import chromedriver_binary

CAT = os.environ.get('CHANNEL_ACCESS_TOKEN')
MASTER = os.environ.get('MASTER')
USER = os.environ.get('USER')
HEADER = {'Content-Type': 'application/json', 'Authorization': f"Bearer {CAT}"}


def reply_text(text, token):
    ep = "https://api.line.me/v2/bot/message/reply"
    body = {'replyToken': token, 'messages': [{'type': 'text', 'text': text}]}
    requests.post(ep, data=json.dumps(body, ensure_ascii=False).encode('utf-8'), headers=HEADER)


def push_text(text, to):
    ep = "https://api.line.me/v2/bot/message/push"
    body = {'to': to, 'messages': [{'type': 'text', 'text': text}]}
    return requests.post(ep, data=json.dumps(body, ensure_ascii=False).encode('utf-8'), headers=HEADER)


def fetch_giga():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)

    driver.get(os.environ.get('LOGIN_URL'))
    print(driver.current_url)
    driver.find_element_by_name('telnum').send_keys(os.environ.get('TEL_NUM'))
    driver.find_element_by_name('password').send_keys(os.environ.get('PASSWORD'))
    driver.find_element_by_xpath("//input[@value='ログインする']").click()
    print(driver.current_url)
    driver.find_element_by_xpath("//*[@id='use-data']/div/div/div[1]/p/img").click()
    print(driver.current_url)
    gb = driver.find_element_by_xpath(
        "//*[@id='contents-body']/form/div[3]/div/div/div[2]/table/tbody/tr[2]/th/div/div[2]/span").text
    print(gb)
    driver.find_element_by_id('js-toggle-menu').click()
    driver.find_element_by_xpath('//*[@id="js-toggle-menu-contents"]/p[2]/a').click()
    time.sleep(3)
    print(driver.current_url)

    driver.close()
    driver.quit()

    return gb


def one_off_report(token):
    debug = os.environ.get('DEBUG', False)

    reply_text("今月のデータ残量が知りたいんだね？\nわかった、調べてくるよ！\nちょっと待っててね！", token)
    if debug:
        push_text("データ残量の確認がリクエストされました。", MASTER)

    giga = fetch_giga()

    push_text(f"おまたせ！\n今月のデータ残量は {giga} GBだよ!", USER)
    if debug:
        push_text(f"おまたせ！\n今月のデータ残量は {giga} GBだよ!", MASTER)


@route('report', method='POST')
def timed_report():
    debug = os.environ.get('DEBUG', False)

    giga = fetch_giga()
    push_text(f"今月のデータ残量はあと {giga} GBだよ！", USER)
    if debug:
        push_text(f"今月のデータ残量はあと {giga} GBだよ！", MASTER)


@route('/callback', method='POST')
def callback():
    for event in request.json.get('events'):
        pprint(event)
        reply_token = event.get('replyToken', None)
        source = event['source']['userId']
        if event['type'] == 'message':
            message = event['message']
            if not source == USER and not source == MASTER:
                reply_text('ごめんなさい！個別のメッセージ返信にはまだ対応していないよ！', reply_token)
            elif not message['type'] == 'text':
                reply_text('テキストメッセージ以外には対応していないよ！', reply_token)
            elif not message['text'] == "データ":
                reply_text('「データ」と言うとデータ残量を返すよ！', reply_token)
            else:
                timed_report(reply_token)


if __name__ == '__main__':
    run(host='0.0.0.0', port=int(os.environ.get('PORT', 443)))

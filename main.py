from datetime import datetime
import json
import os
from pprint import pprint
import time

from bottle import run, route, request, HTTPResponse
import chromedriver_binary
import psycopg2
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException

CAT = os.environ.get('CHANNEL_ACCESS_TOKEN')
MASTER = os.environ.get('MASTER')
USER = os.environ.get('USER')
API_KEY = os.environ.get('API_KEY')
APP_ID = os.environ.get('APP_ID')
HEADER = {'Content-Type': 'application/json', 'Authorization': f"Bearer {CAT}"}


def reply_text(text, token):
    ep = "https://api.line.me/v2/bot/message/reply"
    body = {'replyToken': token, 'messages': [{'type': 'text', 'text': text}]}
    requests.post(ep, data=json.dumps(body, ensure_ascii=False).encode('utf-8'), headers=HEADER)


def push_text(text, to):
    ep = "https://api.line.me/v2/bot/message/push"
    body = {'to': to, 'messages': [{'type': 'text', 'text': text}]}
    return requests.post(ep, data=json.dumps(body, ensure_ascii=False).encode('utf-8'), headers=HEADER)


def get_connection():
    dsn = os.environ.get('DATABASE_URL')
    return psycopg2.connect(dsn)


def fetch_giga():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    try:
        driver.get(os.environ.get('LOGIN_URL'))
        print(driver.current_url)
        driver.find_element_by_name('telnum').send_keys(os.environ.get('TEL_NUM'))
        driver.find_element_by_name('password').send_keys(os.environ.get('PASSWORD'))
        driver.find_element_by_xpath("//input[@value='ログインする']").click()
        print(driver.current_url)
        driver.find_element_by_xpath("//*[@id='use-data']/div/div/div[1]/p/img").click()
        print(driver.current_url)
        wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "span.remain.nums.fs-24")))
        gb = driver.find_element_by_css_selector("#use-data-table-1 > div.util-border-box.m-bottom-0 > table > tbody > tr:nth-child(1) > td > div > div.data-total-capacity > p > span").text
        print(driver.current_url)
        driver.execute_script("window.scrollTo({top: 1000, behavior: 'instant'});")
        driver.find_element_by_id('js-toggle-menu').click()
        logout = wait.until(ec.element_to_be_clickable((By.XPATH, '//*[@id="js-toggle-menu-contents"]/p[2]/a')))
        logout.click()
        time.sleep(2)
        print(driver.current_url)
        driver.close()
        driver.quit()
    except ElementClickInterceptedException as e:
        print("クリック関連のエラーが発生しました。")
        print(e)
        driver.close()
        driver.quit()
        return "err"
    except NoSuchElementException as e:
        print("要素が存在しないエラーが発生しました。")
        print(e)
        driver.close()
        driver.quit()
        return "err"

    return int(float(gb) * 100) / 100


def fetch_db(key):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('select value from logs where key = %s;', (key, ))
            (value, ) = cur.fetchone()
    return value


def save_db(key, value):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('update logs set value = %s where key = %s;', (value, key))


def get_name():
    ep = f"https://api.line.me/v2/bot/profile/{USER}"
    header = {"Authorization": f"Bearer {CAT}"}
    req = requests.get(ep, headers=header)
    print(req.json())
    return req.json()['displayName']


def one_off_report(token):
    debug = os.environ.get('DEBUG', False)

    reply_text("今月の総データ使用量が知りたいんだね？\nわかった、調べてくるよ！\nちょっと待っててね！\n\n※この処理は最大で3分程かかる事があります。", token)
    if debug:
        push_text("総データ使用量の確認がリクエストされました。", MASTER)

    giga = fetch_giga()
    push_text(f"おまたせ！\n今月の総データ使用量は {giga:.2f} GBだよ!", USER)
    if debug:
        push_text(f"今月の総データ使用量は {giga:.2f} GBでした。", MASTER)


def timed_report():
    debug = os.environ.get('DEBUG', False)

    giga = fetch_giga()
    if giga == "err":
        return
    latest = float(fetch_db('latest'))
    interval = int(fetch_db('interval'))
    # デバッグ用
    print(f"latest:  {int(latest * 1000 / interval)}")
    print(f"current: {int(giga * 1000 / interval)}")
    if int(giga * 1000 / interval) != int(latest * 1000 / interval):
        push_text(f"今月の総データ使用量が {giga:.2f} GBになったよ！", USER)
        if debug:
            push_text(f"今月の総データ使用量が {giga:.2f} GBになったよ！", MASTER)
        save_db('latest', giga)


@route('/callback', method='POST')
def callback():
    for event in request.json.get('events'):
        pprint(event)
        reply_token = event.get('replyToken', None)
        source = event['source']['userId']
        if event['type'] == 'message':
            message = event['message']
            if source in [USER, MASTER] and message['type'] == 'text' and message['text'] == "データ":
                one_off_report(reply_token)
            else:
                reply_text('ごめんなさい！個別のメッセージ返信にはまだ対応していないよ！', reply_token)
        elif event['type'] == 'postback':
            if event['postback']['data'] == 'action=data':
                one_off_report(reply_token)


if __name__ == '__main__':
    run(host='0.0.0.0', port=int(os.environ.get('PORT', 443)))

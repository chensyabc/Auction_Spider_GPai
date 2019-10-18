from bs4 import BeautifulSoup
from lxml import etree
import re
import urllib.request
import random
import MySQL
import ssl
import time, datetime
import DateTimeUtil
import UrlUtil
from threading import Thread
import threading


class AuctionSpiderGPai:
    circleList = ['1', '2', '4']

    def get_page_total(self, total_count, each_page_count):
        page_total = total_count // each_page_count
        if total_count % each_page_count != 0:
            page_total += 1
        return page_total

    def get_total_count(self, url):
        page = UrlUtil.get_html_with_proxy(url, False)
        total_counts = re.findall(re.compile(r'<label>(.*?)</label>'), page.decode('utf8'))
        return int(total_counts[0])

    def get_auction_json(self, url, court_id, category_id, status_id):
        auction_json = {}
        html = UrlUtil.get_html_with_proxy(url)
        et = etree.HTML(html)
        auction_model_div = et.xpath('//div[@class="d-m-tb"]/table[1]/tr[1]/td[1]/text()')
        auction_json['AuctionModel'] = ""
        if auction_model_div.__len__() != 0:
            auction_model = auction_model_div[0]
            len = auction_model.__len__()
            if len > 7:
                auction_json['AuctionModel'] = auction_model[7:]
            else:
                auction_json['AuctionModel'] = auction_model[5:]
        auction_json['SellingPeriod'] = ""
        auction_json['AuctionTimes'] = ""
        auctionTimes = et.xpath('//div[@class="d-m-tb"]/table[1]/tr[1]/td[2]/text()')
        if auctionTimes.__len__() != 0:
            auction_times = auctionTimes[0]
            if str(auction_json['AuctionModel'].encode('utf-8')) == '变卖':
                auction_json['SellingPeriod'] = auction_times[4:]
            else:
                auction_json['AuctionTimes'] = auction_times[5:]

        self.assign_auction_property_et(auction_json, 'AuctionType', et, '//div[@class="d-m-tb"]/table[1]/tr[1]/td[3]/text()', 5)

        onlineCycle = et.xpath('//div[@class="d-m-tb"]/table[1]/tr[2]/td[1]/text()')
        auction_json['OnlineCycle'] = ""
        if onlineCycle.__len__() != 0:
            online_cycle = onlineCycle[0]
            len = online_cycle.__len__()
            if len > 8:
                auction_json['OnlineCycle'] = online_cycle[6:]
            else:
                auction_json['OnlineCycle'] = online_cycle[4:]

        self.assign_auction_property_et(auction_json, 'DelayCycle', et, '//div[@class="d-m-tb"]/table[1]/tr[2]/td[2]/text()', 5)
        self.assign_auction_property(auction_json, 'FareIncrease', html, r'<span id="Price_Step">(.*?)</span>', True)
        self.assign_auction_property(auction_json, 'StartPrice', html, r'<span id="Price_Start">(.*?)</span>', True)

        auction_json['CashDeposit'] = ""
        auction_json['PaymentAdvance'] = ""
        if str(auction_json['AuctionModel'].encode('utf-8')) == '变卖':
            paymentAdvance = et.xpath('//div[@class="d-m-tb"]/table[1]/tr[3]/td[2]/text()')
            cashDeposit = et.xpath('//div[@class="d-m-tb"]/table[1]/tr[3]/td[3]/text()')
            if paymentAdvance.__len__() != 0:
                payment_advance = paymentAdvance[0]
                cash_deposit = cashDeposit[0]
                auction_json['cash_deposit'] = cash_deposit[4:].replace(",", "")
                auction_json['payment_advance'] = payment_advance[6:].replace(",", "")
        else:
            cashDeposit = et.xpath('//div[@class="d-m-tb"]/table[1]/tr[3]/td[2]/text()')
            if cashDeposit.__len__() != 0:
                cash_deposit = cashDeposit[0]
                auction_json['cash_deposit'] = cash_deposit[4:].replace(",", "")

        accessPrice = et.xpath('//div[@class="d-m-tb"]/table[1]/tr[4]/td[1]/text()')
        auction_json['AccessPrice'] = ""
        if accessPrice.__len__() != 0:
            access_price = accessPrice[0]
            auction_json['AccessPrice'] = access_price[4:].replace(",", "").replace("	", "")

        self.assign_auction_property(auction_json, 'Title', html, r'class="d-m-title"><b>(.*?)</b>', True)
        self.assign_auction_property_et(auction_json, 'Enrollment', et, '//div[@class="peoples-infos"]/span[1]/b[1]/text()')
        self.assign_auction_property_et(auction_json, 'SetReminders', et, '//div[@class="peoples-infos"]/span[2]/b[1]/text()')
        self.assign_auction_property_et(auction_json, 'Onlookers', et, '//div[@class="peoples-infos"]/span[3]/b[1]/text()')
        self.assign_auction_property(auction_json, 'CourtName', html, r"<td nowrap class='pr7'>(.*?)</td>", False, 5)
        self.assign_auction_property(auction_json, 'CorporateAgent', html, r"<td valign='top'>(.*?)</td>", False, 4)
        self.assign_auction_property(auction_json, 'Phone', html, r"<td colspan='2'>(.*?)</td>", False, 5)
        self.assign_auction_property(auction_json, 'BiddingRecord', html, r"id='html_Bid_Shu'>(.*?)</span>", True)
        self.assign_auction_property(auction_json, 'CurrentPrice', html, r"<b class='price-red'>(.*?)</b>", True)

        auction_json['Url'] = url
        auction_json['datetime'] = dataTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        auction_json['AuctionId'] = url[44:]
        auction_json['CourtId'] = court_id
        auction_json['CategoryId'] = category_id
        auction_json['StatusId'] = status_id
        return auction_json

    def assign_auction_property(self, auction_json, json_property, html, regex, is_int, start_index=0):
        regex_raw_result = re.findall(re.compile(regex, re.S), html.decode('utf-8'))
        auction_json[json_property] = ""
        if regex_raw_result.__len__() != 0:
            regex_result = regex_raw_result[0]
            if is_int and regex_result == "":
                auction_json[json_property] = '0'
            else:
                auction_json[json_property] = regex_result if start_index == 0 else regex_result[start_index:]

    def assign_auction_property_et(self, auction_json, json_property, et, et_str, start_index=0):
        et_raw_result = et.xpath(et_str)
        auction_json[json_property] = ""
        if et_raw_result.__len__() != 0:
            et_result = et_raw_result[0]
            auction_json[json_property] = et_result if start_index == 0 else et_result[start_index:]

    def spider_auction_and_insert(self, url, court_id, category_id, status_id, mysql_instance):
        item_html = UrlUtil.get_html_with_proxy(url)
        url_list = re.findall(re.compile(r'<a href="(\S*?)item2.do?(\S*?)"><img'), item_html.decode('utf8'))
        for urls in url_list:
            url = 'http://www.gpai.net/sf/item2.do' + urls[1]
            auction_json = self.get_auction_json(url, court_id, category_id, status_id)
            mysql_instance.upsert_auction(auction_json)

    def spider_auctions(self, court_list):
        print("Start Craw...")
        mysql_instance = MySQL.MySQL()
        categories = mysql_instance.get_categories()
        statuses = mysql_instance.get_statuses()
        for court in court_list:
            print('Thread Id: ' + str(threading.currentThread().ident), end='')
            print(court)
            if int(court[3]) == 0:
                print(court[2] + ": no auction")
                continue
            else:
                print(court[2] + ": has auctions, start to craw")
                for category in categories:
                    category_id = category[1]
                    for status in statuses:
                        if status[3] == 0:
                            continue
                        url_auctions_list = 'http://s.gpai.net/sf/court.do?id=' + str(court[1]) + '&at=' + category_id + '&restate=' + str(status[1])
                        total_count = self.get_total_count(url_auctions_list)
                        if total_count > 0:
                            # get page count
                            each_page_count = 20
                            page_total = total_count // each_page_count
                            if total_count % each_page_count != 0:
                                page_total += 1
                            page_total = self.get_page_total(total_count, 20)
                            # process url to get html and insert
                            print('total count: ' + str(total_count) + ' page count: ' + str(page_total))
                            for page_number in range(1, page_total + 1):
                                url = url_auctions_list + '&page=' + str(page_number)
                                self.spider_auction_and_insert(url, court[1], category_id, status[1], mysql_instance)
            print(court[2] + ": spider finish")
        print("Finish Craw...")


if __name__ == '__main__':
    auctionSpiderGPai = AuctionSpiderGPai()
    mysql = MySQL.MySQL()
    print(DateTimeUtil.get_current_time() + " start main progress")
    # prepare
    courts = mysql.get_courts()
    thread_count = 2
    each_count = len(courts) // thread_count
    # start multiple thread
    thread_array = {}
    start_time = time.time()
    for tid in range(thread_count):
        # t = Thread(target=auctionSpiderGPai.spider_auctions, args=(courts[tid:(tid+1)],))
        t = Thread(target=auctionSpiderGPai.spider_auctions, args=(courts[tid*each_count:(tid+1)*each_count],))
        t.start()
        thread_array[tid] = t
    for i in range(thread_count):
        thread_array[i].join()
    end_time = time.time()
    print("Total time: {}".format(end_time - start_time))
    print(DateTimeUtil.get_current_time() + " end main progress")

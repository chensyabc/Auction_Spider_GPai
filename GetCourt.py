import re
import urllib.request
import MySQL
import UrlUtil


class CourtUtil:
    def get_court_data(self):
        url = 'http://www.gpai.net/sf/courtList.do'
        html = UrlUtil.get_html(url)
        court_data_list = re.findall(re.compile(
            r'<a href="\S*?court.do\?id=(\d+)" target="_blank">(\S*?)</a>\s*<span class="iconfont-sf">\((\d+)', re.S),
                                     html.decode('utf-8'))
        return court_data_list

    def spider_and_upsert_court_info(self):
        print("start to get court list and insert into DB")
        court_info_list = self.get_court_data()
        for court_info in court_info_list:
            if court_info.__len__() > 1:
                court_id = court_info[0]
                court_name = court_info[1]
                auction_count = court_info[2]
                select_sql = 'select count(*) from Courts where CourtId=' + court_id
                insert_sql = 'insert into Courts (CourtId, CourtName, AuctionCount) values (' + court_id + ',"' + court_name + '",' + auction_count + ')'
                update_sql = 'update Courts set AuctionCount= ' + auction_count + ' where CourtId=' + court_id
                mysql.upsert(select_sql, insert_sql, update_sql)
        print("end to get court list and insert into DB")


if __name__ == '__main__':
    mysql = MySQL.MySQL()
    court_util = CourtUtil()
    court_util.spider_and_upsert_court_info()
    court_list = mysql.get_courts()
    print(court_list)

import feedparser, urllib.parse, csv, json, time, datetime
from bs4 import BeautifulSoup
from random import randint
from pytz import timezone

url = "http://news.google.com/news?hl=en-US&sort=date&gl=US&num=10&output=rss&q="

class ParseFeed():

    def __init__(self):
        pass

    def addRow(self, article):
        return '<tr>' \
        '    <td>{0}</td>' \
        '    <td>{1}</td>' \
        '    <td>{2}</td>' \
        '    <td><a target="_blank" href="{3}">Link</a></td>' \
        '  </tr>'.format(article['Date'], article['Title'], article['Description'], article['Url'])

    def addTable(self, target, articles):
        template = '<h3>{0}. <a target="_blank" href="{1}">{2}</a></h2>'\
        '<table>' \
        '  <tr>' \
        '    <th>Date</th>' \
        '    <th>Title</th>' \
        '    <th>Description</th>' \
        '    <th>Url</th>' \
        '  </tr>'.format(target['ID'], target['Ticker'], target['Name'])
        for a in articles:
            template += self.addRow(a)

        return template + '</table>'
        
    def clean(self, html):
        '''
        Get the text from html and do some cleaning
        '''
        soup = BeautifulSoup(html, features="html.parser")
        text = soup.get_text()
        text = text.replace('\xa0', ' ')
        return text

    def parse(self, url, query, contains_keyword, include_keyword_in_query, max_days_old=2, top=3):
        '''
        Parse the URL, and print all the details of the news 
        '''
        contains_keyword = contains_keyword.lower()
        articles = []
        if include_keyword_in_query:
            query = query + " " + contains_keyword
        feed_url = url + urllib.parse.quote(query)
        feeds = feedparser.parse(feed_url).entries
        n = 0
        for f in feeds:
            if n == top:
                break

            published = f.get("published", "")
            # format string from "Wed, 03 Jun 2020 06:30:00 GMT" to "03 Jun 2020 06:30:00"
            date_time_obj = datetime.datetime.strptime(published[5:len(published)-4], '%d %b %Y %H:%M:%S')
            delta = datetime.datetime.now()-date_time_obj
            # only care about the articles published in last 2 days
            if delta.days <= max_days_old:
                # check if contains the keyword
                title = f.get("title", "")
                description = self.clean(f.get("description", ""))
                if contains_keyword in title.lower() or contains_keyword in description.lower():
                    articles.append({
                        'Description': description,
                        'Date': date_time_obj.astimezone(timezone('US/Pacific')).strftime("%d %b %Y %H:%M:%S"),
                        'Title': title,
                        'Url': f.get("link", "")
                    })
            n += 1

        return articles
            






tableTemplateFilename = 'table_template.html'
outputHtmlFilename = 'data.html'
outputJsonFilename = 'data.json'
targetsFilename = 'targets.csv'
article_must_contain_keyword = "covid"
include_keyword_in_query = False # otherwise searched without the keyword but checked afterwards
article_max_days_old = 2
max_articles_per_target = 3

# load targets
targets = []

with open(targetsFilename, newline='') as csvfile:
    targetsreader = csv.reader(csvfile, delimiter=',', quotechar='"')
    for row in targetsreader:
        targets.append({"ID":row[0], "Name":row[1], "Ticker":"https://www.tradingview.com/symbols/NASDAQ-" + row[2]})

print("{0} Working on {1} targets with keyword '{2}'...".format(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), len(targets), article_must_contain_keyword))

# parse every target
feed = ParseFeed()

tables = ""

errors_until_shutdown = 7

blob = []

try:
    for t in targets:
        print("Parsing {0}. {1}".format(t['ID'], t['Name']))
        articles = []
        try:
            articles = feed.parse(url, t['Name'], article_must_contain_keyword, include_keyword_in_query, article_max_days_old, max_articles_per_target)
        except Exception as e:
            errors_until_shutdown -= 1
            print("Error parsing {0}: {1}", t['Name'], e)
            if errors_until_shutdown == 0:
                print("Too many errors!")
                break  

        time.sleep(randint(1,3))

        if len(articles) < 1:
            continue  

        tables += feed.addTable(t, articles)

        blob.append({
            "ID": t['ID'],
            "Name": t['Name'],
            "Articles": articles
        })

finally:
    # load the HTML tables template
    template = ""
    with open(tableTemplateFilename, 'r') as file:
        template = file.read()

    # save the results
    f = open(outputHtmlFilename, 'w', encoding='utf-8')
    data = template.replace('TABLES', tables)
    f.write(data)
    f.close()

    # save as json as well
    with open(outputJsonFilename, 'w', encoding='utf-8') as f:
        json.dump(blob, f, ensure_ascii=False, indent=4)

    print("{0} Result saved. $ open data.html".format(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")))




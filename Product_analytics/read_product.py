import pandas as pd
import matplotlib.pyplot as plt

product_month = pd.read_csv('./Product_analytics/data/20231116_상품_1달.csv')
product_week = pd.read_csv('./Product_analytics/data/20231116_상품_7일.csv')
product_lastweek = pd.read_csv('./Product_analytics/data/20231116_상품_지난7일.csv')

product_month.drop([0], inplace=True)
product_month.reset_index(drop=True, inplace=True)
product_week.drop([0], inplace=True)
product_week.reset_index(drop=True, inplace=True)
product_lastweek.drop([0], inplace=True)
product_lastweek.reset_index(drop=True, inplace=True)


product_month[product_month['판매수량'] == product_month['판매수량'].max()]
product_month[product_month['조회수'] == product_month['조회수'].max()]

product_month[product_month['판매수량'] == product_month['판매수량'].max()]
product_week[product_week['판매수량'] == product_week['판매수량'].max()]
product_lastweek[product_lastweek['판매수량'] == product_lastweek['판매수량'].max()]

sales_production = []
sales_production.append(product_week['판매건수'][product_week['판매수량'] == product_week['판매수량'].max()])


stat = ""

plt.figure(figsize=(12,8))
plt.hist()
import pandas as pd
import datetime
import numpy as np
import exception_list as ex

current_date = str(datetime.datetime.now().date()).replace('-', '')
excetption_list = ex.get_exception_list()

sale_61sec = pd.read_csv(f'./{current_date}_61sec.csv')
stock_data = pd.read_excel(f'./{current_date}_podong_automation.xlsx')

new_stock = stock_data.copy()
stock_61sec = np.zeros(shape=(len(new_stock),), dtype=int)

for sec61_data in sale_61sec.iloc:
    print(sec61_data['상품명'])
    status = 0
    if sec61_data['상품명'] == 'No.500':
        continue
    if sec61_data['상품명'] == '더블스퀘어링':
        status = 1
        stock_idx = stock_data[(stock_data['item_names'] == sec61_data['상품명']) & (
                    stock_data['item_colors'] == excetption_list['더블스퀘어링']['공통옵션'])].index[0]
        stock_61sec[stock_idx] += sec61_data['판매수량']
        for i in excetption_list['더블스퀘어링']:
            if i == '공통옵션':
                continue
            option_data = excetption_list['더블스퀘어링'][i]
            stock_idx = stock_data[(stock_data['item_names'] == option_data[0]) & (stock_data['item_colors'] == option_data[1])].index[0]
            stock_61sec[stock_idx] += sec61_data['판매수량']
    if status == 1:
        continue
    if sec61_data['상품명'] in excetption_list.keys():
        for except_option in excetption_list[sec61_data['상품명']].keys():
            if sec61_data['옵션'] == except_option:
                # print(sec61_data, "except")
                status = 1
                for except_data in excetption_list[sec61_data['상품명']][sec61_data['옵션']]:
                    stock_idx = stock_data[(stock_data['item_names'] == sec61_data['상품명']) & (stock_data['item_colors'] == except_data)].index[0]
                    stock_61sec[stock_idx] += sec61_data['판매수량']
    if status == 1:
        continue
    match_data = stock_data[(stock_data['item_names'] == sec61_data['상품명']) & (stock_data['item_colors'] == sec61_data['옵션'])]
    if len(match_data) == 0:
        print(sec61_data['상품명'], sec61_data['옵션'], "추가 안됨")
    else:
        # print(match_data)
        stock_idx = match_data.index[0]
        stock_61sec[stock_idx] += sec61_data['판매수량']

new_stock['sale_61sec'] = stock_61sec
new_stock['sale_61sec*2'] = stock_61sec * 2
new_stock['stock'] = new_stock['item_counts'] - new_stock['sale_61sec']
new_stock['stock(*2)'] = new_stock['item_counts'] - new_stock['sale_61sec*2']

temp_order = round(new_stock['item_counts'] / new_stock['sale_61sec*2'], 2)
new_stock['exp_3_weeks_stock'] = temp_order
order_now = np.zeros(shape=(len(new_stock),), dtype=int)
order_now[np.where(temp_order>1.5)] = 1
new_stock['order_now'] = order_now

new_stock.to_excel(f'./{current_date}_stock_match.xlsx', index=False)
import pandas as pd
import re
import datetime
import openpyxl
import openpyxl.cell._writer
import xlsxwriter

current_date = str(datetime.datetime.now().date()).replace('-', '')

df = pd.read_excel(f'./{current_date}_재고파일.xlsx')
df.columns = df.iloc[2]
df.drop([0, 1, 2], axis=0, inplace=True)
df = df[pd.isna(df['품명']) == False]
df = df.reset_index(drop=True)
# df['품명'][df['품명'] != '재고량'] =  df['품명'][df['품명'] != '재고량'].str.replace('  ', ' ')


new_column = []
count = 0
for idx, key in enumerate(df.keys()):
    if pd.isna(key):
        count += 1
        new_column.append(f"temp_{count}")
    else:
        new_column.append(key)
df.columns = new_column

append_list = {'category': [], 'item_names': [], 'item_colors': [], 'wian': [], 'won': [], 'item_counts': []}
status=0
for idx, data in enumerate(df.iloc):
    if data['품명'] == '중국이름':
        continue
    if re.findall(r'^[0-9]\.[가-힝]+', data['품명']):
        temp_category = data['품명']
        # print(temp_category)
        continue
    if data['품명'] != '재고량':
        if status != 0:
            print(status, "?")
            break
        status = 1
        temp_item_name = data['품명']
        for i in range(1, 13):
            if pd.isna(data[f'temp_{i}']):
                break
            append_list['item_colors'].append(data[f'temp_{i}'])
            append_list['item_names'].append(temp_item_name)
            append_list['wian'].append(data['위안'])
            append_list['won'].append(data['원화'])
            append_list['category'].append(temp_category)
        # print(temp_item_name)
    else:
        if status != 1:
            print(status, "?")
            break
        status = 0
        for i in range(1, 13):
            if pd.isna(data[f'temp_{i}']):
                break
            append_list['item_counts'].append(int(data[f"temp_{i}"]))
        if len(append_list['item_counts']) != len(append_list['item_names']):
            print("안맞음")
            break


test = pd.DataFrame(append_list)
test.to_excel(f'./{current_date}_podong_automation.xlsx', index=False)

import numpy as np
# import exception_list as ex
import json

# excetption_list = ex.get_exception_list()
file_path = "./exception_list.json"
with open(file_path, 'r', encoding='UTF-8-sig') as file:
    excetption_list = json.load(file)

sale_61sec = pd.read_csv(f'./{current_date}_61sec.csv')
stock_data = pd.read_excel(f'./{current_date}_podong_automation.xlsx')

new_stock = stock_data.copy()
stock_61sec = np.zeros(shape=(len(new_stock),), dtype=int)

f = open("error.txt", "w+")
for sec61_data in sale_61sec.iloc:
    # print(sec61_data['상품명'])
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
    if sec61_data['상품명'] == '사각 집게핀' and '스타일' in sec61_data['옵션']:
        extra_option = sec61_data['옵션'].split('\n')
        sec61_data['옵션'] = extra_option[1]
        if 'L size' in extra_option[0]:
            sec61_data['상품명'] = '사각 집게핀 (L size)'
        else :
            sec61_data['상품명'] = '사각 집게핀 (S size)'
    if sec61_data['상품명'] == 'No.13' and '하프' in sec61_data['옵션']:
        sec61_data['상품명'] = 'No.13 하프'
        sec61_data['옵션'] = sec61_data['옵션'].replace('하프', '').replace('  ', ' ')
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
        # if sec61_data['상품명'] = 'No.297':
        #     break
        print(sec61_data['상품명'], sec61_data['옵션'], "추가 안됨")
        f.write(f"{sec61_data['상품명']} {sec61_data['옵션']} `추가 안됨` \n")
    else:
        # print(match_data)
        stock_idx = match_data.index[0]
        stock_61sec[stock_idx] += sec61_data['판매수량']
f.close()

new_stock['sale_61sec'] = stock_61sec
new_stock['sale_61sec*2'] = stock_61sec * 2
# new_stock['stock'] = new_stock['item_counts'] - new_stock['sale_61sec']
# new_stock['stock(*2)'] = new_stock['item_counts'] - new_stock['sale_61sec*2']

temp_order = round(new_stock['item_counts'] / new_stock['sale_61sec*2'], 2)
new_stock['exp_3_weeks_stock'] = temp_order
order_now = np.zeros(shape=(len(new_stock),), dtype=int)
order_now[np.where(temp_order>1.5)] = 1
new_stock['order_now'] = order_now

del new_stock['wian']
del new_stock['won']
# stock_idx = stock_data[(stock_data['item_names'] == sec61_data['상품명']) & (stock_data['item_colors'] == except_data)].index[0]



# new_stock.to_excel(f'./{current_date}_stock_match.xlsx', index=False, freeze_panes=(1, 0))
def apply_column_format(df, file_path):
    def get_width(test_str):
        import string
        import re
        letter_to_width = {
            'lower': 0.95,  ## 영어 소문자 하나당 칼럼 폭
            'upper': 1.18,  ## 영어 대문자 하나당 칼럼 폭
            'digit': 1,  ## 숫자 하나당 칼럼 폭
            'korea': 1.85,  ## 한국어 한 글자당 칼럼 폭
            'other': 0.95,  ## 나머지 한 문자당 칼럼 폭
        }
        width = 0
        for c in test_str:
            if c in string.ascii_lowercase:
                width += letter_to_width['lower']
            elif c in string.ascii_uppercase:
                width += letter_to_width['upper']
            elif c in string.digits:
                width += letter_to_width['digit']
            elif re.match(r'[ㄱ-힣]', c):
                width += letter_to_width['korea']
            else:
                width += letter_to_width['other']

        return width

    def podong_get_width(test_str):
        width = 0
        if test_str == 'category':
            width = 12.75
        elif test_str == 'item_names':
            width = 30.13
        elif test_str == 'item_colors':
            width = 48.75
        elif test_str == 'item_counts':
            width = 16
        elif test_str == 'sale_61sec':
            width = 14.25
        elif test_str == 'sale_61sec*2':
            width = 16.5
        elif test_str == 'exp_3_weeks_stock':
            width = 22.5
        elif test_str == 'order_now':
            width = 14.5

        return width

    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
        ws = writer.sheets['Sheet1']

        ## 칼럼 폭 조절
        for i, col in enumerate(df.columns):
            width = podong_get_width(col)
            ws.set_column(i, i, width)

        ws.autofilter(0, 0, df.shape[0] - 1, df.shape[1] - 1)  ## 첫 행 필터 추가
        ws.freeze_panes(1, 0)  ## 첫 행 고정

apply_column_format(new_stock, f'./{current_date}_stock_match.xlsx')

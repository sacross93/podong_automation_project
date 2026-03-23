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
categories = len(new_column) - 7 + 1

append_list = {'category': [], 'item_names': [], 'item_colors': [], 'wian': [], 'won': [], 'item_counts': []}
temp_category = "미분류"
status=0
for idx, data in enumerate(df.iloc):
    if data['품명'] == '중국이름' or data['품명'] == 'package':
        continue
    if re.findall(r'^[0-9]\.[가-힝]+', str(data['품명'])):
        temp_category = data['품명']
        # print(temp_category)
        continue
    if data['품명'] != '재고량':
        if status != 0:
            print(status, "? 품명")
            break
        status = 1
        temp_item_name = data['품명']
        for i in range(1, categories):
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
        for i in range(1, categories):
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
# file_path = "./test/exception_list.json"
with open(file_path, 'r', encoding='UTF-8-sig') as file:
    excetption_list = json.load(file)

sale_61sec = pd.read_csv(f'./{current_date}_61sec.csv')
emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)
sale_61sec = sale_61sec.apply(lambda col: col.map(lambda x: emoji_pattern.sub('', x) if isinstance(x, str) else x))
stock_data = pd.read_excel(f'./{current_date}_podong_automation.xlsx')

new_stock = stock_data.copy()
stock_61sec = np.zeros(shape=(len(new_stock),), dtype=int)

import os
os.makedirs("./logs", exist_ok=True)
f = open("./logs/error.txt", "w+", encoding='utf-8')
for sec61_data in sale_61sec.iloc:
    status = 0
    item_name = sec61_data['상품명']
    item_option = sec61_data['옵션']
    sale_qty = sec61_data['판매수량']

    if item_name == '더블스퀘어링':
        status=1
        common_option = excetption_list['더블스퀘어링']['공통옵션']
        match_data = stock_data[(stock_data['item_names'] == '더블스퀘어링') & (stock_data['item_colors'] == common_option)]
        if len(match_data) > 0:
            common_option_stock_idx = match_data.index[0]
            stock_61sec[common_option_stock_idx] += sale_qty
        else:
            error_message = f"더블스퀘어링 공통옵션 '{common_option}'을 재고목록에서 찾을 수 없습니다.\n"
            print(error_message.strip())
            f.write(error_message)

        if "추가옵션" in item_option:
            except_data = excetption_list[item_name][item_option]
            match_data = stock_data[(stock_data['item_names'] == except_data[0]) & (stock_data['item_colors'] == except_data[1])]
            if len(match_data) > 0:
                stock_idx = match_data.index[0]
                stock_61sec[stock_idx] += sale_qty
            else:
                error_message = f"더블스퀘어링 추가옵션 '{item_option}' -> '{except_data}'을/를 재고목록에서 찾을 수 없습니다.\n"
                print(error_message.strip())
                f.write(error_message)

    if item_name == '사각 집게핀' and '스타일' in item_option:
        extra_option = item_option.split('\n')
        item_option = extra_option[1]
        if 'L size' in extra_option[0]:
            item_name = '사각 집게핀 (L size)'
        else:
            item_name = '사각 집게핀 (S size)'
    if item_name == 'No.13' and '종류' in item_option:
        option_parts = item_option.split('\n')
        if '하프' in option_parts[0]:
            item_name = 'No.13 하프'
        item_option = option_parts[1].replace('옵션 : ', '')
    if status == 1:
        continue
    if item_name in excetption_list.keys():
        for except_option in excetption_list[item_name].keys():
            if item_option == except_option:
                status = 1
                for except_data in excetption_list[item_name][item_option]:
                    match_data = stock_data[(stock_data['item_names'] == item_name) & (stock_data['item_colors'] == except_data)]
                    if len(match_data) > 0:
                        stock_idx = match_data.index[0]
                        stock_61sec[stock_idx] += sale_qty
                    else:
                        error_message = f"예외처리 실패: 상품명 '{item_name}', 옵션 '{item_option}'에 해당하는 재고 '{except_data}'를 찾을 수 없습니다.\n"
                        print(error_message.strip())
                        f.write(error_message)
    if status == 1:
        continue
    match_data = stock_data[(stock_data['item_names'] == item_name) & (stock_data['item_colors'] == item_option)]
    if len(match_data) == 0:
        name_match = stock_data[stock_data['item_names'] == item_name]
        if len(name_match) == 0:
            reason = f"[재고파일에 상품명 없음]"
        else:
            available = name_match['item_colors'].tolist()
            reason = f"[옵션 불일치] 가능한 옵션: {available}"
        print(f"{item_name} / {item_option} → 추가 안됨 {reason}")
        f.write(f"{item_name} / {item_option} → 추가 안됨 {reason}\n")
    else:
        stock_idx = match_data.index[0]
        stock_61sec[stock_idx] += sale_qty
f.close()

new_stock['sale_61sec'] = stock_61sec
new_stock['sale_61sec*2'] = stock_61sec * 2
# new_stock['stock'] = new_stock['item_counts'] - new_stock['sale_61sec']
# new_stock['stock(*2)'] = new_stock['item_counts'] - new_stock['sale_61sec*2']

temp_order = round(new_stock['item_counts'] / new_stock['sale_61sec*2'].replace(0, np.nan), 2)
new_stock['exp_3_weeks_stock'] = temp_order
order_now = np.zeros(shape=(len(new_stock),), dtype=int)
order_now[np.where(temp_order>1.5)] = 1
order_now[new_stock['sale_61sec*2'] == 0] = -1
new_stock['order_now'] = order_now

del new_stock['wian']
del new_stock['won']
# stock_idx = stock_data[(stock_data['item_names'] == sec61_data['상품명']) & (stock_data['item_colors'] == except_data)].index[0]



# new_stock.to_excel(f'./{current_date}_stock_match.xlsx', index=False, freeze_panes=(1, 0))
def apply_column_format(df, file_path):
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

    with pd.ExcelWriter(file_path, engine='xlsxwriter', engine_kwargs={'options': {'nan_inf_to_errors': True}}) as writer:
        df.to_excel(writer, index=False)
        ws = writer.sheets['Sheet1']

        ## 칼럼 폭 조절
        for i, col in enumerate(df.columns):
            width = podong_get_width(col)
            ws.set_column(i, i, width)

        ws.autofilter(0, 0, df.shape[0] - 1, df.shape[1] - 1)  ## 첫 행 필터 추가
        ws.freeze_panes(1, 0)  ## 첫 행 고정

apply_column_format(new_stock, f'./{current_date}_stock_match.xlsx')
# 한글 인코딩
new_stock.to_csv(f'./{current_date}_stock_match.csv', encoding='cp949')
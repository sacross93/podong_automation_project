import pandas as pd
import re
import datetime

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
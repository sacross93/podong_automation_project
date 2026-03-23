import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
# 파일 로드
data_path = 'C:/Users/wlsdu/OneDrive/문서/카카오톡 받은 파일/20240315_podong_automation.xlsx'
data = pd.read_excel(data_path)

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
# category별 item_counts 집계
category_counts = data.groupby('category')['item_counts'].sum()

# 시각화 개선
plt.figure(figsize=(12, 8))
colors = sns.color_palette('pastel', len(category_counts))

# 카테고리별 재고량 시각화
sns.barplot(y=category_counts.index, x=category_counts.values, palette=colors)
socks_inventory = data[data['category'] == '1.양말'].groupby('item_names')['item_counts'].sum()

# 시각화 개선: 각 막대에 재고량 표시
plt.figure(figsize=(15, 10))
barplot = sns.barplot(x=socks_inventory.values, y=socks_inventory.index, palette='viridis')

# 각 막대에 재고량 숫자 표시
for p in barplot.patches:
    width = p.get_width()
    plt.text(width + 50,  # 위치 조정
             p.get_y() + p.get_height() / 2,  # y 위치
             f'{int(width)}',  # 표시할 텍스트
             va='center')

title_font = {
    'fontsize': 20,
    'fontweight': 'bold'
}
title_left = plt.title('61sec & wangsmall socks stock', fontdict=title_font, loc='center', pad=20)
plt.xlabel('재고량', fontsize=12)
plt.ylabel('양말 이름', fontsize=12)
plt.savefig(f'./figure.png', dpi=500, bbox_inches='tight')




# Filter data for the "Socks" category (noted as "1.양말" in the dataset)
socks_df = data[data['category'] == '1.양말']

# Aggregate the total quantity of each item_name within the "Socks" category
socks_quantity = socks_df.groupby('item_names')['item_counts'].sum()

# Prepare the data for plotting
socks_quantity = socks_quantity.sort_values(ascending=False)  # Sorting for better visualization


numerical_parts = socks_quantity.index.str.extract(r'No\.(\d+)').astype(int)
socks_quantity_sorted = socks_quantity.iloc[numerical_parts.sort_values(by=0).index]

# Defining a range of pastel colors for the bars
pastel_colors = plt.cm.Pastel1(np.linspace(0, 1, len(socks_quantity_sorted)))

# Re-plotting with the updated specifications
plt.figure(figsize=(14, 10))
bars = plt.barh(socks_quantity_sorted.index, socks_quantity_sorted.values, color=pastel_colors)

# Adding the text with the total quantity next to each bar, in black font color
for bar in bars:
    plt.text(bar.get_width(), bar.get_y() + bar.get_height() / 2, int(bar.get_width()),
             va='center', ha='left', fontsize=8, color='black')

plt.title('Quantity of Items in the "Socks" Category with Total Quantities', fontsize=16)
plt.xlabel('Quantity', fontsize=14)
plt.ylabel('Item Names', fontsize=14)
plt.xticks(fontsize=10)
plt.yticks(fontsize=10)
plt.tight_layout()

# Show plot
plt.show()


# Defining a range of pastel colors for the bars again with numpy imported
pastel_colors = plt.cm.Pastel1(np.linspace(0, 1, len(socks_quantity_sorted)))

# Re-plotting with the corrected specifications
plt.figure(figsize=(14, 10))
bars = plt.barh(socks_quantity_sorted.index, socks_quantity_sorted.values, color=pastel_colors)

# Adding the text with the total quantity next to each bar, in black font color
for bar in bars:
    plt.text(bar.get_width(), bar.get_y() + bar.get_height() / 2, int(bar.get_width()),
             va='center', ha='left', fontsize=8, color='black')

plt.title('Quantity of Items in the "Socks" Category with Total Quantities', fontsize=16)
plt.xlabel('Quantity', fontsize=14)
plt.ylabel('Item Names', fontsize=14)
plt.xticks(fontsize=10)
plt.yticks(fontsize=10)
plt.tight_layout()

# Show plot
plt.show()
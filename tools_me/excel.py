import xlrd
from tools_me.svb import SVB

data = xlrd.open_workbook('yang.xlsx')
table = data.sheets()[0]
nrows = table.nrows
row_list = [table.row_values(i) for i in range(0, nrows)]
for i in row_list:
    card_id = i[5]
    print(card_id)
    response = SVB().card_detail(card_id)
    print(response)

from parser import Parser, SOURCE_DOMAIN
from histograms import ValueHist
import pandas as pd

SOURCE_URL = SOURCE_DOMAIN + '/ru/jobs-kharkiv-it/'

buffer = 'export.csv'
# parser = Parser(SOURCE_URL).gather().export(fname=buffer)

table = pd.read_csv(buffer)
table['experience'] = table['experience'].fillna(0)
print()
ValueHist(table, 'experience').plot()





import pandas as pd
import matplotlib.pyplot as plt


class ValueBar:
    def __init__(self, dataframe: pd.DataFrame, attribute: str):
        self.attribute = str
        self.map: pd.Series = dataframe[attribute].value_counts(ascending=False)
        self.normalized: pd.Series = dataframe[attribute].value_counts(ascending=False, normalize=True)

    def plot(self, to_file=None):
        span = range(len(self.map.values))
        plt.bar(span, self.map.values)
        plt.xticks(span, self.map.keys())
        plt.show()


class ValueHist:
    def __init__(self, dataframe: pd.DataFrame, attribute: str):
        self.attribute = str
        self.map: pd.Series = dataframe[attribute]

    def plot(self, to_file=None):
        plt.hist(self.map.values)
        plt.show()

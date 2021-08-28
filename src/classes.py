import pandas_datareader.data as web
import statsmodels.api as sm
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from statsmodels.tsa.stattools import coint
import pandas as pd


class TickersProcessor:
    '''
    Принимает список тикеров, стартовую дату и финальную дату
    Умеет скачивать движение цены указанных активов от стартовой до финальной даты

    Нужен для поиска коинтегрированных пар на указанном временном промежутке
    '''
    def __init__(self, tickers, startDate, endDate, initData=False):
        '''
        @param
        tickers :
        '''
        self._tickers = tickers
        self._startDate = startDate
        self._endDate = endDate
        self._data = self.getTickersData() if initData else None

    def getTickersData(self):
        '''
        Скачивает данные с yahoo finance
        '''
        self._data = web.DataReader(
            self._tickers,
            'yahoo',
            start=self._startDate,
            end=self._endDate).Close
        return self._data

    @property
    def data(self):
        return self._data

    def findCointegratedPairs(self):
        if self._data is None:
            self._data = data = self.getTickersData().dropna()
        else:
            data = self._data
        n = data.shape[1]
        keys = data.keys()
        pvalue_matrix = np.ones((n, n))

        pairs = []
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                S1 = data[keys[i]]
                S2 = data[keys[j]]
                res = coint(S1, S2)
                _, pvalue = res[0], res[1]
                pvalue_matrix[i, j] = pvalue
                if pvalue < 0.05:
                    pairs.append((keys[i], keys[j]))
        return keys, pvalue_matrix, pairs, keys

    def visualizeCointegration(self):
        _, pvalues, _, keys = self.findCointegratedPairs()
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.heatmap(pvalues, xticklabels=keys, yticklabels=keys, cmap='coolwarm', annot=True, fmt=".2f",
                    mask=(pvalues >= 0.99))

        ax.set_title('Матрица коинтегрированности, p-value')
        plt.tight_layout()
        plt.show()


class PairsWorker:
    def __init__(self, tickerA, tickerB, tickerAData, tickerBData):
        self._tickerA = tickerA
        self._tickerB = tickerB
        self._dataA = tickerAData
        self._dataB = tickerBData

    def getSpread(self):
        x_train = sm.add_constant(self._dataB)
        model = sm.OLS(self._dataA, x_train)
        result = model.fit()
        hedge_ratio = result.params[1]
        spread = self._dataA - self._dataB * hedge_ratio

        return spread, hedge_ratio

    def visualizeSpread(self):
        spread, _ = self.getSpread()
        spreadPlt = plt.figure(figsize=(12, 6))
        plt.plot(spread, label='Спред')
        plt.axhline(spread.mean(), color='black')
        spreadPlt.suptitle(f'Спред активов, {self._tickerA} & {self._tickerB}')
        plt.ylabel('Спред активов, USD')
        plt.xlabel('Дата')
        plt.grid(True)
        plt.show()

    def visualizePriceMovement(self, finalPairTextNeeded=False):
        text = ' -- выбрали эту пару для торговли'
        pricesPlt = plt.figure(figsize=(12, 6))

        plt.plot(self._dataA, label=self._tickerA)
        plt.plot(self._dataB, label=self._tickerB)
        title = f'Цены закрытия по дням, {self._tickerA} & {self._tickerB}'
        title += text if finalPairTextNeeded else ''
        pricesPlt.suptitle(title)
        plt.ylabel('Цена закрытия, USD')
        plt.xlabel('Дата')
        plt.grid(True)
        plt.legend()
        plt.show()


class Trader:
    def __init__(self, capital, tickerA, tickerB, tickerAData, tickerBData):
        self._capital = capital
        self._cntA = 0
        self._cntB = 0
        self._tickerA = tickerA
        self._tickerB = tickerB
        self._tickerAData = tickerAData
        self._tickerBData = tickerBData

        self._signals1 = pd.DataFrame()
        self._signals2 = pd.DataFrame()

    @property
    def capital(self):
        return self._capital

    @property
    def positions(self):
        return self._cntA, self._cntA

    def getZScore(self, series):
        zScore = (series - series.mean()) / series.std()
        zLow = zScore.mean() - zScore.std()
        zUp = zScore.mean() + zScore.std()
        return zLow, zScore, zUp

    def visualizeZScore(self):
        signals = pd.DataFrame()
        signals['z-low'], signals['z-score'], signals['z-up'] = self.getZScore(
            self._tickerAData / self._tickerBData)
        signals['z-score'].plot(label="z value")
        plt.title('z-score')
        plt.axhline(signals['z-score'].dropna().mean(), color="black")
        plt.axhline(1, color="red", label="upper threshold")
        plt.axhline(-1, color="green", label="lower threshold")
        plt.legend()
        plt.tight_layout()
        plt.show()

    def createSignals(self):
        signals = pd.DataFrame()
        signals[self._tickerA] = self._tickerAData
        signals[self._tickerB] = self._tickerBData
        ratios = self._tickerAData / self._tickerBData
        signals['z-low'], signals['z-score'], signals['z-up'] = self.getZScore(
            ratios)

        signals['signalsA'] = 0
        signals['signalsA'] = np.select(
            [signals['z-score'] > signals['z-up'],
             signals['z-score'] < signals['z-low']],
            [-1, 1],
            default=0)
        signals['positionsA'] = signals['signalsA'].diff()
        signals['signalsB'] = -signals['signalsA']
        signals['positionsB'] = signals['signalsB'].diff()
        return signals

    def visualizeTrades(self):
        signals = self.createSignals()

        fig = plt.figure(figsize=(12, 6))
        bx = fig.add_subplot(111)
        bx2 = bx.twinx()

        l1, = bx.plot(signals[self._tickerA], color='blue')
        l2, = bx2.plot(signals[self._tickerB], color='orange')

        u1, = bx.plot(signals[self._tickerA][signals['positionsA'] == 1],
                      lw=0, marker='^', markersize=8, c='g', alpha=0.7)
        d1, = bx.plot(signals[self._tickerA][signals['positionsA']
                      == -1], lw=0, marker='v', markersize=8, c='r', alpha=0.7)
        u2, = bx2.plot(signals[self._tickerB][signals['positionsB'] == 1],
                       lw=0, marker=3, markersize=9, c='g', alpha=0.9, markeredgewidth=3)
        d2, = bx2.plot(signals[self._tickerB][signals['positionsB'] == -1],
                       lw=0, marker=3, markersize=9, c='r', alpha=0.9, markeredgewidth=3)

        bx.set_ylabel(self._tickerA,)
        bx2.set_ylabel(self._tickerB, rotation=270)
        bx.yaxis.labelpad = 15
        bx2.yaxis.labelpad = 15
        bx.set_xlabel('Дата')
        bx.xaxis.labelpad = 15

        plt.legend([l1, l2, u1, d1, u2, d2], [
            self._tickerA,
            self._tickerB,
            f'LONG {self._tickerA}',
            f'SHORT {self._tickerA}',
            f'LONG {self._tickerB}',
            f'SHORT {self._tickerB}'
        ], loc='best')

        plt.title('Сигналы')
        plt.xlabel('Дата')
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def getSharpeRatio(self, returns, days, basePct=0.02):
        if basePct < 0 or basePct > 1:
            return None
        ret = (np.cumprod(1 + returns) - 1)[-1]
        return (ret - basePct) / (np.sqrt(days) * np.std(1 + returns))

    def getPortfolioStats(self):
        DAYS_ONE_YEAR = 365
        signals = self.createSignals()

        positionsA = self._capital // (2 * max(signals[self._tickerA]))
        positionsB = self._capital // (2 * max(signals[self._tickerB]))

        portfolio = pd.DataFrame()
        portfolio[self._tickerA] = signals[self._tickerA]
        portfolio['holdingsA'] = signals['positionsA'].cumsum() * \
            signals[self._tickerA] * positionsA
        portfolio['cashA'] = self._capital / 2 - \
            (signals['positionsA'] *
             signals[self._tickerA] *
             positionsA).cumsum()
        portfolio['totalA'] = portfolio['holdingsA'] + portfolio['cashA']
        portfolio['returnA'] = portfolio['totalA'].pct_change()
        portfolio['positionsA'] = signals['positionsA']

        portfolio[self._tickerB] = signals[self._tickerB]
        portfolio['holdingsB'] = signals['positionsB'].cumsum() * \
            signals[self._tickerB] * positionsB
        portfolio['cashB'] = self._capital / 2 - \
            (signals['positionsB'] *
             signals[self._tickerB] *
             positionsB).cumsum()
        portfolio['totalB'] = portfolio['holdingsB'] + portfolio['cashB']
        portfolio['returnB'] = portfolio['totalB'].pct_change()
        portfolio['positionsB'] = signals['positionsB']

        portfolio['total'] = portfolio['totalA'] + portfolio['totalB']
        finalPortfolio = portfolio['total'].iloc[-1]
        portfolio = portfolio.dropna()
        hDrawdown = max(portfolio['total']) / min(portfolio['total'])
        delta = (portfolio.index[-1] - portfolio.index[0]).days
        returns = (finalPortfolio /
                   self._capital) ** (DAYS_ONE_YEAR / delta) - 1

        return returns * 100, self.getSharpeRatio(portfolio['returnA'], delta), \
            self.getSharpeRatio(portfolio['returnB'], delta), hDrawdown, finalPortfolio

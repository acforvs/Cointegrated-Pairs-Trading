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
        '''
        Выполняет тест на коинтеграцию по всем парам

        Возвращает
            keys : список всех тикеров
            pvalue_matrix : матрица коинтегрированности
            pairs : list of tuples выбранных пар активов
        '''
        if self._data is None:
            self._data = data = self.getTickersData().dropna()
        else:
            data = self._data
        n = data.shape[1]
        keys = data.keys()
        pvalue_matrix = np.ones((n, n))

        pairs = []
        for i, key_i in enumerate(data):
            for j, key_j in enumerate(data):
                if i == j:
                    continue
                S1 = data[key_i]
                S2 = data[key_j]
                res = coint(S1, S2)
                _, pvalue = res[0], res[1]
                pvalue_matrix[i, j] = pvalue
                if pvalue < 0.05:
                    pairs.append((key_i, key_j))
        return keys, pvalue_matrix, pairs

    def visualizeCointegration(self):
        '''
        Heatmap по матрице коинтеграции
        '''
        keys, pvalues, _ = self.findCointegratedPairs()
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.heatmap(pvalues, xticklabels=keys, yticklabels=keys, cmap='coolwarm', annot=True, fmt=".2f",
                    mask=(pvalues >= 0.99))

        ax.set_title('Матрица коинтегрированности, p-value')
        plt.tight_layout()
        plt.show()


class PairsWorker:
    '''
    Принимает два тикера, а также информацию по их ценам
    Умеет вычислять спред при помощи OLS и строить визуализацию
    '''

    def __init__(self, tickerA, tickerB, tickerAData, tickerBData):
        self._tickerA = tickerA
        self._tickerB = tickerB
        self._dataA = tickerAData
        self._dataB = tickerBData

    def getSpread(self):
        '''
        Получить стационарный спред двух активов

        Возвращает
            spread : сам спред
            hedgeRatio : параметр регрессии
        '''
        xs = sm.add_constant(self._dataB)
        model = sm.OLS(self._dataA, xs)
        result = model.fit()
        hedgeRatio = result.params[1]
        spread = self._dataA - self._dataB * hedgeRatio

        return spread, hedgeRatio

    def visualizeSpread(self):
        '''
        Визуализирует спред
        '''
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
        '''
        Выводит изменение цен обоих активов на одном графике
        '''
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
    '''
    Принимает стартовый капитал, два тикера и информацию об их движении цен
    Умеет генерировать сигналы и моделировать торговлю
    '''

    def __init__(self, capital, tickerA, tickerB, tickerAData, tickerBData):
        self._capital = capital
        self._tickerA = tickerA
        self._tickerB = tickerB
        self._tickerAData = tickerAData
        self._tickerBData = tickerBData

        self._signals1 = pd.DataFrame()
        self._signals2 = pd.DataFrame()
        self._worker = PairsWorker(tickerA, tickerB, tickerAData, tickerBData)

    @property
    def capital(self):
        return self._capital

    def getZScore(self, series):
        '''
        Изменяет DataFrame, чтобы сделать E = 0, D = 1
        '''
        zScore = (series - series.mean()) / series.std()
        zLow = zScore.mean() - zScore.std()
        zUp = zScore.mean() + zScore.std()

        return zLow, zScore, zUp

    def visualizeZScore(self):
        '''
        Визуализирует z-score и threshold-ы, которые являются отсечками для начала торговли
        '''
        signals = pd.DataFrame()
        spread, _ = self._worker.getSpread()
        signals['z-low'], signals['z-score'], signals['z-up'] = self.getZScore(
            spread)
        signals['z-score'].plot(label="z value")
        plt.title('z-score')
        plt.axhline(signals['z-score'].dropna().mean(), color="black")
        plt.axhline(1, color="red", label="upper threshold")
        plt.axhline(-1, color="green", label="lower threshold")
        plt.legend()
        plt.tight_layout()
        plt.show()

    def createSignals(self):
        '''
        Генерирует сигналы для торговли

        Возвращает DataFrame с ключами
            signalsA & signalsB - сигналы по двум активам
            positionsA & positionsB - количество активов в любой момент времени
        '''
        signals = pd.DataFrame()
        signals[self._tickerA] = self._tickerAData
        signals[self._tickerB] = self._tickerBData
        spread, hedge = self._worker.getSpread()
        signals['z-low'], signals['z-score'], signals['z-up'] = self.getZScore(
            spread)

        signals['signalsA'] = 0
        signals['signalsA'] = np.select(
            [signals['z-score'] > 1,
             signals['z-score'] < -1],
            [-1, 1],
            default=0)
        signals['positionsA'] = signals['signalsA'].diff()
        signals['signalsB'] = -hedge * signals['signalsA']
        signals['positionsB'] = signals['signalsB'].diff()

        return signals, hedge

    def visualizeTrades(self):
        '''
        Рисует график с отметками сделок
        '''
        signals, hedge = self.createSignals()

        fig = plt.figure(figsize=(12, 6))
        bx = fig.add_subplot(111)
        bx2 = bx.twinx()

        pricesA, = bx.plot(signals[self._tickerA], color='blue')
        pricesB, = bx2.plot(signals[self._tickerB], color='orange')

        longA, = bx.plot(signals[self._tickerA][signals['positionsA'] == 1],
                         lw=0, marker='^', markersize=9, c='g', alpha=0.7)
        shortA, = bx.plot(signals[self._tickerA][signals['positionsA']
                                                 == -1], lw=0, marker='v', markersize=9, c='r', alpha=0.7)
        longB, = bx2.plot(signals[self._tickerB][signals['positionsB'] == hedge],
                          lw=0, marker=3, markersize=9, c='g', alpha=0.9, markeredgewidth=3)
        shortB, = bx2.plot(signals[self._tickerB][signals['positionsB'] == -hedge],
                           lw=0, marker=3, markersize=9, c='r', alpha=0.9, markeredgewidth=3)

        bx.set_ylabel(self._tickerA,)
        bx2.set_ylabel(self._tickerB, rotation=270)
        bx.yaxis.labelpad = 15
        bx2.yaxis.labelpad = 15
        bx.set_xlabel('Дата')
        bx.xaxis.labelpad = 15

        plt.legend([pricesA, pricesB, longA, shortA, longB, shortB], [
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
        '''
        Выдает коэффициент Шарпа, получая на вход дневную доходность по отношению к прошлому дню и количество прошедших дней

        Считает безрисковую процентную ставку по дефолту за 2% годовых
        '''
        if basePct < 0 or basePct > 1:
            return None
        ret = (np.cumprod(1 + returns) - 1)[-1]
        return (ret - basePct) / (np.sqrt(days) * np.std(1 + returns))

    def getPortfolioStats(self):
        '''
        Получить статистику по стратегии

        Возвращает
            ожидаемый годовой возврат стратегии
            коэффициент Шарпа первого актива
            коэффициент Шарпа второго актива
            отношение максимальной доходности к максимальной просадке
            финальное количество денег в портфеле
        '''
        DAYS_ONE_YEAR = 365
        signals, _ = self.createSignals()

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
            self.getSharpeRatio(
            portfolio['returnB'], delta), hDrawdown, finalPortfolio

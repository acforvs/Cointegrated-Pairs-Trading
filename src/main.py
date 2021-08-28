from classes import TickersProcessor, PairsWorker, Trader
from pairs_processor import getTickers


def backtest(startDate, endDate):
    '''
    Бектест на тестовом временном интервале

    Выдает пару, которая показала себя лучше всего
    '''
    tickers = getTickers()
    p = TickersProcessor(tickers, startDate, endDate)
    keys, _, pairs = p.findCointegratedPairs()
    p.visualizeCointegration()
    if not pairs:
        print('Не найдено подходящих для торговли пар, завершаем работу....')
        return
    print('Мы нашли следующие коинтегрированные пары: ', pairs)
    bestSharpeA, bestSharpeB = -float('inf'), -float('inf')
    bestHDrawdown = -float('inf')
    bestReturns = -float('inf')

    finalTickerA, finalTickerB = pairs[0]
    for tickerA, tickerB in pairs:
        worker = PairsWorker(
            tickerA,
            tickerB,
            p.data[tickerA],
            p.data[tickerB])
        worker.visualizePriceMovement()
        worker.visualizeSpread()

        t = Trader(10000, tickerA, tickerB, p.data[tickerA], p.data[tickerB])
        returns, sharpeA, sharpeB, hDrawdown, _ = t.getPortfolioStats()
        if sharpeA + sharpeB > bestSharpeA + bestSharpeB or \
                (abs(sharpeA + sharpeB - bestSharpeA - bestSharpeB) < 0.1 and hDrawdown >= 0.1 + bestHDrawdown):
            finalTickerA, finalTickerB = tickerA, tickerB

    return finalTickerA, finalTickerB


def main():
    capital = 10000
    testStartDate = '2010-01-01'
    testEndDate = '2019-12-31'
    finalStartDate = '2021-01-01'
    finalEndDate = '2021-08-13'

    tickerA, tickerB = backtest(testStartDate, testEndDate)
    print('После бектеста были выбраны пары: ', tickerA, tickerB)

    p = TickersProcessor([tickerA, tickerB],
                         finalStartDate, finalEndDate, True)
    worker = PairsWorker(tickerA, tickerB, p.data[tickerA], p.data[tickerB])
    worker.visualizePriceMovement(True)
    worker.visualizeSpread()

    t = Trader(capital, tickerA, tickerB, p.data[tickerA], p.data[tickerB])
    t.visualizeTrades()
    t.visualizeZScore()
    returns, sharpeA, sharpeB, hDrawdown, finalPortfolio = t.getPortfolioStats()

    print(
        f'Возврат на капитал: {returns}\nШарп первого актива: {sharpeA}\nШарп второго актива: {sharpeB}\nДоходность к просадке: {hDrawdown}')

    print(f'Было денег: {capital}, стало денег: {finalPortfolio}')


if __name__ == '__main__':
    main()

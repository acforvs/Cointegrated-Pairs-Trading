from parser import Parser

worker = Parser()


def getTickers():
    '''
    Получает тикеры либо из входного файла, либо выдает дефолтный набор
    '''
    path = worker.processArguments()
    if not path:
        return ['MSFT', 'ADBE', 'AAPL', 'V', 'MA',
                'AMZN', 'NVDA', 'GOOG', 'EWA', 'EWC']
    with open(path, 'r') as file:
        tickers = [line.strip() for line in file.readlines()]
        return [ticker for ticker in tickers if ticker]

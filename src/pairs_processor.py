from parser import Parser

worker = Parser()


def getTickers():
    path = worker.processArguments()
    if not path:
        return ['MSFT', 'ADBE', 'AAPL', 'V', 'MA', 'AMZN', 'NVDA', 'GOOG',
                'EWA', 'EWC', 'EWI', 'EWG', 'EWU', 'EWQ', 'EWL', 'EWK', 'EWO', 'EWN']
    with open(path, 'r') as file:
        tickers = [line.strip() for line in file.readlines()]
        return [ticker for ticker in tickers if ticker]

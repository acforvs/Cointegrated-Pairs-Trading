import argparse

ARGUMENTS = '''
[-f]    :    set path to an input file with a list of tickers
[-u]    :    usage
'''

USAGE = '''
Запуск трейдинговой стратегии на данных с 2021-01-01 до 2021-08-13
Если запустите без аргументов, то коинтегрированная пара найдется среди фиксированного набора акций
Иначе поиск будет осуществлен среди акций, указанных в файле
'''


class Parser:
    '''
    Command line arguments parser
    '''

    def __init__(self):
        self.parser = argparse.ArgumentParser()

    def parse(self):
        self.parser.add_argument(
            '-u',
            '--usage',
            action='store_true',
            help='Usage'
        )
        self.parser.add_argument(
            '-f',
            '--file',
            action='store',
            nargs=1,
            type=str,
            help='Set path to an input file with a list of tickers'
        )
        arguments = self.parser.parse_args()
        return arguments

    def processArguments(self):
        '''
        Processing the arguments from the command line
        '''
        arguments = self.parse()
        if arguments.file:
            return arguments.file[0]

        if arguments.usage:
            print(USAGE)

        return None

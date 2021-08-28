import argparse

ARGUMENTS = '''
[-f]    :    Указать путь до файла со списком тикеров
'''


class Parser:
    '''
    Парсер аргументов командной строки
    '''

    def __init__(self):
        self.parser = argparse.ArgumentParser()

    def parse(self):
        '''
        Парсит аргументы командной строки
        '''
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
        Обрабатывает аргументы командной строки
        '''
        arguments = self.parse()
        if arguments.file:
            return arguments.file[0]

        return None

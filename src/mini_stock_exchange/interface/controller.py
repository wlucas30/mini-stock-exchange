from mini_stock_exchange.commands.execute import ErrorResponse, Executor
from mini_stock_exchange.commands.lexer import LexerError, lex
from mini_stock_exchange.commands.parser import Parser, ParserError
from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.interface.render import RenderedOutput, Renderer


class Controller:
    def __init__(self, exchange: Exchange) -> None:
        self._exchange = exchange
        self._executor = Executor(exchange)
        self._renderer = Renderer()

    def process(self, source: str) -> RenderedOutput:
        try:
            tokens = lex(source)
            command = Parser(tokens).parse()
            response = self._executor.execute(command)
        except (LexerError, ParserError) as error:
            response = ErrorResponse(message=str(error))

        return self._renderer.render(response)

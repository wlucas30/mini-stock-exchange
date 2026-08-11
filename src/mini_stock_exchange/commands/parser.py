"""Contains the parser which converts tokens into the internal Command datatype."""

from mini_stock_exchange.exchange.models import OrderType, Side

from .command import (
    AddInstrument,
    AddParticipant,
    CancelOrder,
    Command,
    FastForward,
    ListInstruments,
    ListParticipants,
    PlaceOrder,
    SetTimeMultiplier,
    ShowBook,
    ShowGraph,
    ShowParticipant,
    ShowTime,
    ShowTrades,
)
from .lexer import Token, TokenType


class ParserError(ValueError):
    pass


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._current = 0

    def _peek(self) -> Token:
        """Return the current token without consuming it."""
        return self._tokens[self._current]

    def _advance(self) -> Token:
        """Consume and return the current token."""
        token = self._peek()

        if token.type is not TokenType.END:
            self._current += 1

        return token

    def _expect(self, expected: TokenType) -> Token:
        """Consume the expected token or raise a parser error."""
        token = self._peek()

        if token.type is not expected:
            raise ParserError(
                f"Expected {expected.name}, "
                f"found {token.type.name} at character position {token.position}"
            )

        return self._advance()

    def _expect_positive_integer(self, name: str) -> int:
        token = self._expect(TokenType.INTEGER)
        value = int(token.lexeme)

        if value <= 0:
            raise ParserError(
                f"{name} must be positive at character position {token.position}"
            )

        return value

    def _expect_nonnegative_integer(self, name: str) -> int:
        token = self._expect(TokenType.INTEGER)
        value = int(token.lexeme)

        if value < 0:
            raise ParserError(
                f"{name} cannot be negative at character position {token.position}"
            )

        return value

    def parse(self) -> Command:
        match self._peek().type:
            case TokenType.ADD:
                self._advance()
                match self._peek().type:
                    case TokenType.INSTR | TokenType.PARTICIPANT:
                        add = self._advance()
                        ident = self._expect(TokenType.IDENTIFIER)
                        self._expect(TokenType.END)
                        if add.type == TokenType.INSTR:
                            return AddInstrument(symbol=ident.lexeme)
                        else:
                            return AddParticipant(participant_id=ident.lexeme)
                    case _:
                        raise ParserError(
                            f"Command not recognised: ADD {self._peek().lexeme}"
                        )

            case TokenType.AS:
                self._advance()
                participant_ident = self._expect(TokenType.IDENTIFIER)
                match self._peek().type:
                    case TokenType.BUY | TokenType.SELL:
                        side = (
                            Side.BUY
                            if self._peek().type == TokenType.BUY
                            else Side.SELL
                        )
                        self._advance()
                        symbol_ident = self._expect(TokenType.IDENTIFIER)
                        match self._peek().type:
                            case TokenType.MARKET:
                                order_type = OrderType.MARKET
                            case TokenType.LIMIT:
                                order_type = OrderType.LIMIT
                            case _:
                                raise ParserError(
                                    f"Expected MARKET or LIMIT after {
                                        symbol_ident.lexeme
                                    }"
                                )

                        if order_type == OrderType.LIMIT:
                            self._expect(TokenType.LIMIT)
                            self._expect(TokenType.PRICE)
                            price = self._expect_positive_integer("Price")
                        else:
                            self._expect(TokenType.MARKET)
                            price = None

                        self._expect(TokenType.QUANTITY)
                        quantity = self._expect_positive_integer("Quantity")

                        self._expect(TokenType.END)

                        return PlaceOrder(
                            participant_id=participant_ident.lexeme,
                            side=side,
                            symbol=symbol_ident.lexeme,
                            order_type=order_type,
                            quantity=quantity,
                            price_ticks=price,
                        )

                    case TokenType.CANCEL:
                        self._advance()
                        self._expect(TokenType.ORDER)
                        order_id = self._expect_positive_integer("Order ID")
                        self._expect(TokenType.END)

                        return CancelOrder(
                            participant_id=participant_ident.lexeme,
                            order_id=order_id,
                        )

                    case _:
                        raise ParserError(
                            f"Command not recognised: AS {participant_ident.lexeme}"
                            + f"{self._peek().lexeme}"
                        )

            case TokenType.LIST:
                self._advance()
                match self._peek().type:
                    case TokenType.INSTR:
                        self._advance()
                        self._expect(TokenType.END)
                        return ListInstruments()

                    case TokenType.PARTICIPANT:
                        self._advance()
                        self._expect(TokenType.END)
                        return ListParticipants()

                    case _:
                        raise ParserError(
                            f"Command not recognised: LIST {self._peek().lexeme}"
                        )

            case TokenType.SET:
                self._advance()
                self._expect(TokenType.TIME)
                self._expect(TokenType.MULTIPLIER)
                multiplier = self._expect_nonnegative_integer("Multiplier")
                self._expect(TokenType.END)
                return SetTimeMultiplier(multiplier=multiplier)

            case TokenType.FAST:
                self._advance()
                self._expect(TokenType.FORWARD)
                delta = self._expect_nonnegative_integer("Fast-forward delta")
                self._expect(TokenType.END)
                return FastForward(delta=delta)

            case TokenType.SHOW:
                self._advance()
                match self._peek().type:
                    case TokenType.BOOK:
                        self._advance()
                        ident = self._expect(TokenType.IDENTIFIER)
                        self._expect(TokenType.END)
                        return ShowBook(symbol=ident.lexeme)

                    case TokenType.PARTICIPANT:
                        self._advance()
                        ident = self._expect(TokenType.IDENTIFIER)
                        self._expect(TokenType.END)
                        return ShowParticipant(participant_id=ident.lexeme)

                    case TokenType.TRADES:
                        self._advance()
                        self._expect(TokenType.END)
                        return ShowTrades()

                    case TokenType.TIME:
                        self._advance()
                        self._expect(TokenType.END)
                        return ShowTime()

                    case TokenType.GRAPH:
                        self._advance()
                        ident = self._expect(TokenType.IDENTIFIER)
                        self._expect(TokenType.END)
                        return ShowGraph(symbol=ident.lexeme)

                    case _:
                        raise ParserError(
                            f"Command not recognised: SHOW {self._peek().lexeme}"
                        )

            case _:
                raise ParserError(f"Command not recognised: {self._peek().lexeme}")

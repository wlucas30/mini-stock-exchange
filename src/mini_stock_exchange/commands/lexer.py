from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    ADD = auto()
    AS = auto()
    BOOK = auto()
    BUY = auto()
    CANCEL = auto()
    FAST = auto()
    FORWARD = auto()
    GRAPH = auto()
    INSTR = auto()
    LIMIT = auto()
    LIST = auto()
    MARKET = auto()
    MULTIPLIER = auto()
    ORDER = auto()
    PARTICIPANT = auto()
    PERFORMANCE = auto()
    PRICE = auto()
    QUANTITY = auto()
    SELL = auto()
    SET = auto()
    SHOW = auto()
    STATS = auto()
    TIME = auto()
    TRADES = auto()
    VOLUME = auto()

    IDENTIFIER = auto()
    INTEGER = auto()
    END = auto()


KEYWORDS: dict[str, TokenType] = {
    "ADD": TokenType.ADD,
    "AS": TokenType.AS,
    "BOOK": TokenType.BOOK,
    "BUY": TokenType.BUY,
    "CANCEL": TokenType.CANCEL,
    "FAST": TokenType.FAST,
    "FORWARD": TokenType.FORWARD,
    "GRAPH": TokenType.GRAPH,
    "INSTR": TokenType.INSTR,
    "LIMIT": TokenType.LIMIT,
    "LIST": TokenType.LIST,
    "MARKET": TokenType.MARKET,
    "MULTIPLIER": TokenType.MULTIPLIER,
    "ORDER": TokenType.ORDER,
    "PARTICIPANT": TokenType.PARTICIPANT,
    "PERFORMANCE": TokenType.PERFORMANCE,
    "PRICE": TokenType.PRICE,
    "QUANTITY": TokenType.QUANTITY,
    "SELL": TokenType.SELL,
    "SET": TokenType.SET,
    "SHOW": TokenType.SHOW,
    "STATS": TokenType.STATS,
    "TIME": TokenType.TIME,
    "TRADES": TokenType.TRADES,
    "VOLUME": TokenType.VOLUME,
}


@dataclass(frozen=True)
class Token:
    type: TokenType
    lexeme: str
    position: int


class LexerError(ValueError):
    pass


def lex(source: str) -> list[Token]:
    """Convert command source into tokens ending with an END token."""
    tokens: list[Token] = []
    position = 0

    for word in source.split():
        start = source.find(word, position)
        position = start + len(word)

        if word in KEYWORDS:
            token_type = KEYWORDS[word]
        elif word.isdigit():
            token_type = TokenType.INTEGER
        elif is_identifier(word):
            token_type = TokenType.IDENTIFIER
        else:
            raise LexerError(f"Invalid token {word!r} at character position {start}")

        tokens.append(
            Token(
                type=token_type,
                lexeme=word,
                position=start,
            )
        )

    tokens.append(
        Token(
            type=TokenType.END,
            lexeme="",
            position=len(source),
        )
    )

    return tokens


def is_identifier(word: str) -> bool:
    if not word:
        return False

    if not ("A" <= word[0] <= "Z"):
        return False

    return all("A" <= char <= "Z" or "0" <= char <= "9" or char == "_" for char in word)

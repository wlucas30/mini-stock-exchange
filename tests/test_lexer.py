import pytest

from mini_stock_exchange.commands.lexer import (
    KEYWORDS,
    LexerError,
    Token,
    TokenType,
    lex,
)


def test_lexes_command_and_records_token_positions() -> None:
    source = "AS ALICE BUY AAPL LIMIT PRICE 10490 QUANTITY 7"

    assert lex(source) == [
        Token(TokenType.AS, "AS", 0),
        Token(TokenType.IDENTIFIER, "ALICE", 3),
        Token(TokenType.BUY, "BUY", 9),
        Token(TokenType.IDENTIFIER, "AAPL", 13),
        Token(TokenType.LIMIT, "LIMIT", 18),
        Token(TokenType.PRICE, "PRICE", 24),
        Token(TokenType.INTEGER, "10490", 30),
        Token(TokenType.QUANTITY, "QUANTITY", 36),
        Token(TokenType.INTEGER, "7", 45),
        Token(TokenType.END, "", len(source)),
    ]


@pytest.mark.parametrize(("lexeme", "token_type"), KEYWORDS.items())
def test_recognises_keywords(lexeme: str, token_type: TokenType) -> None:
    assert lex(lexeme) == [
        Token(token_type, lexeme, 0),
        Token(TokenType.END, "", len(lexeme)),
    ]


def test_accepts_uppercase_identifier_with_digits_and_underscores() -> None:
    assert lex("TRADER_01") == [
        Token(TokenType.IDENTIFIER, "TRADER_01", 0),
        Token(TokenType.END, "", 9),
    ]


def test_ignores_whitespace_but_preserves_source_positions() -> None:
    source = "  SHOW\tTIME  "

    assert lex(source) == [
        Token(TokenType.SHOW, "SHOW", 2),
        Token(TokenType.TIME, "TIME", 7),
        Token(TokenType.END, "", len(source)),
    ]


def test_empty_source_returns_only_end_token() -> None:
    assert lex("") == [Token(TokenType.END, "", 0)]


@pytest.mark.parametrize(
    "invalid_token",
    [
        "show",
        "ALIce",
        "_ALICE",
        "123ALICE",
        "ALICE!",
    ],
)
def test_rejects_invalid_tokens(invalid_token: str) -> None:
    with pytest.raises(
        LexerError,
        match=rf"Invalid token {invalid_token!r} at character position 0",
    ):
        lex(invalid_token)

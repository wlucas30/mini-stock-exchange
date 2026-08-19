from dataclasses import dataclass
from queue import Empty, Queue
from threading import Thread
from time import monotonic

from mini_stock_exchange.commands.execute import (
    ErrorResponse,
    Executor,
    ExecutorResponse,
)
from mini_stock_exchange.commands.lexer import LexerError, lex
from mini_stock_exchange.commands.parser import Parser, ParserError
from mini_stock_exchange.interface.render import RenderedOutput, Renderer
from mini_stock_exchange.simulation import ProgressCallback, Simulation


@dataclass(frozen=True, kw_only=True)
class _CommandRequest:
    source: str
    responses: Queue[ExecutorResponse | Exception]


@dataclass(frozen=True)
class _Stop:
    pass


type _Event = _CommandRequest | _Stop


class Controller:
    """Serialises user commands and automatic ticks on one worker thread."""

    def __init__(
        self,
        simulation: Simulation,
        tick_interval_seconds: float = 1.0,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        if tick_interval_seconds <= 0:
            raise ValueError("Tick interval must be positive")

        self._simulation = simulation
        self._executor = Executor(
            simulation.exchange,
            simulation,
            progress_callback=progress_callback,
        )
        self._renderer = Renderer()
        self._tick_interval_seconds = tick_interval_seconds
        self._events: Queue[_Event] = Queue()
        self._closed = False
        self._worker = Thread(target=self._run, daemon=True)
        self._worker.start()

    def _execute(self, source: str) -> ExecutorResponse:
        try:
            command = Parser(lex(source)).parse()
            return self._executor.execute(command)
        except (LexerError, ParserError) as error:
            return ErrorResponse(message=str(error))

    def _advance_due_ticks(self, next_tick: float) -> float:
        """Catch up simulation time with real-time, and return the next deadline."""
        now = monotonic()
        while now >= next_tick:
            self._simulation.advance()
            next_tick += self._tick_interval_seconds
        return next_tick

    def _run(self) -> None:
        next_tick = monotonic() + self._tick_interval_seconds

        while True:
            timeout = max(0.0, next_tick - monotonic())
            try:
                event = self._events.get(timeout=timeout)
            except Empty:
                next_tick = self._advance_due_ticks(next_tick)
                continue

            if isinstance(event, _Stop):
                return

            next_tick = self._advance_due_ticks(next_tick)
            try:
                response: ExecutorResponse | Exception = self._execute(event.source)
            except Exception as error:
                response = error
            event.responses.put(response)

    def process(self, source: str) -> RenderedOutput:
        if self._closed:
            raise RuntimeError("Controller is closed")

        responses: Queue[ExecutorResponse | Exception] = Queue(maxsize=1)
        self._events.put(_CommandRequest(source=source, responses=responses))
        response = responses.get()

        if isinstance(response, Exception):
            raise response

        return self._renderer.render(response)

    def close(self) -> None:
        if self._closed:
            return

        self._closed = True
        self._events.put(_Stop())
        self._worker.join()

    def __enter__(self) -> Controller:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

from typing import Protocol


class UnitOfWork(Protocol):
    def commit(self) -> None:
        raise NotImplementedError

    def rollback(self) -> None:
        raise NotImplementedError

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Page:
    page: int = 1
    page_size: int = 20

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page must be greater than zero")
        if self.page_size < 1 or self.page_size > 100:
            raise ValueError("page_size must be between 1 and 100")

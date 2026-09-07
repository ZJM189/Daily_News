"""Start a disposable E2E API. Requires a migrated database ending in _test."""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import uvicorn
from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.application.identity.passwords import PasswordService
from app.infrastructure.models import Favorite, FavoriteFolder, Item, Source, User, UserPreference


def main():
    url = os.environ["FAVORITES_TEST_DATABASE_URL"]
    if not (make_url(url).database or "").endswith("_test"):
        raise RuntimeError("E2E requires a disposable database ending in _test")
    password = os.environ["E2E_PASSWORD"]
    os.environ["DATABASE_URL"] = url
    os.environ["APP_ENV"] = "development"
    os.environ["SESSION_COOKIE_SECURE"] = "false"
    engine = create_engine(url)
    with Session(engine) as session, session.begin():
        for project in ["desktop", "mobile"]:
            username = f"favorites-e2e-{project}"
            user = session.scalar(select(User).where(User.username == username))
            if user is None:
                user = User(
                    username=username,
                    role="user",
                    password_hash=PasswordService().hash_password(password),
                )
                session.add(user)
                session.flush()
            else:
                user.password_hash = PasswordService().hash_password(password)
            session.execute(delete(Favorite).where(Favorite.user_id == user.id))
            session.execute(delete(FavoriteFolder).where(FavoriteFolder.user_id == user.id))
            preference = session.get(UserPreference, user.id)
            if preference is None:
                preference = UserPreference(user_id=user.id)
                session.add(preference)
            preference.follow_keywords = ["Favorite E2E"]
        source = session.scalar(select(Source).where(Source.name == "Favorites E2E source"))
        if source is None:
            source = Source(name="Favorites E2E source", type="github")
            session.add(source)
            session.flush()
            for i in range(25):
                session.add(
                    Item(
                        source_id=source.id,
                        title=f"Favorite E2E {i:02d} - Agent 工程实践与开源工具",
                        normalized_title=f"favorite e2e {i}",
                        title_hash=str(uuid4()),
                        url=f"https://example.com/e2e/{i}",
                        category="open_source",
                        score=80 + i / 2,
                        summary_zh="围绕智能体的工具调用、任务编排和评估，整理可复现的工程实践与开源实现。",
                        importance_zh="帮助开发者比较不同实现的可靠性，并为实际项目选择合适的工具。",
                        published_at=datetime.now(UTC) - timedelta(hours=i),
                        tags=["Agent", "开源"],
                    )
                )
    engine.dispose()
    uvicorn.run("app.main:create_app", factory=True, host="127.0.0.1", port=8100)


if __name__ == "__main__":
    main()

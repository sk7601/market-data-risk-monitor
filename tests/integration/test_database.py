from sqlalchemy import inspect

from market.database import Base, engine


def test_schema():
    db = engine("sqlite://")
    Base.metadata.create_all(db)
    assert len(inspect(db).get_table_names()) == 7
    Base.metadata.drop_all(db)
    assert not inspect(db).get_table_names()
    db.dispose()

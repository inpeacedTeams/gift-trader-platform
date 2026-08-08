from sqlalchemy.orm import configure_mappers

from app.db.models import Collection, Gift


def test_collection_gift_relationship_is_configurable():
    configure_mappers()

    assert Collection.gifts.property.mapper.class_ is Gift
    assert Gift.collection.property.mapper.class_ is Collection


def test_gift_collection_id_references_collections_table():
    foreign_keys = Gift.__table__.c.collection_id.foreign_keys

    assert len(foreign_keys) == 1
    assert next(iter(foreign_keys)).target_fullname == "collections.id"

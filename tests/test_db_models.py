from sqlalchemy.orm import configure_mappers

from app.db.models import Collection, Gift


def test_collection_gift_relationship_is_configured():
    configure_mappers()

    collection = Collection(chain_address="EQcollection")
    gift = Gift(canonical_id="EQgift")
    collection.gifts.append(gift)

    assert gift.collection is collection

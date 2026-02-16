from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.gift import GiftBinding
from app.models.red_packet import (
    RedPacket,
    RedPacketBatch,
    RedPacketCategory,
    RedPacketTag,
    RedPacketTagBinding,
)


class RedPacketRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_batch(self, batch_no: str, source: str = "import") -> RedPacketBatch:
        batch = RedPacketBatch(batch_no=batch_no, source=source)
        self.db.add(batch)
        self.db.flush()
        return batch

    def create_item(
        self,
        batch_id: int,
        title: str,
        amount: float,
        level: int,
        content_type: str,
        content_value: str,
        content_image_url: str = "",
        content_image_key: str = "",
        category_id: int | None = None,
        meta_json: str = "{}",
        available_from=None,
        available_to=None,
    ) -> RedPacket:
        item = RedPacket(
            batch_id=batch_id,
            title=title,
            category_id=category_id,
            amount=amount,
            level=level,
            content_type=content_type,
            content_value=content_value,
            content_image_url=content_image_url,
            content_image_key=content_image_key,
            meta_json=meta_json,
            claim_url=content_value if content_type == "url" else "",
            status="idle",
            available_from=available_from,
            available_to=available_to,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def list_items(self, limit: int = 100) -> list[RedPacket]:
        stmt = (
            select(RedPacket)
            .where(RedPacket.status != "deleted")
            .order_by(RedPacket.id.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_item(self, red_packet_id: int) -> RedPacket | None:
        return self.db.get(RedPacket, red_packet_id)

    def delete_item(self, item: RedPacket) -> None:
        self.db.delete(item)

    def query_idle(self) -> Select[tuple[RedPacket]]:
        return select(RedPacket).where(RedPacket.status == "idle").order_by(RedPacket.id.asc())

    def get_category_by_code(self, code: str) -> RedPacketCategory | None:
        stmt = select(RedPacketCategory).where(RedPacketCategory.code == code)
        return self.db.scalar(stmt)

    def get_category_by_name(self, name: str) -> RedPacketCategory | None:
        stmt = select(RedPacketCategory).where(RedPacketCategory.name == name)
        return self.db.scalar(stmt)

    def create_category(
        self, name: str, code: str, is_builtin: bool, allowed_content_types: str
    ) -> RedPacketCategory:
        category = RedPacketCategory(
            name=name,
            code=code,
            is_builtin=is_builtin,
            allowed_content_types=allowed_content_types,
        )
        self.db.add(category)
        self.db.flush()
        return category

    def list_categories(self) -> list[RedPacketCategory]:
        stmt = select(RedPacketCategory).order_by(
            RedPacketCategory.is_builtin.desc(), RedPacketCategory.id.asc()
        )
        return list(self.db.scalars(stmt).all())

    def get_tag_by_name(self, name: str) -> RedPacketTag | None:
        stmt = select(RedPacketTag).where(RedPacketTag.name == name)
        return self.db.scalar(stmt)

    def create_tag(self, name: str) -> RedPacketTag:
        tag = RedPacketTag(name=name)
        self.db.add(tag)
        self.db.flush()
        return tag

    def bind_tag(self, red_packet_id: int, tag_id: int) -> None:
        exists_stmt = select(RedPacketTagBinding.id).where(
            RedPacketTagBinding.red_packet_id == red_packet_id,
            RedPacketTagBinding.tag_id == tag_id,
        )
        if self.db.scalar(exists_stmt):
            return
        self.db.add(RedPacketTagBinding(red_packet_id=red_packet_id, tag_id=tag_id))

    def get_categories_map(self, category_ids: set[int]) -> dict[int, RedPacketCategory]:
        if not category_ids:
            return {}
        stmt = select(RedPacketCategory).where(RedPacketCategory.id.in_(category_ids))
        categories = self.db.scalars(stmt).all()
        return {item.id: item for item in categories}

    def get_tags_map(self, red_packet_ids: set[int]) -> dict[int, list[str]]:
        if not red_packet_ids:
            return {}
        stmt = (
            select(RedPacketTagBinding.red_packet_id, RedPacketTag.name)
            .join(RedPacketTag, RedPacketTag.id == RedPacketTagBinding.tag_id)
            .where(RedPacketTagBinding.red_packet_id.in_(red_packet_ids))
        )
        result: dict[int, list[str]] = {}
        for red_packet_id, name in self.db.execute(stmt).all():
            result.setdefault(int(red_packet_id), []).append(str(name))
        return result

    def list_active_gift_bindings(self, red_packet_id: int) -> list[GiftBinding]:
        stmt = select(GiftBinding).where(
            GiftBinding.red_packet_id == red_packet_id,
            GiftBinding.status == "active",
        )
        return list(self.db.scalars(stmt).all())

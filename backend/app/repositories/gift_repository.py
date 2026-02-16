from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.gift import GiftBinding, GiftQrcode
from app.models.red_packet import RedPacket


class GiftRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_gift(
        self,
        title: str,
        token_plain: str,
        token_hash: str,
        activate_at,
        expire_at,
        binding_mode: str,
        dispatch_strategy: str,
        style_type: str,
        style_config: str,
        storage_channel_id: str,
        image_url: str,
        object_key: str,
    ) -> GiftQrcode:
        gift = GiftQrcode(
            title=title,
            status="draft",
            token_plain=token_plain,
            token_hash=token_hash,
            activate_at=activate_at,
            expire_at=expire_at,
            binding_mode=binding_mode,
            dispatch_strategy=dispatch_strategy,
            style_type=style_type,
            style_config=style_config,
            storage_channel_id=storage_channel_id,
            image_url=image_url,
            object_key=object_key,
        )
        self.db.add(gift)
        self.db.flush()
        return gift

    def list_gifts(self, limit: int = 100) -> list[GiftQrcode]:
        stmt = select(GiftQrcode).order_by(GiftQrcode.id.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())

    def get_gift(self, gift_id: int) -> GiftQrcode | None:
        return self.db.get(GiftQrcode, gift_id)

    def delete_gift(self, gift: GiftQrcode) -> None:
        self.db.delete(gift)

    def get_by_token_hash(self, token_hash: str) -> GiftQrcode | None:
        stmt = select(GiftQrcode).where(GiftQrcode.token_hash == token_hash)
        return self.db.scalar(stmt)

    def get_by_token_plain(self, token_plain: str) -> GiftQrcode | None:
        stmt = select(GiftQrcode).where(GiftQrcode.token_plain == token_plain)
        return self.db.scalar(stmt)

    def bind_red_packet(self, gift_qrcode_id: int, red_packet_id: int) -> GiftBinding:
        binding = GiftBinding(
            gift_qrcode_id=gift_qrcode_id, red_packet_id=red_packet_id, status="active"
        )
        self.db.add(binding)
        return binding

    def remove_binding(self, binding: GiftBinding) -> None:
        self.db.delete(binding)

    def list_bindings(self, gift_qrcode_id: int) -> list[GiftBinding]:
        stmt = select(GiftBinding).where(
            GiftBinding.gift_qrcode_id == gift_qrcode_id,
            GiftBinding.status == "active",
        )
        return list(self.db.scalars(stmt).all())

    def get_binding(self, gift_qrcode_id: int) -> GiftBinding | None:
        stmt = select(GiftBinding).where(
            GiftBinding.gift_qrcode_id == gift_qrcode_id,
            GiftBinding.status == "active",
        )
        return self.db.scalar(stmt)

    def get_idle_red_packet(self) -> RedPacket | None:
        stmt = select(RedPacket).where(RedPacket.status == "idle").order_by(RedPacket.id.asc())
        return self.db.scalar(stmt)

    def list_idle_red_packets_by_ids(self, ids: list[int]) -> list[RedPacket]:
        if not ids:
            return []
        stmt = (
            select(RedPacket)
            .where(RedPacket.id.in_(ids), RedPacket.status == "idle")
            .order_by(RedPacket.id.asc())
        )
        return list(self.db.scalars(stmt).all())

    def list_red_packets_by_ids(self, ids: list[int]) -> list[RedPacket]:
        if not ids:
            return []
        stmt = select(RedPacket).where(RedPacket.id.in_(ids)).order_by(RedPacket.id.asc())
        return list(self.db.scalars(stmt).all())

    def get_active_binding_by_packet_id(self, red_packet_id: int) -> GiftBinding | None:
        stmt = select(GiftBinding).where(
            GiftBinding.red_packet_id == red_packet_id,
            GiftBinding.status == "active",
        )
        return self.db.scalar(stmt)

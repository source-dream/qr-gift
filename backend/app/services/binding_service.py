from sqlalchemy.orm import Session

from app.models.qrcode import Qrcode
from app.models.red_packet import RedPacket
from app.repositories.binding_repository import BindingRepository


class BindingService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BindingRepository(db)

    def bind_manual(self, qrcode_id: int, red_packet_id: int) -> None:
        qrcode = self.db.get(Qrcode, qrcode_id)
        packet = self.db.get(RedPacket, red_packet_id)
        if not qrcode or not packet:
            raise ValueError("二维码或红包不存在")
        if qrcode.status != "created":
            raise ValueError("二维码状态不允许绑定")
        if packet.status != "idle":
            raise ValueError("红包已被使用")

        self.repo.create_binding(qrcode_id=qrcode_id, red_packet_id=red_packet_id)
        qrcode.status = "bound"
        packet.status = "bound"
        self.db.commit()

    def bind_auto(self, count: int) -> int:
        qrcodes = list(self.db.scalars(self.repo.query_unbound_qrcodes().limit(count)).all())
        packets = list(self.db.scalars(self.repo.query_idle_packets().limit(count)).all())
        amount = min(len(qrcodes), len(packets))

        for index in range(amount):
            qrcode = qrcodes[index]
            packet = packets[index]
            self.repo.create_binding(qrcode_id=qrcode.id, red_packet_id=packet.id)
            qrcode.status = "bound"
            packet.status = "bound"

        self.db.commit()
        return amount

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.binding import Binding
from app.models.qrcode import Qrcode
from app.models.red_packet import RedPacket


class BindingRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_binding(self, qrcode_id: int, red_packet_id: int) -> Binding:
        binding = Binding(qrcode_id=qrcode_id, red_packet_id=red_packet_id, status="active")
        self.db.add(binding)
        return binding

    def get_active_by_qrcode(self, qrcode_id: int) -> Binding | None:
        stmt = select(Binding).where(Binding.qrcode_id == qrcode_id, Binding.status == "active")
        return self.db.scalar(stmt)

    def query_unbound_qrcodes(self) -> Select[tuple[Qrcode]]:
        return select(Qrcode).where(Qrcode.status == "created").order_by(Qrcode.id.asc())

    def query_idle_packets(self) -> Select[tuple[RedPacket]]:
        return select(RedPacket).where(RedPacket.status == "idle").order_by(RedPacket.id.asc())

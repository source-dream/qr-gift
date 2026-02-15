import json
from datetime import datetime, timezone
from io import BytesIO
import random
from secrets import token_urlsafe

import qrcode
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_claim_content_token, hash_gift_token
from app.models.gift import GiftClaimLog
from app.models.red_packet import RedPacket
from app.repositories.gift_repository import GiftRepository
from app.services.system_config_service import get_runtime_storage_config
from app.storage.factory import get_storage


class GiftService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = GiftRepository(db)
        self.storage = get_storage(db)
        self.storage_runtime = get_runtime_storage_config(db)

    def create_gift(
        self,
        title: str,
        activate_at,
        expire_at,
        binding_mode: str,
        dispatch_strategy: str,
        red_packet_ids: list[int],
        style_type: str,
        host_base: str,
    ) -> tuple[int, str]:
        activate_at = self._to_utc(activate_at)
        expire_at = self._to_utc(expire_at)

        token = token_urlsafe(32)
        claim_url = self._build_claim_url(token, host_base)
        token_hash = hash_gift_token(token)
        image_data = self._render_qrcode(claim_url)
        object_key = self._build_object_key(token_hash)
        image_url = self.storage.upload_bytes(object_key, image_data, "image/png")

        gift = self.repo.create_gift(
            title=title,
            token_plain=token,
            token_hash=token_hash,
            activate_at=activate_at,
            expire_at=expire_at,
            binding_mode=binding_mode,
            dispatch_strategy=dispatch_strategy,
            style_type=style_type,
            style_config=json.dumps({"style_type": style_type}, ensure_ascii=False),
            image_url=image_url,
            object_key=object_key,
        )

        if binding_mode == "auto":
            packet = self.repo.get_idle_red_packet()
            if packet:
                self._bind_packet(gift.id, packet)
        else:
            if not red_packet_ids:
                raise ValueError("手动绑定模式下请至少选择一个红包")
            packets = self.repo.list_idle_red_packets_by_ids(red_packet_ids)
            if not packets:
                raise ValueError("所选红包不可用，请刷新后重试")
            for packet in packets:
                self._bind_packet(gift.id, packet)

        self.db.commit()
        return gift.id, claim_url

    def regenerate_gift_qrcode(self, gift_id: int, host_base: str) -> tuple[str, str]:
        gift = self.repo.get_gift(gift_id)
        if not gift:
            raise ValueError("礼物二维码不存在")
        if gift.status == "claimed":
            raise ValueError("已领取的礼物二维码不可重新生成")

        token = token_urlsafe(32)
        claim_url = self._build_claim_url(token, host_base)
        token_hash = hash_gift_token(token)
        image_data = self._render_qrcode(claim_url)
        object_key = self._build_object_key(token_hash)
        image_url = self.storage.upload_bytes(object_key, image_data, "image/png")

        if gift.object_key:
            try:
                self.storage.delete(gift.object_key)
            except Exception:
                pass

        gift.token_plain = token
        gift.token_hash = token_hash
        gift.image_url = image_url
        gift.object_key = object_key
        self.db.commit()
        return claim_url, image_url

    def claim_by_token(self, token: str, ip: str, ua: str, host_base: str) -> str:
        gift = self.repo.get_by_token_plain(token)
        if not gift:
            token_hash = hash_gift_token(token)
            gift = self.repo.get_by_token_hash(token_hash)
        if not gift:
            raise ValueError("礼物二维码不存在")

        now = datetime.now(tz=timezone.utc)
        activate_at = self._to_utc(gift.activate_at)
        expire_at = self._to_utc(gift.expire_at)

        if activate_at and now < activate_at:
            self._write_claim_log(gift.id, ip, ua, "rejected", "未到激活时间")
            raise ValueError("礼物尚未激活")
        if expire_at and now > expire_at:
            gift.status = "expired"
            self._write_claim_log(gift.id, ip, ua, "rejected", "已过期")
            self.db.commit()
            raise ValueError("礼物已过期")
        if gift.status == "claimed":
            self._write_claim_log(gift.id, ip, ua, "rejected", "该码已领取")
            raise ValueError("该礼物二维码已领取")
        if gift.status == "disabled":
            self._write_claim_log(gift.id, ip, ua, "rejected", "二维码已停用")
            raise ValueError("该礼物二维码已停用")

        bindings = self.repo.list_bindings(gift.id)
        if not bindings:
            self._write_claim_log(gift.id, ip, ua, "rejected", "未绑定红包")
            raise ValueError("当前礼物未绑定红包")

        packet = self._select_packet(gift.dispatch_strategy, bindings)
        if not packet:
            disabled_exists = False
            for binding in bindings:
                candidate = self.db.get(RedPacket, binding.red_packet_id)
                if candidate and candidate.status == "disabled":
                    disabled_exists = True
                    break
            if disabled_exists:
                self._write_claim_log(gift.id, ip, ua, "rejected", "红包已停用")
                raise ValueError("该礼物已失效")
            self._write_claim_log(gift.id, ip, ua, "rejected", "红包不存在")
            raise ValueError("红包记录不存在")

        # 中文注释：一经领取即写入已领取状态，确保每个码只能领取一次。
        gift.status = "claimed"
        for binding in bindings:
            binding.status = "claimed"
        packet.status = "claimed"
        self._write_claim_log(gift.id, ip, ua, "success", "", packet.id, gift.dispatch_strategy)
        self.db.commit()
        return self._resolve_claim_target(packet, host_base)

    def update_gift(
        self,
        gift_id: int,
        *,
        title: str,
        activate_at,
        expire_at,
        binding_mode: str,
        dispatch_strategy: str,
        red_packet_ids: list[int],
        style_type: str,
    ) -> None:
        gift = self.repo.get_gift(gift_id)
        if not gift:
            raise ValueError("礼物二维码不存在")
        if gift.status == "claimed":
            raise ValueError("该礼物二维码已领取，不可修改绑定")

        gift.title = title.strip()
        gift.activate_at = self._to_utc(activate_at)
        gift.expire_at = self._to_utc(expire_at)
        gift.binding_mode = binding_mode
        gift.dispatch_strategy = dispatch_strategy
        gift.style_type = style_type
        gift.style_config = json.dumps({"style_type": style_type}, ensure_ascii=False)

        self._sync_bindings(
            gift_id=gift.id, binding_mode=binding_mode, red_packet_ids=red_packet_ids
        )
        self.db.commit()

    def delete_gift(self, gift_id: int) -> None:
        gift = self.repo.get_gift(gift_id)
        if not gift:
            raise ValueError("礼物二维码不存在")
        if gift.status == "claimed":
            raise ValueError("已领取的礼物二维码不可删除")

        bindings = self.repo.list_bindings(gift.id)
        for binding in bindings:
            packet = self.db.get(RedPacket, binding.red_packet_id)
            if packet and packet.status == "bound":
                packet.status = "idle"
            self.repo.remove_binding(binding)

        self.repo.delete_gift(gift)
        self.db.commit()

    def _sync_bindings(self, gift_id: int, binding_mode: str, red_packet_ids: list[int]) -> None:
        current_bindings = self.repo.list_bindings(gift_id)
        current_by_packet = {item.red_packet_id: item for item in current_bindings}
        current_ids = set(current_by_packet.keys())

        if binding_mode == "auto":
            if current_ids:
                # 中文注释：自动模式只保留一条未领取绑定，避免重复派发来源。
                keep_id = min(current_ids)
            else:
                packet = self.repo.get_idle_red_packet()
                if not packet:
                    raise ValueError("当前没有可自动绑定的红包")
                keep_id = packet.id
            target_ids = {keep_id}
        else:
            unique_ids = list(dict.fromkeys(red_packet_ids))
            if not unique_ids:
                raise ValueError("手动绑定模式下请至少选择一个红包")
            packets = self.repo.list_red_packets_by_ids(unique_ids)
            packet_map = {item.id: item for item in packets}
            if len(packet_map) != len(unique_ids):
                raise ValueError("存在无效红包，请刷新后重试")
            target_ids = set(unique_ids)

            for packet_id in target_ids:
                packet = packet_map[packet_id]
                if packet.status == "claimed":
                    raise ValueError(f"红包 {packet_id} 已领取，不能绑定")
                if packet.status == "bound" and packet_id not in current_ids:
                    raise ValueError(f"红包 {packet_id} 已被其他礼物绑定")

        to_remove = current_ids - target_ids
        to_add = target_ids - current_ids

        for packet_id in to_remove:
            binding = current_by_packet.get(packet_id)
            if binding:
                self.repo.remove_binding(binding)
            packet = self.db.get(RedPacket, packet_id)
            if packet and packet.status == "bound":
                packet.status = "idle"

        for packet_id in to_add:
            packet = self.db.get(RedPacket, packet_id)
            if not packet:
                raise ValueError(f"红包 {packet_id} 不存在")
            if packet.status == "claimed":
                raise ValueError(f"红包 {packet_id} 已领取，不能绑定")
            if packet.status == "bound":
                active_binding = self.repo.get_active_binding_by_packet_id(packet_id)
                if active_binding and active_binding.gift_qrcode_id != gift_id:
                    raise ValueError(f"红包 {packet_id} 已被其他礼物绑定")
            self.repo.bind_red_packet(gift_id, packet_id)
            packet.status = "bound"

    @staticmethod
    def _resolve_claim_target(packet: RedPacket, host_base: str) -> str:
        content_type = (packet.content_type or "url").strip()
        if content_type == "url":
            return packet.content_value or packet.claim_url
        ticket = create_claim_content_token(packet.id)
        base = host_base.rstrip("/")
        return f"{base}/claim/content?ticket={ticket}"

    def _bind_packet(self, gift_id: int, packet: RedPacket) -> None:
        if packet.status != "idle":
            return
        self.repo.bind_red_packet(gift_id, packet.id)
        packet.status = "bound"

    def _select_packet(self, strategy: str, bindings) -> RedPacket | None:
        packet_list: list[RedPacket] = []
        for binding in bindings:
            packet = self.db.get(RedPacket, binding.red_packet_id)
            if packet and packet.status in {"idle", "bound"}:
                packet_list.append(packet)
        if not packet_list:
            return None

        if strategy == "amount_desc":
            return max(packet_list, key=lambda x: float(x.amount))
        if strategy == "level_desc":
            return max(packet_list, key=lambda x: (x.level, float(x.amount)))
        return random.choice(packet_list)

    def _write_claim_log(
        self,
        gift_qrcode_id: int,
        ip: str,
        ua: str,
        result: str,
        reason: str,
        red_packet_id: int | None = None,
        dispatch_strategy: str = "",
    ) -> None:
        self.db.add(
            GiftClaimLog(
                gift_qrcode_id=gift_qrcode_id,
                red_packet_id=red_packet_id,
                dispatch_strategy=dispatch_strategy,
                ip=ip,
                ua=ua,
                result=result,
                reason=reason,
            )
        )

    @staticmethod
    def _render_qrcode(content: str) -> bytes:
        qr = qrcode.QRCode(border=2, box_size=10)
        qr.add_data(content)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        image.save(buffer, "PNG")
        return buffer.getvalue()

    @staticmethod
    def _build_claim_url(token: str, fallback_base: str) -> str:
        settings = get_settings()
        preferred_base = fallback_base.strip().rstrip("/")
        configured_base = settings.frontend_base_url.strip().rstrip("/")
        base = preferred_base or configured_base
        return f"{base}/r/{token}"

    def _build_object_key(self, token_hash: str) -> str:
        now = datetime.now()
        relative = f"gifts/{now:%Y}/{now:%m}/{token_hash[:16]}.png"
        prefix = self.storage_runtime.storage_prefix.strip().strip("/")
        if not prefix:
            return relative
        return f"{prefix}/{relative}"

    @staticmethod
    def _to_utc(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

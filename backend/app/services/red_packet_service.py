import csv
from datetime import datetime
from io import StringIO
import json
import re
from typing import Any
from urllib.parse import urlparse

import cv2
from fastapi import UploadFile
import numpy as np
from sqlalchemy.orm import Session

from app.repositories.red_packet_repository import RedPacketRepository
from app.services.system_config_service import get_runtime_storage_config
from app.storage.factory import get_storage


class RedPacketService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = RedPacketRepository(db)
        self.storage = get_storage(db)
        self.storage_runtime = get_runtime_storage_config(db)

    def ensure_builtin_categories(self) -> None:
        builtins = [
            ("支付宝红包", "alipay_red_packet", "url,qr_image"),
            ("账号", "account", "text,url"),
            ("其他", "misc", "url,text,qr_image"),
        ]
        changed = False
        for name, code, allowed in builtins:
            existing = self.repo.get_category_by_code(code)
            if existing:
                if existing.allowed_content_types != allowed:
                    existing.allowed_content_types = allowed
                    changed = True
                continue
            self.repo.create_category(
                name=name,
                code=code,
                is_builtin=True,
                allowed_content_types=allowed,
            )
            changed = True
        if changed:
            self.db.commit()

    def list_categories(self):
        self.ensure_builtin_categories()
        return self.repo.list_categories()

    def create_custom_category(self, name: str):
        self.ensure_builtin_categories()
        normalized = name.strip()
        if not normalized:
            raise ValueError("分类名称不能为空")
        existed = self.repo.get_category_by_name(normalized)
        if existed:
            return existed
        code = self._build_custom_category_code(normalized)
        collision = self.repo.get_category_by_code(code)
        if collision:
            code = f"{code}-{int(datetime.now().timestamp())}"
        category = self.repo.create_category(
            name=normalized,
            code=code,
            is_builtin=False,
            allowed_content_types="url",
        )
        self.db.commit()
        return category

    def create_red_packet(
        self,
        *,
        title: str,
        amount: float,
        level: int,
        category_code: str | None,
        custom_category_name: str | None,
        content_type: str,
        content_value: str,
        tags: list[str],
        meta: dict[str, str],
        available_from,
        available_to,
        content_image_url: str = "",
        content_image_key: str = "",
        batch_source: str = "manual",
    ) -> None:
        self.ensure_builtin_categories()
        category = self._resolve_category(category_code, custom_category_name, content_type)
        normalized_content_value = content_value.strip()
        if content_type == "url" and not normalized_content_value:
            raise ValueError("链接内容不能为空")
        if content_type == "text" and not normalized_content_value:
            raise ValueError("文本内容不能为空")
        if content_type == "qr_image" and not content_image_url:
            raise ValueError("二维码图片不能为空")

        batch_no = f"RP{datetime.now().strftime('%Y%m%d%H%M%S')}"
        batch = self.repo.create_batch(batch_no=batch_no, source=batch_source)
        item = self.repo.create_item(
            batch_id=batch.id,
            title=title.strip(),
            amount=float(amount),
            level=level,
            content_type=content_type,
            content_value=normalized_content_value,
            content_image_url=content_image_url,
            content_image_key=content_image_key,
            category_id=category.id,
            meta_json=json.dumps(meta, ensure_ascii=False),
            available_from=self._parse_dt(available_from),
            available_to=self._parse_dt(available_to),
        )
        self._bind_tags(item.id, tags)
        self.db.commit()

    def import_csv(self, content: bytes) -> tuple[str, int]:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(StringIO(text))
        self.ensure_builtin_categories()
        misc = self.repo.get_category_by_code("misc")
        if not misc:
            raise ValueError("默认分类初始化失败")

        batch_no = f"RP{datetime.now().strftime('%Y%m%d%H%M%S')}"
        batch = self.repo.create_batch(batch_no=batch_no, source="csv")

        count = 0
        for row in reader:
            claim_url = (row.get("claim_url") or row.get("content_value") or "").strip()
            amount = float((row.get("amount") or "0").strip())
            level = int((row.get("level") or "1").strip())
            title = (row.get("title") or f"红包{count + 1}").strip()
            available_from = self._parse_dt(row.get("available_from"))
            available_to = self._parse_dt(row.get("available_to"))
            if not claim_url:
                continue
            self.repo.create_item(
                batch_id=batch.id,
                title=title,
                amount=amount,
                level=level,
                content_type="url",
                content_value=claim_url,
                category_id=misc.id,
                meta_json="{}",
                available_from=available_from,
                available_to=available_to,
            )
            count += 1

        self.db.commit()
        return batch_no, count

    async def import_image_files(
        self,
        *,
        files: list[UploadFile],
        title_prefix: str,
        amount: float,
        level: int,
        category_code: str | None,
        tags: list[str],
    ) -> tuple[str, int]:
        self.ensure_builtin_categories()
        category = self._resolve_category(category_code, None, "qr_image")
        batch_no = f"RP{datetime.now().strftime('%Y%m%d%H%M%S')}"
        batch = self.repo.create_batch(batch_no=batch_no, source="image")

        count = 0
        for index, upload in enumerate(files, start=1):
            filename = upload.filename or f"image-{index}.png"
            raw = await upload.read()
            if not raw:
                continue
            title = f"{title_prefix}-{index}" if title_prefix else f"支付宝红包-{index}"

            if category.code == "alipay_red_packet":
                decoded_url = self._decode_qrcode_url(raw)
                if not decoded_url:
                    continue
                item = self.repo.create_item(
                    batch_id=batch.id,
                    title=title,
                    amount=float(amount),
                    level=level,
                    content_type="url",
                    content_value=decoded_url,
                    content_image_url="",
                    content_image_key="",
                    category_id=category.id,
                    meta_json="{}",
                )
                self._bind_tags(item.id, tags)
                count += 1
                continue

            key = self._build_object_key(filename)
            image_url = self.storage.upload_bytes(key, raw, upload.content_type or "image/png")
            item = self.repo.create_item(
                batch_id=batch.id,
                title=title,
                amount=float(amount),
                level=level,
                content_type="qr_image",
                content_value="",
                content_image_url=image_url,
                content_image_key=key,
                category_id=category.id,
                meta_json="{}",
            )
            self._bind_tags(item.id, tags)
            count += 1

        self.db.commit()
        return batch_no, count

    async def parse_image_files_to_urls(
        self, files: list[UploadFile]
    ) -> tuple[int, int, list[dict[str, str]]]:
        results: list[dict[str, str]] = []
        success = 0
        failed = 0
        for index, upload in enumerate(files, start=1):
            filename = upload.filename or f"image-{index}.png"
            raw = await upload.read()
            if not raw:
                failed += 1
                results.append({"filename": filename, "status": "failed", "decoded_url": ""})
                continue
            decoded_url = self._decode_qrcode_url(raw)
            if not decoded_url:
                failed += 1
                results.append({"filename": filename, "status": "failed", "decoded_url": ""})
                continue
            success += 1
            results.append({"filename": filename, "status": "success", "decoded_url": decoded_url})
        return success, failed, results

    def import_urls(
        self,
        *,
        urls: list[dict[str, str]],
        title_prefix: str,
        amount: float,
        level: int,
        category_code: str | None,
        tags: list[str],
        available_from,
        available_to,
    ) -> tuple[str, int]:
        self.ensure_builtin_categories()
        category = self._resolve_category(category_code, None, "url")
        batch_no = f"RP{datetime.now().strftime('%Y%m%d%H%M%S')}"
        batch = self.repo.create_batch(batch_no=batch_no, source="image-parse")

        count = 0
        for index, row in enumerate(urls, start=1):
            candidate_url = (row.get("url") or "").strip()
            if not candidate_url or not self._is_valid_url(candidate_url):
                continue
            source_name = (row.get("filename") or "").strip()
            title = f"{title_prefix}-{index}" if title_prefix else f"支付宝红包-{index}"
            if source_name:
                title = f"{title_prefix}-{source_name}" if title_prefix else source_name
            item = self.repo.create_item(
                batch_id=batch.id,
                title=title[:120],
                amount=float(amount),
                level=level,
                content_type="url",
                content_value=candidate_url,
                content_image_url="",
                content_image_key="",
                category_id=category.id,
                meta_json="{}",
                available_from=self._parse_dt(available_from),
                available_to=self._parse_dt(available_to),
            )
            self._bind_tags(item.id, tags)
            count += 1

        self.db.commit()
        return batch_no, count

    @staticmethod
    def _decode_qrcode_url(raw: bytes) -> str | None:
        matrix = np.frombuffer(raw, dtype=np.uint8)
        image = cv2.imdecode(matrix, cv2.IMREAD_COLOR)
        if image is None:
            return None

        detector = cv2.QRCodeDetector()
        text, _, _ = detector.detectAndDecode(image)
        candidate = text.strip() if isinstance(text, str) else ""

        if not candidate and hasattr(detector, "detectAndDecodeMulti"):
            try:
                ok, decoded_info, _, _ = detector.detectAndDecodeMulti(image)
            except Exception:
                ok = False
                decoded_info = []
            if ok and decoded_info:
                for item in decoded_info:
                    next_candidate = (item or "").strip()
                    if next_candidate:
                        candidate = next_candidate
                        break

        if not candidate:
            return None
        if not RedPacketService._is_valid_url(candidate):
            return None
        return candidate

    @staticmethod
    def _is_valid_url(value: str) -> bool:
        try:
            parsed = urlparse(value)
        except Exception:
            return False
        if parsed.scheme not in {"http", "https", "alipays"}:
            return False
        if parsed.scheme in {"http", "https"} and not parsed.netloc:
            return False
        return True

    def _resolve_category(
        self, category_code: str | None, custom_category_name: str | None, content_type: str
    ):
        if custom_category_name and custom_category_name.strip():
            category = self.create_custom_category(custom_category_name)
        elif category_code:
            category = self.repo.get_category_by_code(category_code.strip())
        else:
            category = self.repo.get_category_by_code("misc")

        if not category:
            raise ValueError("分类不存在")

        allowed = {
            item.strip() for item in category.allowed_content_types.split(",") if item.strip()
        }
        if content_type not in allowed:
            raise ValueError("该分类不支持当前内容类型")
        if not category.is_builtin and content_type != "url":
            raise ValueError("自定义分类仅支持链接类型")
        return category

    def _bind_tags(self, red_packet_id: int, tags: list[str]) -> None:
        normalized_tags: list[str] = []
        seen: set[str] = set()
        for raw in tags:
            name = raw.strip()
            if not name:
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized_tags.append(name[:50])

        for name in normalized_tags:
            tag = self.repo.get_tag_by_name(name)
            if not tag:
                tag = self.repo.create_tag(name)
            self.repo.bind_tag(red_packet_id, tag.id)

    def _build_object_key(self, filename: str) -> str:
        now = datetime.now()
        clean_name = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
        relative = f"red-packets/{now:%Y}/{now:%m}/{int(now.timestamp())}-{clean_name}"
        prefix = self.storage_runtime.storage_prefix.strip().strip("/")
        if not prefix:
            return relative
        return f"{prefix}/{relative}"

    @staticmethod
    def _parse_dt(raw: Any):
        if raw is None:
            return None
        if isinstance(raw, datetime):
            return raw
        value = str(raw).strip()
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _build_custom_category_code(name: str) -> str:
        collapsed = re.sub(r"\s+", "-", name.strip().lower())
        base = re.sub(r"[^a-z0-9_-]", "", collapsed)
        if not base:
            base = "custom"
        return f"custom-{base[:40]}"

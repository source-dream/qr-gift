import csv
from datetime import datetime
from io import BytesIO, StringIO
import zipfile

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.response import ok
from app.models.user import User
from app.repositories.qrcode_repository import QrcodeRepository
from app.schemas.qrcode import CreateBatchRequest, QrcodeBatchResponse, QrcodeItem
from app.services.qrcode_service import QrcodeService
from app.storage.factory import get_storage
from app.core.database import get_db

router = APIRouter(prefix="/api/qrcodes", tags=["qrcode"])


@router.post("/batches")
def create_batch(
    payload: CreateBatchRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    try:
        batch_no = QrcodeService(db).create_batch(payload.amount)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"二维码生成失败: {exc}") from exc
    return ok(
        QrcodeBatchResponse(batch_no=batch_no, amount=payload.amount).model_dump(), "创建成功"
    )


@router.get("")
def list_qrcodes(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    records = QrcodeRepository(db).list_qrcodes()
    data = [
        QrcodeItem(
            id=item.id,
            short_code=item.short_code,
            status=item.status,
            image_url=item.image_url,
        ).model_dump()
        for item in records
    ]
    return ok(data)


@router.get("/export")
def export_qrcodes_csv(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    records = QrcodeRepository(db).list_qrcodes(limit=50000)

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "short_code", "status", "image_url"])
    for item in records:
        writer.writerow([item.id, item.short_code, item.status, item.image_url])

    output.seek(0)
    # 中文注释：先提供 CSV 导出，确保用户能快速批量核对二维码状态与链接，后续再扩展图片压缩包导出。
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="qrcodes_export.csv"'},
    )


@router.get("/export/images")
def export_qrcode_images_zip(
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    records = QrcodeRepository(db).list_qrcodes(limit=limit)
    storage = get_storage(db)
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        manifest = StringIO()
        writer = csv.writer(manifest)
        writer.writerow(["id", "short_code", "status", "object_key", "included"])

        for item in records:
            included = "no"
            if item.object_key:
                try:
                    image_data = storage.download_bytes(item.object_key)
                    archive.writestr(f"qrcodes/{item.short_code}.png", image_data)
                    included = "yes"
                except Exception:
                    included = "no"
            writer.writerow([item.id, item.short_code, item.status, item.object_key, included])

        archive.writestr("manifest.csv", manifest.getvalue())

    zip_buffer.seek(0)
    filename = f"qrcodes_images_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

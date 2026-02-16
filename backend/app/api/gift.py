from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from urllib.parse import urlparse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import ok
from app.models.user import User
from app.repositories.gift_repository import GiftRepository
from app.schemas.gift import (
    CreateGiftRequest,
    CreateGiftResponse,
    GiftDetail,
    GiftItem,
    UpdateGiftRequest,
)
from app.services.gift_service import GiftService
from app.services.system_config_service import get_runtime_storage_channels
from app.storage.factory import create_storage_from_channel

router = APIRouter(prefix="/api/gifts", tags=["gifts"])


def _resolve_public_web_base(request: Request) -> str:
    # 中文注释：优先使用前端显式传入的 Web Origin，确保二维码地址与当前访问入口一致。
    candidates = [
        request.headers.get("x-web-origin", ""),
        request.headers.get("origin", ""),
        "",
    ]

    referer = request.headers.get("referer", "")
    if referer:
        try:
            parsed = urlparse(referer)
            if parsed.scheme and parsed.netloc:
                candidates.append(f"{parsed.scheme}://{parsed.netloc}")
        except Exception:
            pass

    for raw in candidates:
        base = raw.strip().rstrip("/")
        if not base:
            continue
        parsed = urlparse(base)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        return f"{parsed.scheme}://{parsed.netloc}"

    return str(request.base_url).rstrip("/")


@router.post("")
def create_gift(
    payload: CreateGiftRequest,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    try:
        gift_id, claim_url = GiftService(db).create_gift(
            title=payload.title,
            activate_at=payload.activate_at,
            expire_at=payload.expire_at,
            binding_mode=payload.binding_mode,
            dispatch_strategy=payload.dispatch_strategy,
            red_packet_ids=payload.red_packet_ids,
            style_type=payload.style_type,
            host_base=_resolve_public_web_base(request),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"创建礼物二维码失败: {exc}") from exc

    return ok(
        CreateGiftResponse(id=gift_id, title=payload.title, claim_url=claim_url).model_dump(),
        "创建成功",
    )


@router.get("")
def list_gifts(
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    repo = GiftRepository(db)
    items = repo.list_gifts()
    host_base = _resolve_public_web_base(request)
    data = [
        GiftItem(
            id=item.id,
            title=item.title,
            status=item.status,
            activate_at=item.activate_at,
            expire_at=item.expire_at,
            binding_mode=item.binding_mode,
            dispatch_strategy=item.dispatch_strategy,
            binding_count=len(repo.list_bindings(item.id)),
            style_type=item.style_type,
            image_url=item.image_url,
            claim_url=f"{host_base}/r/{item.token_plain}" if item.token_plain else "",
        ).model_dump()
        for item in items
    ]
    return ok(data)


@router.get("/{gift_id}")
def get_gift_detail(
    gift_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    repo = GiftRepository(db)
    gift = repo.get_gift(gift_id)
    if not gift:
        raise HTTPException(status_code=404, detail="礼物二维码不存在")
    bindings = repo.list_bindings(gift.id)
    host_base = _resolve_public_web_base(request)
    return ok(
        GiftDetail(
            id=gift.id,
            title=gift.title,
            status=gift.status,
            activate_at=gift.activate_at,
            expire_at=gift.expire_at,
            binding_mode=gift.binding_mode,
            dispatch_strategy=gift.dispatch_strategy,
            style_type=gift.style_type,
            image_url=gift.image_url,
            claim_url=f"{host_base}/r/{gift.token_plain}" if gift.token_plain else "",
            red_packet_ids=[item.red_packet_id for item in bindings],
        ).model_dump()
    )


@router.put("/{gift_id}")
def update_gift(
    gift_id: int,
    payload: UpdateGiftRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    try:
        GiftService(db).update_gift(
            gift_id,
            title=payload.title,
            activate_at=payload.activate_at,
            expire_at=payload.expire_at,
            binding_mode=payload.binding_mode,
            dispatch_strategy=payload.dispatch_strategy,
            red_packet_ids=payload.red_packet_ids,
            style_type=payload.style_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(message="更新成功")


@router.post("/{gift_id}/activate")
def activate_gift(
    gift_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    gift = GiftRepository(db).get_gift(gift_id)
    if not gift:
        raise HTTPException(status_code=404, detail="礼物二维码不存在")
    gift.status = "active"
    db.commit()
    return ok(message="已启用")


@router.post("/{gift_id}/disable")
def disable_gift(
    gift_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    gift = GiftRepository(db).get_gift(gift_id)
    if not gift:
        raise HTTPException(status_code=404, detail="礼物二维码不存在")
    gift.status = "disabled"
    db.commit()
    return ok(message="已停用")


@router.delete("/{gift_id}")
def delete_gift(
    gift_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    try:
        GiftService(db).delete_gift(gift_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(message="已删除")


@router.post("/{gift_id}/regenerate-qrcode")
def regenerate_gift_qrcode(
    gift_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    try:
        claim_url, _image_url = GiftService(db).regenerate_gift_qrcode(
            gift_id=gift_id,
            host_base=_resolve_public_web_base(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok({"claim_url": claim_url, "image_url": ""}, "二维码已重新生成")


@router.get("/{gift_id}/qrcode.png")
def download_gift_qrcode(
    gift_id: int,
    request: Request,
    download: int = 0,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    gift = GiftRepository(db).get_gift(gift_id)
    if not gift:
        raise HTTPException(status_code=404, detail="礼物二维码不存在")
    if not gift.object_key:
        raise HTTPException(status_code=400, detail="该礼物二维码缺少存储对象，请重新生成")

    channels = get_runtime_storage_channels(db)
    channel = next((item for item in channels if item.id == gift.storage_channel_id), None)
    if not channel:
        raise HTTPException(status_code=400, detail="当前二维码存储渠道不可用，请重新生成")
    storage = create_storage_from_channel(channel)
    try:
        image = storage.download_bytes(gift.object_key)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"二维码下载失败: {exc}") from exc

    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="gift-qrcode-{gift_id}.png"'
    return Response(content=image, media_type="image/png", headers=headers)


@router.get("/{gift_id}/qrcode-download-url")
def get_gift_qrcode_download_url(
    gift_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    gift = GiftRepository(db).get_gift(gift_id)
    if not gift:
        raise HTTPException(status_code=404, detail="礼物二维码不存在")
    if not gift.object_key:
        raise HTTPException(status_code=400, detail="该礼物二维码缺少存储对象，请重新生成")

    channels = get_runtime_storage_channels(db)
    channel = next((item for item in channels if item.id == gift.storage_channel_id), None)
    if not channel or channel.provider == "local":
        base = _resolve_public_web_base(request)
        return ok({"url": f"{base}/api/gifts/{gift_id}/qrcode.png?download=1"})

    storage = create_storage_from_channel(channel)
    try:
        url = storage.generate_presigned_url(gift.object_key, expires=600)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"下载链接生成失败: {exc}") from exc
    if url.startswith("local://"):
        base = _resolve_public_web_base(request)
        return ok({"url": f"{base}/api/gifts/{gift_id}/qrcode.png?download=1"})
    return ok({"url": url})

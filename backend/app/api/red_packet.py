import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.response import ok
from app.models.user import User
from app.repositories.red_packet_repository import RedPacketRepository
from app.schemas.red_packet import (
    BatchImportUrlsRequest,
    CreateCategoryRequest,
    CreateRedPacketRequest,
    ParseImageResult,
    ParseImagesResponse,
    RedPacketCategoryItem,
    RedPacketImportResponse,
    RedPacketItem,
    UpdateRedPacketRequest,
)
from app.services.red_packet_service import RedPacketService

router = APIRouter(prefix="/api/red-packets", tags=["red-packets"])


@router.get("/categories")
def list_categories(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    service = RedPacketService(db)
    categories = service.list_categories()
    data = [
        RedPacketCategoryItem(
            id=item.id,
            name=item.name,
            code=item.code,
            is_builtin=item.is_builtin,
            allowed_content_types=[
                value.strip() for value in item.allowed_content_types.split(",") if value.strip()
            ],
        ).model_dump()
        for item in categories
    ]
    return ok(data)


@router.post("/categories")
def create_category(
    payload: CreateCategoryRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    try:
        category = RedPacketService(db).create_custom_category(payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(
        RedPacketCategoryItem(
            id=category.id,
            name=category.name,
            code=category.code,
            is_builtin=category.is_builtin,
            allowed_content_types=[
                value.strip()
                for value in category.allowed_content_types.split(",")
                if value.strip()
            ],
        ).model_dump(),
        "创建分类成功",
    )


@router.post("")
def create_red_packet(
    payload: CreateRedPacketRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    try:
        RedPacketService(db).create_red_packet(
            title=payload.title,
            amount=payload.amount,
            level=payload.level,
            category_code=payload.category_code,
            custom_category_name=payload.custom_category_name,
            content_type=payload.content_type,
            content_value=payload.content_value,
            tags=payload.tags,
            meta=payload.meta,
            available_from=payload.available_from,
            available_to=payload.available_to,
            batch_source="manual",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"创建红包失败: {exc}") from exc
    return ok(message="创建成功")


@router.post("/batch-images")
async def batch_import_images(
    files: list[UploadFile] = File(...),
    title_prefix: str = Form(default="支付宝红包"),
    amount: float = Form(default=0),
    level: int = Form(default=1),
    category_code: str | None = Form(default="alipay_red_packet"),
    tags: str = Form(default=""),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一张图片")
    tag_list = [item.strip() for item in tags.split(",") if item.strip()]
    try:
        batch_no, imported_count = await RedPacketService(db).import_image_files(
            files=files,
            title_prefix=title_prefix,
            amount=amount,
            level=level,
            category_code=category_code,
            tags=tag_list,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"图片导入失败: {exc}") from exc
    return ok(
        RedPacketImportResponse(batch_no=batch_no, imported_count=imported_count).model_dump(),
        "导入成功",
    )


@router.post("/parse-images-to-urls")
async def parse_images_to_urls(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="请至少上传一张图片")
    success_count, failed_count, results = await RedPacketService(db).parse_image_files_to_urls(
        files
    )
    payload = ParseImagesResponse(
        success_count=success_count,
        failed_count=failed_count,
        results=[ParseImageResult(**item) for item in results],
    )
    return ok(payload.model_dump(), "解析完成")


@router.post("/batch-urls")
def batch_import_urls(
    payload: BatchImportUrlsRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    if not payload.urls:
        raise HTTPException(status_code=400, detail="请先解析得到链接后再导入")
    rows = [{"filename": item.filename, "url": item.url} for item in payload.urls]
    try:
        batch_no, imported_count = RedPacketService(db).import_urls(
            urls=rows,
            title_prefix=payload.title_prefix,
            amount=payload.amount,
            level=payload.level,
            category_code=payload.category_code,
            tags=payload.tags,
            available_from=payload.available_from,
            available_to=payload.available_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"链接导入失败: {exc}") from exc

    return ok(
        RedPacketImportResponse(batch_no=batch_no, imported_count=imported_count).model_dump(),
        "导入成功",
    )


@router.post("/import")
async def import_csv_compat(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="仅支持 CSV 文件")
    content = await file.read()
    batch_no, imported_count = RedPacketService(db).import_csv(content)
    response = RedPacketImportResponse(batch_no=batch_no, imported_count=imported_count)
    return ok(response.model_dump(), "导入成功")


@router.get("")
def list_red_packets(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    service = RedPacketService(db)
    service.ensure_builtin_categories()
    repo = RedPacketRepository(db)
    items = repo.list_items()

    category_ids = {item.category_id for item in items if item.category_id is not None}
    category_map = repo.get_categories_map({int(item_id) for item_id in category_ids})
    tag_map = repo.get_tags_map({item.id for item in items})

    data = []
    for item in items:
        category = category_map.get(item.category_id or 0)
        try:
            meta = json.loads(item.meta_json or "{}")
            if not isinstance(meta, dict):
                meta = {}
        except Exception:
            meta = {}
        data.append(
            RedPacketItem(
                id=item.id,
                title=item.title,
                amount=float(item.amount),
                level=item.level,
                category_name=category.name if category else "未分类",
                category_code=category.code if category else "",
                tags=tag_map.get(item.id, []),
                content_type=item.content_type,
                content_value=item.content_value or item.claim_url,
                content_image_url=item.content_image_url,
                status=item.status,
                meta={str(k): str(v) for k, v in meta.items()},
                available_from=item.available_from,
                available_to=item.available_to,
            ).model_dump()
        )
    return ok(data)


@router.put("/{red_packet_id}")
def update_red_packet(
    red_packet_id: int,
    payload: UpdateRedPacketRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    repo = RedPacketRepository(db)
    item = repo.get_item(red_packet_id)
    if not item:
        raise HTTPException(status_code=404, detail="礼物记录不存在")
    if item.status == "claimed":
        raise HTTPException(status_code=400, detail="已领取记录不可编辑")
    if item.status == "deleted":
        raise HTTPException(status_code=400, detail="已删除记录不可编辑")

    item.title = payload.title.strip()
    item.amount = float(payload.amount)
    item.level = payload.level
    item.available_from = payload.available_from
    item.available_to = payload.available_to
    if item.content_type == "url":
        normalized_url = payload.content_value.strip()
        if not normalized_url:
            raise HTTPException(status_code=400, detail="链接不能为空")
        item.content_value = normalized_url
        item.claim_url = normalized_url
    db.commit()
    return ok(message="更新成功")


@router.post("/{red_packet_id}/disable")
def disable_red_packet(
    red_packet_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    repo = RedPacketRepository(db)
    item = repo.get_item(red_packet_id)
    if not item:
        raise HTTPException(status_code=404, detail="礼物记录不存在")
    if item.status == "claimed":
        raise HTTPException(status_code=400, detail="已领取记录不可停用")
    if item.status == "deleted":
        raise HTTPException(status_code=400, detail="已删除记录不可停用")
    item.status = "disabled"
    db.commit()
    return ok(message="已停用")


@router.post("/{red_packet_id}/enable")
def enable_red_packet(
    red_packet_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    repo = RedPacketRepository(db)
    item = repo.get_item(red_packet_id)
    if not item:
        raise HTTPException(status_code=404, detail="礼物记录不存在")
    if item.status == "claimed":
        raise HTTPException(status_code=400, detail="已领取记录不可启用")
    if item.status == "deleted":
        raise HTTPException(status_code=400, detail="已删除记录不可启用")

    bindings = repo.list_active_gift_bindings(item.id)
    item.status = "bound" if bindings else "idle"
    db.commit()
    return ok(message="已启用")


@router.delete("/{red_packet_id}")
def delete_red_packet(
    red_packet_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    repo = RedPacketRepository(db)
    item = repo.get_item(red_packet_id)
    if not item:
        raise HTTPException(status_code=404, detail="礼物记录不存在")

    if item.status == "claimed":
        # 中文注释：已领取记录改为逻辑删除，避免破坏历史领取日志关联。
        item.status = "deleted"
        db.commit()
        return ok(message="已标记删除（日志保留）")

    bindings = repo.list_active_gift_bindings(item.id)
    for binding in bindings:
        repo.db.delete(binding)
    repo.delete_item(item)
    db.commit()
    return ok(message="已自动解绑并删除")

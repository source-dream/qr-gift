import html
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_claim_content_token
from app.models.red_packet import RedPacket, RedPacketCategory
from app.services.gift_service import GiftService
from app.services.system_config_service import get_claim_contact_text

router = APIRouter(tags=["redirect"])


@router.get("/r/{gift_token}")
def gift_redirect(gift_token: str, request: Request, db: Session = Depends(get_db)):
    try:
        target_url = GiftService(db).claim_by_token(
            token=gift_token,
            ip=request.client.host if request.client else "",
            ua=request.headers.get("user-agent", ""),
            host_base=str(request.base_url),
        )
    except ValueError as exc:
        detail = str(exc)
        if detail in {"该礼物已失效", "该礼物二维码已停用"}:
            return _render_invalid_page(detail, get_claim_contact_text(db))
        raise HTTPException(status_code=400, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"领取处理异常: {exc}") from exc

    return RedirectResponse(url=target_url, status_code=302)


def _render_invalid_page(reason: str, contact_text: str) -> HTMLResponse:
    html_doc = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>礼物已失效</title>
  <style>
    body {{ font-family: sans-serif; margin: 0; padding: 24px; background: #fff6ef; color: #2b241f; }}
    .card {{ max-width: 560px; margin: 0 auto; background: #fff; border-radius: 14px; padding: 18px; box-shadow: 0 8px 30px rgba(0,0,0,0.08); }}
    .title {{ margin: 0 0 10px; font-size: 22px; color: #c04729; }}
    .reason {{ margin: 0; color: #7b695d; }}
    .contact {{ border-radius: 10px; background: #fff1e6; margin-top: 14px; padding: 10px; }}
    .contact-title {{ margin: 0 0 6px; color: #7b695d; font-size: 13px; }}
    .contact-text {{ margin: 0; line-height: 1.6; white-space: pre-wrap; }}
  </style>
</head>
<body>
  <div class="card">
    <h1 class="title">该礼物已失效</h1>
    <p class="reason">{html.escape(reason)}</p>
    <div class="contact">
      <p class="contact-title">联系方式</p>
      <p class="contact-text">{html.escape(contact_text)}</p>
    </div>
  </div>
</body>
</html>
"""
    return HTMLResponse(content=html_doc, status_code=200)


@router.get("/claim/content")
def claim_content(ticket: str, db: Session = Depends(get_db)):
    try:
        red_packet_id = verify_claim_content_token(ticket)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"内容凭证无效: {exc}") from exc

    packet = db.get(RedPacket, red_packet_id)
    if not packet:
        raise HTTPException(status_code=404, detail="内容不存在")
    category_name = "内容"
    if packet.category_id:
        category = db.get(RedPacketCategory, packet.category_id)
        if category and category.name:
            category_name = category.name

    content_type = (packet.content_type or "").strip()
    if content_type == "url":
        target = packet.content_value or packet.claim_url
        if not target:
            raise HTTPException(status_code=400, detail="链接内容为空")
        return RedirectResponse(url=target, status_code=302)

    if content_type == "qr_image":
        image_url = packet.content_image_url
        if not image_url:
            raise HTTPException(status_code=400, detail="图片内容为空")
        html_doc = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(category_name)}内容</title>
  <style>
    body {{ font-family: sans-serif; margin: 0; padding: 24px; background: #fff7ef; color: #2b241f; }}
    .card {{ max-width: 560px; margin: 0 auto; background: #fff; border-radius: 14px; padding: 16px; box-shadow: 0 8px 30px rgba(0,0,0,0.08); }}
    .title {{ margin: 0 0 12px; font-size: 20px; }}
    .meta {{ margin: 0 0 8px; color: #7d6b5e; font-size: 13px; }}
    img {{ width: 100%; max-width: 360px; display: block; margin: 0 auto; border-radius: 10px; border: 1px solid #eee; }}
  </style>
</head>
<body>
  <div class="card">
    <h1 class="title">请使用下方二维码继续领取</h1>
    <p class="meta">分类：{html.escape(category_name)}</p>
    <img src="{html.escape(image_url)}" alt="二维码内容" />
  </div>
</body>
</html>
"""
        return HTMLResponse(content=html_doc)

    raw_text_content = packet.content_value or ""
    js_text_content = json.dumps(raw_text_content, ensure_ascii=False)
    html_doc = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(category_name)}内容</title>
  <style>
    body {{ font-family: sans-serif; margin: 0; padding: 24px; background: #fff7ef; color: #2b241f; }}
    .card {{ max-width: 560px; margin: 0 auto; background: #fff; border-radius: 14px; padding: 16px; box-shadow: 0 8px 30px rgba(0,0,0,0.08); }}
    .title {{ margin: 0 0 12px; font-size: 20px; }}
    .meta {{ margin: 0 0 12px; color: #7d6b5e; font-size: 13px; }}
    .content {{ white-space: pre-wrap; line-height: 1.6; }}
    .toolbar {{ display: flex; gap: 8px; margin-top: 14px; }}
    .btn {{ border: 0; border-radius: 10px; cursor: pointer; font-size: 14px; padding: 8px 12px; }}
    .btn-primary {{ background: #d8512d; color: #fff; }}
    .btn-secondary {{ background: #f5e3d9; color: #5f3c2e; }}
    .tip {{ color: #7d6b5e; font-size: 13px; margin-top: 10px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1 class="title">礼物文本内容</h1>
    <p class="meta">分类：{html.escape(category_name)}</p>
    <div id="content" class="content">********</div>
    <div class="toolbar">
      <button id="toggle" class="btn btn-secondary" type="button">显示内容</button>
      <button id="copy" class="btn btn-primary" type="button">复制内容</button>
    </div>
    <div id="tip" class="tip">请注意账号与密钥信息安全。</div>
  </div>
  <script>
    const rawContent = {js_text_content};
    const contentEl = document.getElementById('content');
    const toggleEl = document.getElementById('toggle');
    const copyEl = document.getElementById('copy');
    const tipEl = document.getElementById('tip');
    let revealed = false;

    function render() {{
      if (!contentEl || !toggleEl) return;
      contentEl.textContent = revealed ? rawContent : '********';
      toggleEl.textContent = revealed ? '隐藏内容' : '显示内容';
    }}

    if (toggleEl) {{
      toggleEl.addEventListener('click', () => {{
        revealed = !revealed;
        render();
      }});
    }}

    if (copyEl) {{
      copyEl.addEventListener('click', async () => {{
        try {{
          await navigator.clipboard.writeText(rawContent);
          if (tipEl) tipEl.textContent = '内容已复制到剪贴板';
        }} catch (err) {{
          if (tipEl) tipEl.textContent = '复制失败，请手动长按复制';
        }}
      }});
    }}

    render();
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_doc)

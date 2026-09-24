import uuid
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from pypinyin import lazy_pinyin, Style
from snownlp import SnowNLP
from datetime import datetime, timezone
from storage import init_db, save_record, get_history

app = FastAPI()

# ==================== 1. 完善 CORS 配置 ====================
# 定义允许访问的源列表
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,               # 允许前端域名
    allow_methods=["GET", "POST", "OPTIONS"], # 必须包含 OPTIONS，否则 POST 预检会失败
    allow_headers=["*"],                 # ⭐ 必须加上！允许所有请求头，解决跨域拦截
    allow_credentials=True,              # ⭐ 允许跨源请求带上 cookie（纸条）
)

# 启动时确保数据库表已建立
init_db()

# ==================== 2. 基础数据 ====================
profile = {
    "heroTitle": "关于我（来自后端）",
    "heroSubtitle": "项目，创意，灵感，心得，我的作品",
    "featuredWork": {
        "kicker": "作品",
        "title": "文字实验室",
        "copy": "拼音和情绪，挖掘中文里的细节",
        "linkLabel": "打开作品",
    },
    "identity": {
        "motto": "已识乾坤大，尤怜草木青",
        "learning": "零到全栈",
    },
}

class AnalyzeRequest(BaseModel):
    text: str

# ==================== 3. 工具函数：管理 Session（纸条） ====================
def get_session_id(request: Request, response: Response) -> str:
    sid = request.cookies.get("session_id")      # 先看有没有纸条
    if not sid:                                  # 第一次来，没有——发一张
        sid = uuid.uuid4().hex                    # 一串随机、不重复的 id
        response.set_cookie(
            "session_id", sid,
            httponly=True, samesite="lax",
            max_age=60 * 60 * 24 * 30,            # 记 30 天
        )
    return sid

def score_label(score):
    if score >= 0.6:
        return "偏积极"
    elif score <= 0.4:
        return "偏消极"
    else:
        return "中性"

# ==================== 4. 路由接口 ====================

@app.get("/api/profile")
def get_profile(request: Request, response: Response):  # ⭐ 接收 request 和 response
    get_session_id(request, response)                   # ⭐ 调用一下，确保第一次访问时发 Cookie（纸条）
    return profile                                      # ⭐ 返回正确的 JSON 数据

@app.post("/api/analyze")
def analyze(req: AnalyzeRequest, request: Request, response: Response):
    sid = get_session_id(request, response)
    text = req.text
    score = round(SnowNLP(text).sentiments, 2)
    
    result = {
        "text": text,
        "score": score,
        "label": score_label(score),
        "pinyin": " ".join(lazy_pinyin(text, style=Style.TONE)),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    
    save_record(sid, result)          # 存的时候盖上这个会话的记号
    return result                     # 返回体不变，session_id 只走 cookie

@app.get("/api/history")
def history(request: Request, response: Response, limit: int = 10):
    sid = get_session_id(request, response)
    return get_history(sid, limit)    # 只回这个会话自己的
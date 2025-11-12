# app.py
import streamlit as st
from PIL import Image
import cloudinary
import cloudinary.uploader
import cloudinary.api
import exifread, io, re
from datetime import datetime
import time

# -------------------- 1. 页面配置 --------------------
st.set_page_config(
    page_title="千禧时光 | 梦核相册",
    page_icon="⏳",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# -------------------- 2. Cloudinary 配置（只改这里） --------------------
CLOUD_NAME = "dv1ghhue3"
API_KEY = "852246619638176"
API_SECRET = "dwWSz9ODbMGn5fpuJ7AyEAMJERo"
BASE_FOLDER = "time-keys"

cloudinary.config(
    cloud_name=CLOUD_NAME,
    api_key=API_KEY,
    api_secret=API_SECRET,
    secure=True
)

BGM_URL = "https://res.cloudinary.com/dv1ghhue3/video/upload/v1762852048/nop_tnar44.mp3"

# -------------------- 3. 主题色 --------------------
THEME = {
    "primary": "#8A2BE2",
    "secondary": "#FF69B4",
    "bg": "#0A0A1A",
    "text": "#F0F0FF",
    "accent": "#00FFFF"
}

# -------------------- 4. 小工具 --------------------
def safe_key(text: str) -> str:
    return re.sub(r'\W+', '_', text)

def get_exif_year(photo_bytes):
    try:
        tags = exifread.process_file(io.BytesIO(photo_bytes))
        if 'EXIF DateTimeOriginal' in tags:
            return str(tags['EXIF DateTimeOriginal'])[:4]
    except:
        pass
    return ""

# -------------------- 5. 全局样式 + BGM --------------------
def inject_css():
    st.markdown(f"""
    <style>
    .stApp {{
        background: {THEME['bg']};
        color: {THEME['text']};
    }}
    h1,h2,h3,p,label,stTextInput > div > div > input{{
        color: {THEME['text']} !important;
    }}
    .stButton > button{{
        background: {THEME['primary']};
        color: {THEME['text']};
        border: 1px solid {THEME['accent']};
        border-radius: 8px;
        font-size: 1rem;
    }}
    .stButton > button:hover{{
        background: {THEME['secondary']};
        border-color: {THEME['accent']};
    }}
    .center-box{{
        max-width: 480px;
        margin: 0 auto;
        padding: 2rem 1rem;
        text-align: center;
    }}
    </style>
    """, unsafe_allow_html=True)


def bgm_player():
    with st.container():
        st.markdown(f"""
        <div style="margin-bottom:25px;">
            <h3 style="color:{THEME['accent']};text-shadow:0 0 8px {THEME['accent']};">
                🎵 梦核 BGM · 千禧时光
            </h3>
        </div>
        """, unsafe_allow_html=True)
        st.audio(BGM_URL, format="audio/mp3", loop=True, autoplay=False)

# -------------------- 6. 登录页 --------------------
def login_page():
    inject_css()
    bgm_player()
    with st.container():
        st.markdown('<div class="center-box">', unsafe_allow_html=True)
        st.markdown(f"""
        <h1 style="color:{THEME['accent']};font-size:2.8rem;text-shadow:0 0 12px {THEME['accent']};">
            千禧时光
        </h1>
        <p style="margin-bottom:30px;">请输入你的「时光密钥」以开启回忆</p>
        """, unsafe_allow_html=True)
        key = st.text_input(
            "时光密钥",
            placeholder="任意字符即可，如：moon2025",
            max_chars=50,
            label_visibility="collapsed"
        )
        if st.button("进入相册", type="primary", use_container_width=True):
            if not key.strip():
                st.error("密钥不能为空")
                st.stop()
            st.session_state["key"] = key.strip()
            st.session_state["folder"] = f"{BASE_FOLDER}/{safe_key(key)}"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------- 7. 上传组件（必须选年份） --------------------
def upload_widget():
    st.markdown("### 📤 上传新照片")
    c1, c2 = st.columns([2, 1])
    uploaded = c1.file_uploader("选择图片", type=["jpg", "jpeg", "png", "bmp"], label_visibility="collapsed")
    if uploaded:
        exif_year = get_exif_year(uploaded.getvalue())
    else:
        exif_year = ""
    year_list = [str(y) for y in range(1950, datetime.now().year + 1)]
    year_choice = c2.selectbox("照片年份", year_list, index=year_list.index(exif_year) if exif_year in year_list else len(year_list) - 1)
    if st.button("上传", type="primary"):
        if not uploaded:
            st.error("请先选择图片")
            st.stop()
        try:
            photo_bytes = uploaded.getvalue()
            cloudinary.uploader.upload(
                photo_bytes,
                folder=st.session_state["folder"],
                overwrite=False,
                context={
                    "taken_year": year_choice,
                    "original_name": uploaded.name,
                    "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            )
            st.success("上传成功！"), time.sleep(1), st.rerun()
        except Exception as e:
            st.error(f"上传失败：{e}")

# -------------------- 8. 加载相册 --------------------
def load_albums():
    try:
        resp = cloudinary.api.resources(
            type="upload",
            prefix=st.session_state["folder"] + "/",
            max_results=500,
            context=True
        )
        albums = {}
        for p in resp.get("resources", []):
            year = p["context"]["custom"].get("taken_year", "未知年份")
            albums.setdefault(year, []).append({
                "public_id": p["public_id"],  # 新增：删除用
                "url": p["secure_url"],
                "name": p["context"]["custom"].get("original_name", "未命名"),
                "time": p["context"]["custom"].get("upload_time", "")
            })
        return albums
    except Exception as e:
        if "Not found" in str(e):
            return {}
        st.error(f"加载出错：{e}")
        return {}

# -------------------- 9. 照片墙（带真正删除） --------------------
# def gallery(albums):
#     if not albums:
#         st.info("还没有照片，先上传一张吧~")
#         return
#
#     # 初始化删除状态
#     if "to_delete" not in st.session_state:
#         st.session_state["to_delete"] = None  # 存 public_id
#
#     for year in sorted(albums.keys(), reverse=True):
#         st.markdown(f"#### {year} 年")
#         cols = st.columns(4)
#         for idx, ph in enumerate(albums[year]):
#             with cols[idx % 4]:
#                 st.image(ph["url"], caption=ph["name"], use_container_width=True)
#
#                 # 复制链接
#                 if st.button("复制链接", key=f"copy_{year}_{idx}"):
#                     st.code(ph["url"], language=None)
#
#                 # 删除两步走
#                 if st.button("🗑️ 删除", key=f"del_{year}_{idx}"):
#                     st.session_state["to_delete"] = ph["public_id"]
#                     st.rerun()  # 立即 rerun，进入确认界面
#
#                 # 如果当前照片被标记为待删除，显示确认/取消
#                 if st.session_state["to_delete"] == ph["public_id"]:
#                     c1, c2 = st.columns(2)
#                     with c1:
#                         if st.button("确认删除", key=f"sure_{year}_{idx}"):
#                             try:
#                                 cloudinary.uploader.destroy(ph["public_id"])
#                                 st.success("已删除！")
#                                 st.session_state["to_delete"] = None
#                                 time.sleep(0.8)
#                                 st.rerun()
#                             except Exception as e:
#                                 st.error(f"删除失败：{e}")
#                                 st.session_state["to_delete"] = None
#                     with c2:
#                         if st.button("取消", key=f"cancel_{year}_{idx}"):
#                             st.session_state["to_delete"] = None
#                             st.rerun()
# -------------------- 照片墙（无复制链接） --------------------
def gallery(albums):
    if not albums:
        st.info("还没有照片，先上传一张吧~")
        return
    if "to_delete" not in st.session_state:
        st.session_state["to_delete"] = None

    for year in sorted(albums.keys(), reverse=True):
        st.markdown(f"#### {year} 年")
        cols = st.columns(4)
        for idx, ph in enumerate(albums[year]):
            with cols[idx % 4]:
                st.image(ph["url"], caption=ph["name"], use_container_width=True)

                # 小号删除图标（唯一按钮）
                if st.button("🗑️", key=f"del_{year}_{idx}", help="删除照片"):
                    st.session_state["to_delete"] = ph["public_id"]
                    st.rerun()

                # 确认/取消栏
                if st.session_state["to_delete"] == ph["public_id"]:
                    c1, c2 = st.columns([1, 1])
                    with c1:
                        if st.button("确认", key=f"sure_{year}_{idx}", type="primary"):
                            try:
                                cloudinary.uploader.destroy(ph["public_id"])
                                st.success("已删除！")
                                st.session_state["to_delete"] = None
                                time.sleep(0.8)
                                st.rerun()
                            except Exception as e:
                                st.error(f"删除失败：{e}")
                                st.session_state["to_delete"] = None
                    with c2:
                        if st.button("取消", key=f"cancel_{year}_{idx}"):
                            st.session_state["to_delete"] = None
                            st.rerun()

# -------------------- 10. 主流程 --------------------
def main():
    inject_css()
    if "key" not in st.session_state:
        login_page()
        return

    st.markdown(f"""
    <h1 style='text-align:center;color:{THEME['accent']};text-shadow:0 0 12px {THEME['accent']};'>
        千禧时光 · 梦核相册
    </h1>
    <p style='text-align:center;margin-bottom:30px;'>密钥：<code>{st.session_state['key']}</code></p>
    """, unsafe_allow_html=True)

    bgm_player()

    albums = load_albums()
    gallery(albums)

    st.divider()
    upload_widget()

    st.divider()
    st.markdown("<p style='text-align:center;opacity:0.6'>时间是循环的，回忆是永恒的</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
import streamlit as st
from typing import Dict, Any, Optional
def render_top_video_card(video: Optional[Dict[str, Any]], period_label: str) -> None:
    if not video or not isinstance(video, dict):
        st.info(f"📹 Нет данных о видео за {period_label}")
        return
    title = video.get('title', 'Без названия')
    views = video.get('views', 0)
    likes = video.get('likes', 0)
    video_id = video.get('video_id', '')
    engagement = (likes / views * 100) if views > 0 else 0
    st.markdown(f"**{period_label}**")
    video_url = f"https://youtube.com/watch?v={video_id}"
    st.markdown(f"🎬 [{title}]({video_url})")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Просмотры", f"{views:,}")
    with col2:
        st.metric("Лайки", f"{likes:,}")
    with col3:
        st.metric("ER %", f"{engagement:.2f}")
def render_top_videos_section(
    best_7d: Optional[Dict],
    best_30d: Optional[Dict],
    best_90d: Optional[Dict],
    best_all_time: Optional[Dict]
) -> None:
    st.subheader("🏆 Топ видео по периодам")
    col1, col2 = st.columns(2)
    with col1:
        render_top_video_card(best_7d, "Лучшее за 7 дней")
        st.markdown("---")
        render_top_video_card(best_30d, "Лучшее за 30 дней")
    with col2:
        render_top_video_card(best_90d, "Лучшее за 90 дней")
        st.markdown("---")
        render_top_video_card(best_all_time, "Лучшее за всё время")

import streamlit as st
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
def render_video_table(videos: List[Dict[str, Any]], title: str = "Последние видео") -> None:
    if not videos:
        st.info("📹 Нет данных о видео")
        return
    st.subheader(title)
    data = []
    for video in videos:
        views = video.get('views', 0)
        likes = video.get('likes', 0)
        comments = video.get('comments', 0)
        engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0
        published_at = video.get('published_at')
        if isinstance(published_at, str):
            try:
                published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                published_at = None
        date_str = published_at.strftime('%d.%m.%Y') if published_at else 'N/A'
        video_id = video.get('video_id', '')
        video_url = f"https://youtube.com/watch?v={video_id}"
        title_text = video.get('title', 'Без названия')
        data.append({
            'Название': title_text,
            'URL': video_url,
            'Дата': date_str,
            'Просмотры': views,
            'Лайки': likes,
            'Комментарии': comments,
            'ER %': engagement_rate
        })
    df = pd.DataFrame(data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Название': st.column_config.TextColumn('Название', width='large'),
            'URL': st.column_config.LinkColumn('Ссылка', display_text='YouTube'),
            'Дата': st.column_config.TextColumn('Дата', width='small'),
            'Просмотры': st.column_config.NumberColumn('Просмотры', format='%d'),
            'Лайки': st.column_config.NumberColumn('Лайки', format='%d'),
            'Комментарии': st.column_config.NumberColumn('Комментарии', format='%d'),
            'ER %': st.column_config.NumberColumn('ER %', format='%.2f'),
        }
    )

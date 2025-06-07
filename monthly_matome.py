import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.oauth2 import SpotifyOAuth
import json
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import requests
import zipfile
import streamlit as st
import pandas as pd
import json
import zipfile
from io import BytesIO, TextIOWrapper

# SpotifyのクライアントIDとクライアントシークレットを設定
client_id = st.secrets["SPOTIFY_CLIENT_ID"]
client_secret = st.secrets["SPOTIFY_CLIENT_SECRET"]
redirect_uri = st.secrets["SPOTIFY_REDIRECT_URI"]
# StreamlitでURLパラメータを取得
query_params = st.experimental_get_query_params()
code = query_params.get("code", [None])[0]
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id,
    client_secret
))
# サイズ設定
image_size = (100, 100)
padding = 20
line_height = 120
width = 600
height = padding * 2 + line_height * 5

# 背景作成（単色でもグラデでもOK）
img = Image.new("RGB", (width, height), (255, 230, 240))
draw = ImageDraw.Draw(img)
font_title = ImageFont.truetype("MEIRYO.TTC", 20)
font_artist = ImageFont.truetype("MEIRYO.TTC", 16)
font_rank = ImageFont.truetype("MEIRYO.TTC", 32)
# JSONファイル読み込み
def Read_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        df = pd.DataFrame(data)
        df['endTime'] = pd.to_datetime(df['endTime'], format='%Y-%m-%d %H:%M')
        df = df[df['trackName'] != "Unknown Track"]
# 指定年月のDataframeを作成

def Make_data(json_files,year, month):
    dfs = [Read_json(fp) for fp in json_files]
    df = pd.concat(dfs, ignore_index=True)
    monthly_data = df[(df['endTime'].dt.year == year) & (df['endTime'].dt.month == month)]
    return monthly_data

# 月ごとの再生回数上位5曲を取得
def Get_top_tracks(monthly_data):
    top_tracks = monthly_data.groupby(['artistName', 'trackName']).size().reset_index(name='count').sort_values('count', ascending=False).head(5)
    top_tracks['image_url'] = top_tracks.apply(lambda row: Get_track_image_url(row['artistName'], row['trackName']), axis=1)
    top_tracks = top_tracks.reset_index(drop=True)
    return top_tracks

# 楽曲画像URLを取得する関数
def Get_track_image_url(artist, track):
    query = f"artist:{artist} track:{track}"
    result = sp.search(q=query, type='track', limit=1)
    items = result['tracks']['items']
    if items:
        return items[0]['album']['images'][0]['url']  # 一番大きい画像
    else:
        return None

# アーティスト画像URLを取得する関数    
def Get_artist_image_url(artist, track=None):
    if track:
        query = f'artist:"{artist}" track:"{track}"'
        result = sp.search(q=query, type='track', limit=1)
        items = result['tracks']['items']
        if items and items[0]['artists']:
            artist_id = items[0]['artists'][0]['id']
            artist_info = sp.artist(artist_id)
            if artist_info['images']:
                return artist_info['images'][0]['url']
    query = f'artist:"{artist}"'
    result = sp.search(q=query, type='artist', limit=1)
    items = result['artists']['items']
    if items and items[0]['images']:
        return items[0]['images'][0]['url']
    return None

# 月ごとの再生回数上位5アーティストを取得
def Get_top_artists(monthly_data):
    top_artists = monthly_data.groupby('artistName').agg(count=('artistName', 'size'),total_minutes=('msPlayed', lambda x: round(x.sum() / 1000 / 60, 2))).reset_index()  
    top_artists['total_time'] = top_artists['total_minutes'].apply(Convert_time)
    top_artists = top_artists.sort_values('count', ascending=False).head(5)
    top_artists['top_track'] = top_artists['artistName'].apply(lambda artist: Get_top_track(monthly_data, artist))
    top_artists['image_url'] = top_artists.apply(lambda row: Get_artist_image_url(row['artistName'], row['top_track']),axis=1)
    return top_artists.reset_index(drop=True)

# 合計再生時間を「xx時間yy分」形式に変換
def Convert_time(minutes):
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours}時間{mins}分"

# 月ごとの再生回数上位5アーティストのトップトラックを取得
def Get_top_track(monthly_data, artist_name):
    tracks = (monthly_data[monthly_data['artistName'] == artist_name].groupby('trackName').size().reset_index(name='count').sort_values('count', ascending=False))
    if not tracks.empty:
        return tracks.iloc[0]['trackName']
    else:
        return None
    
# 画像取得
def Get_image(top_list):
    for i, row in top_list.iterrows():
        image_url = row["image_url"]
        response = requests.get(image_url)
        with open(f"./img/{i}.png", 'wb') as f:
            f.write(response.content)

# トップソングの画像生成
def Plot_top_tracks_image(top_tracks):
    Get_image(top_tracks)
    for i, row in top_tracks.iterrows():
        y = padding + i * line_height
        artwork = Image.open(f"./img/{i}.png").resize(image_size)
        img.paste(artwork, (padding, y))
        text_x = padding + image_size[0] + 15
        draw.text((text_x, y), f"{i+1}. {row['trackName']}", fill="black", font=font_title)
        draw.text((text_x, y + 30), row["artistName"], fill="gray", font=font_artist)
        draw.text((text_x, y + 55), f"{row['count']}回再生", fill="gray", font=font_artist)
    img.save("./result/top_track.png")

# トップアーティストの画像生成
def Plot_top_artists_image(top_artists):
    img = Image.new("RGB", (width, height), (220, 255, 220))
    draw = ImageDraw.Draw(img)
    Get_image(top_artists)
    for i, row in top_artists.iterrows():
        y = padding + i * line_height
        artwork = Image.open(f"./img/{i}.png").resize(image_size)
        img.paste(artwork, (padding, y))
        text_x = padding + image_size[0] + 15
        draw.text((text_x, y), f"{i+1}. {row['artistName']}", fill="black", font=font_title)
        draw.text((text_x, y + 30), f"合計時間: {row['total_time']}", fill="gray", font=font_artist)
    img.save("./result/top_artist.png")
st.title("Spotify 月間レポート Webアプリ")

# ZIPファイルアップロード（中に複数のJSONファイルが入っている前提）
uploaded_zip = st.file_uploader("再生履歴の ZIP ファイルをアップロード", type="zip")

# 年月の指定
col1, col2 = st.columns(2)
with col1:
    year = st.number_input("年を入力（例：2025）", value=2025, min_value=2000, max_value=2100)
with col2:
    month = st.number_input("月を入力（1〜12）", value=4, min_value=1, max_value=12)

# 実行ボタン
if st.button("画像を生成"):
    if uploaded_zip is None:
        st.warning("ZIPファイルをアップロードしてください。")
    else:
        dfs = []

        # ZIPファイルを展開
        with zipfile.ZipFile(uploaded_zip) as z:
            for filename in z.namelist():
                if filename.endswith(".json"):
                    with z.open(filename) as json_file:
                        text_file = TextIOWrapper(json_file, encoding='utf-8')
                        if "StreamingHistory_music" in text_file.name:
                            data = json.load(text_file)
                            df = pd.DataFrame(data)
                            df['endTime'] = pd.to_datetime(df['endTime'], format='%Y-%m-%d %H:%M')
                            df = df[df['trackName'] != "Unknown Track"]
                            dfs.append(df)

        if not dfs:
            st.error("ZIP内に有効なJSONファイルが見つかりませんでした。")
        else:
            df_all = pd.concat(dfs, ignore_index=True)
            monthly_data = df_all[(df_all['endTime'].dt.year == year) & (df_all['endTime'].dt.month == month)]
            print(monthly_data)
            top_tracks = Get_top_tracks(monthly_data)
            top_artists = Get_top_artists(monthly_data)

            Plot_top_tracks_image(top_tracks)
            Plot_top_artists_image(top_artists)

            st.success("画像生成が完了しました！")

            # 結果画像表示
            st.image("./result/top_track.png", caption="トップトラック", use_column_width=True)
            st.image("./result/top_artist.png", caption="トップアーティスト", use_column_width=True)

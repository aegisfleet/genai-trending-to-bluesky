import io
import requests
import time
from atproto import models, client_utils
from atproto_client.exceptions import UnauthorizedError, NetworkError
from bs4 import BeautifulSoup, Tag
from PIL import Image

def fetch_webpage_metadata(url):
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
    except Exception as error:
        print(f"リクエスト中にエラーが発生しました: {error}")
        return "", "", ""

    return parse_html_for_metadata(response.text)

def parse_html_for_metadata(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    title = soup.find("title")
    title_text = title.get_text() if title else ""

    description = soup.find("meta", attrs={"name": "description"}) or \
                  soup.find("meta", attrs={"property": "og:description"})
    image = soup.find("meta", attrs={"property": "og:image"})

    description_content = description["content"] if description and isinstance(description, Tag) else ""
    image_url = image["content"] if image and isinstance(image, Tag) else ""

    title_text = BeautifulSoup(title_text, "html.parser").get_text()
    description_content = BeautifulSoup(description_content if isinstance(description_content, str) else "", "html.parser").get_text()

    return title_text, description_content, image_url

def authenticate(bs_client, username, password, retries=3, wait_time=5):
    for attempt in range(retries):
        try:
            bs_client.login(username, password)
            print("Authentication successful")
            return
        except UnauthorizedError as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print("All retry attempts failed. Please check your credentials.")
                raise e

def format_message(title, introduction, content):
    formatted_content = content.strip().replace("  ", "").replace("\n", "").replace("。", "。\n")
    return client_utils.TextBuilder().text(f"{introduction}\n\n{title}\n{formatted_content}")

def format_message_with_link(title, url, introduction, content):
    formatted_content = content.strip().replace("  ", "").replace("\n", "").replace("。", "。\n")
    return client_utils.TextBuilder().text(f"{introduction}\n\n")\
                                      .link(title, url)\
                                      .text(f"\n{formatted_content}")

def compress_image(image_bytes, max_size_kb=500, quality=85):
    img = Image.open(io.BytesIO(image_bytes))

    if img.mode in ['RGBA', 'P']:
        img = img.convert('RGB')

    while True:
        with io.BytesIO() as output:
            img.save(output, format="JPEG", quality=quality)
            compressed_bytes = output.getvalue()
            size_kb = len(compressed_bytes) / 1024
            if size_kb <= max_size_kb:
                return compressed_bytes

        if quality > 20:
            quality -= 5
        else:
            img = img.resize((img.width * 9 // 10, img.height * 9 // 10), 
                             resample=Image.Resampling.LANCZOS)

def create_external_embed(bs_client, title, description, url, img_url):
    trimmed_desc = description.replace("\n", "")[:200]
    img_data = None
    thumb_blob = None
    retries = 3

    for attempt in range(1, retries + 1):
        try:
            img_response = requests.get(img_url)
            img_response.raise_for_status()
            img_data = img_response.content
            break
        except requests.RequestException as e:
            print(f"画像データの取得に失敗しました: {e} リトライ回数: {attempt}")
            if attempt < retries:
                time.sleep(10)
            else:
                print("画像の取得に最終的に失敗しました。サムネイルなしで進めます。")

    if img_data is not None:
        compressed_img_data = compress_image(img_data)

        for attempt in range(1, retries + 1):
            try:
                thumb_blob = bs_client.upload_blob(compressed_img_data).blob
                break
            except NetworkError as e:
                print(f"サムネイルのアップロードに失敗しました: {e} リトライ回数: {attempt}")
                if attempt < retries:
                    time.sleep(10)
                else:
                    print("サムネイルのアップロードに最終的に失敗しました。サムネイルなしで進めます。")

    return models.AppBskyEmbedExternal.Main(
        external=models.AppBskyEmbedExternal.External(
            title=title,
            description=trimmed_desc,
            uri=url,
            thumb=thumb_blob
        )
    )

def post(bs_client, text, embed):
    retries = 3
    for attempt in range(1, retries + 1):
        try:
            bs_client.send_post(text, embed=embed)
            break
        except Exception as e:
            print(f"送信に失敗しました。リトライします... リトライ回数: {attempt}, エラー: {e}")
            time.sleep(3)
    else:
        print("リトライ上限に達しました。送信に失敗しました。")

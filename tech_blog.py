import requests
from atproto import Client as BSClient
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
from typing import Optional, List, Tuple
import artifact_utils
import bluesky_utils
import gpt_utils

def fetch_trending_articles(url: str = "https://karaage0703.github.io/tech-blog-rss-feed/feeds/rss.xml", max_articles: int = 5) -> List[Tuple[str, str, str]]:
    previous_articles = artifact_utils.load_previous_results()

    articles: List[Tuple[str, str, str]] = []

    response = requests.get(url)
    root = ET.fromstring(response.content)

    channel = root.find('channel')
    if channel is not None:
        for item in channel.findall('item')[:10]:
            if len(articles) >= max_articles:
                break
            link = item.find('link')
            title = item.find('title')
            description = item.find('description')

            if (
                link is None 
                or title is None 
                or description is None 
                or link.text in previous_articles 
                or any(link.text == article[0] for article in articles)
            ):
                continue
            articles.append((link.text or "", title.text or "", description.text or ""))

    artifact_utils.save_results(articles)
    return articles

def fetch_article_content(url: str) -> Optional[str]:
    response = requests.get(url)
    response.encoding = response.apparent_encoding

    soup = BeautifulSoup(response.text, 'html.parser')
    article_content_selector = 'article'
    article_content = soup.select_one(article_content_selector)

    if not article_content or not article_content.text.strip():
        article_content_selector = '#masterMain'
        article_content = soup.select_one(article_content_selector)

    if article_content is not None:
        return article_content.text.strip()[:6000]
    return None

def generate_post_text(api_key, full_url, title, content, introduction):
    retries = 0
    max_retries = 3
    while retries < max_retries:
        limit_size = 300 - len(introduction) - len(title)
        print(f"limit_size: {limit_size}")
        message = gpt_utils.get_description(
            api_key,
            "この記事で何が伝えたいのか[limit_size]文字以下でまとめて欲しい。"
            "\n回答は日本語で強調文字は使用せず簡素にする。"
            f"\n以下に記事の内容を記載する。\n\n{content}",
            limit_size
        )
        post_text = bluesky_utils.format_message_with_link(
            title, full_url, introduction, message
        )

        if len(post_text.build_text()) < 300:
            return post_text
        retries += 1
        print(f"文字数が300文字を超えています。リトライ回数: {retries}")
    print("300文字以内の文字を生成できませんでした。")
    return None

def post(user_handle: str, user_password: str, api_key: str, config: dict):
    targets = fetch_trending_articles()

    bs_client = BSClient()

    for full_url, title, description in targets:
        print(f"\nURL: {full_url}\nTitle: {title}")

        content = fetch_article_content(full_url)
        post_text = generate_post_text(api_key, full_url, title, content, config["introduction"])
        if not post_text:
            continue

        title, _, image_url = bluesky_utils.fetch_webpage_metadata(full_url)
        print(post_text.build_text(), image_url, sep="\n")

        bluesky_utils.authenticate(bs_client, user_handle, user_password)
        embed_external = bluesky_utils.create_external_embed(
            bs_client, title, description, full_url, image_url
        )
        bluesky_utils.post(bs_client, post_text, embed_external)

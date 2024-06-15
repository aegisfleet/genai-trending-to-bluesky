import sys
import article_utils

def print_usage_and_exit():
    print("使用法: python main.py <BlueSkyのユーザーハンドル> <BlueSkyのパスワード> <GeminiのAPIキー> <モード>")
    sys.exit(1)

def main():
    if len(sys.argv) != 5:
        print_usage_and_exit()

    user_handle, user_password, api_key, mode = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

    if mode not in ["techcrunch", "venturebeat"]:
        print_usage_and_exit()

    if mode == "techcrunch":
        config_techcrunch = {
            "url": "https://techcrunch.com/category/artificial-intelligence/",
            "count": 5,
            "base_url": "",
            "container_tag": {"name": "div", "class_": "wp-block-tc23-post-picker"},
            "title_box_tag": {"name": "h2", "class_": "wp-block-post-title"},
            "article_content": {"name": "div", "class_": "entry-content"},
            "href_prefix": "",
            "introduction": "今日のAIニュース"
        }
        article_utils.post(user_handle, user_password, api_key, config_techcrunch)
    elif mode == "venturebeat":
        config_venturebeat = {
            "url": "https://venturebeat.com/category/ai/",
            "count": 5,
            "base_url": "",
            "container_tag": {"name": "article", "class_": "ArticleListing"},
            "title_box_tag": {"name": "h2", "class_": "ArticleListing__title"},
            "article_content": {"name": "div", "class_": "article-content"},
            "href_prefix": "",
            "introduction": "今日のAIニュース"
        }
        article_utils.post(user_handle, user_password, api_key, config_venturebeat)

if __name__ == "__main__":
    main()

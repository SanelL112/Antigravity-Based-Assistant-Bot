import re


def clean_emojis(text):
    """Remove emoji and other problematic Unicode characters."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002700-\U000027BF"
        "\U0001F900-\U0001F9FF"
        "\U00002600-\U000026FF"
        "\U00002B00-\U00002BFF"
        "\U0001F780-\U0001F7FF"
        "\U0001F800-\U0001F8FF"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", text)


def main() -> None:
    guide_dir = "/home/sanel/personal-assistant-bot/study_guides"
    guide_names = [
        "SAT_Math_and_Geometry_Master_Guide_Study_Guide",
        "SAT_Reading_Comprehension_Master_Guide_Study_Guide",
        "SAT_Writing_and_Grammar_Master_Guide_Study_Guide",
    ]
    for name in guide_names:
        source = f"{guide_dir}/{name}.md"
        target = f"{guide_dir}/{name}_clean.md"
        with open(source, "r", encoding="utf-8") as file:
            cleaned = clean_emojis(file.read())
        with open(target, "w", encoding="utf-8") as file:
            file.write(cleaned)
        print(f"{name} cleaned")


if __name__ == "__main__":
    main()

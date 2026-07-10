import re

def clean_emojis(text):
    """Remove emojis and other problematic Unicode characters"""
    # Remove common emojis used in the study guides
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002700-\U000027BF"  # dingbats
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U00002600-\U000026FF"  # miscellaneous symbols
        "\U00002B00-\U00002BFF"  # arrows and shapes
        "\U0001F780-\U0001F7FF"  # geometric shapes extended
        "\U0001F800-\U0001F8FF"  # supplemental arrows-C
        "]+", 
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)

# Read and clean math guide
with open('/home/sanel/personal-assistant-bot/study_guides/SAT_Math_and_Geometry_Master_Guide_Study_Guide.md', 'r') as f:
    content = f.read()

cleaned = clean_emojis(content)

with open('/home/sanel/personal-assistant-bot/study_guides/SAT_Math_and_Geometry_Master_Guide_Study_Guide_clean.md', 'w') as f:
    f.write(cleaned)

print("Math guide cleaned")

# Also clean the other guides
for name in ['SAT_Reading_Comprehension_Master_Guide_Study_Guide', 'SAT_Writing_and_Grammar_Master_Guide_Study_Guide']:
    with open(f'/home/sanel/personal-assistant-bot/study_guides/{name}.md', 'r') as f:
        content = f.read()
    cleaned = clean_emojis(content)
    with open(f'/home/sanel/personal-assistant-bot/study_guides/{name}_clean.md', 'w') as f:
        f.write(cleaned)
    print(f"{name} cleaned")
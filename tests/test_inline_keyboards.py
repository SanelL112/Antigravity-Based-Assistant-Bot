import pytest
from inline_keyboards import (
    get_new_tasks_keyboard,
    get_digest_topic_keyboard,
    get_study_guide_keyboard,
    get_quick_actions_keyboard,
    get_photo_response_keyboard,
)

def test_get_new_tasks_keyboard_empty():
    keyboard = get_new_tasks_keyboard([])
    assert len(keyboard.inline_keyboard) == 1
    assert keyboard.inline_keyboard[0][0].text == "✅ Ignore All"
    assert keyboard.inline_keyboard[0][0].callback_data == "task_ignore_all"

def test_get_new_tasks_keyboard_under_limit():
    task_ids = ["task1", "task2"]
    keyboard = get_new_tasks_keyboard(task_ids)
    assert len(keyboard.inline_keyboard) == 3 # 2 tasks + 1 ignore all

    # task 1
    assert keyboard.inline_keyboard[0][0].text == "🔴 task1 - High"
    assert keyboard.inline_keyboard[0][0].callback_data == "task_prio:task1:high"
    assert keyboard.inline_keyboard[0][1].text == "🟡 task1 - Medium"
    assert keyboard.inline_keyboard[0][1].callback_data == "task_prio:task1:medium"
    assert keyboard.inline_keyboard[0][2].text == "🟢 task1 - Low"
    assert keyboard.inline_keyboard[0][2].callback_data == "task_prio:task1:low"

    # task 2
    assert keyboard.inline_keyboard[1][0].text == "🔴 task2 - High"
    assert keyboard.inline_keyboard[1][0].callback_data == "task_prio:task2:high"

    # ignore all
    assert keyboard.inline_keyboard[2][0].text == "✅ Ignore All"
    assert keyboard.inline_keyboard[2][0].callback_data == "task_ignore_all"

def test_get_new_tasks_keyboard_over_limit():
    task_ids = ["task1", "task2", "task3", "task4", "task5", "task6"]
    keyboard = get_new_tasks_keyboard(task_ids)
    assert len(keyboard.inline_keyboard) == 6 # max 5 tasks + 1 ignore all

    # last task should be task5
    assert keyboard.inline_keyboard[4][0].text == "🔴 task5 - High"
    assert keyboard.inline_keyboard[4][0].callback_data == "task_prio:task5:high"

def test_get_digest_topic_keyboard_empty():
    keyboard = get_digest_topic_keyboard([])
    assert len(keyboard.inline_keyboard) == 1
    assert keyboard.inline_keyboard[0][0].text == "❌ Dismiss"
    assert keyboard.inline_keyboard[0][0].callback_data == "digest_dismiss"

def test_get_digest_topic_keyboard_under_limit():
    topics = ["math", "science"]
    keyboard = get_digest_topic_keyboard(topics)
    assert len(keyboard.inline_keyboard) == 3 # 2 topics + 1 dismiss

    # topic 1
    assert keyboard.inline_keyboard[0][0].text == "🧠 Build Guide: math"
    assert keyboard.inline_keyboard[0][0].callback_data == "build_guide:math"

    # topic 2
    assert keyboard.inline_keyboard[1][0].text == "🧠 Build Guide: science"
    assert keyboard.inline_keyboard[1][0].callback_data == "build_guide:science"

    # dismiss
    assert keyboard.inline_keyboard[2][0].text == "❌ Dismiss"
    assert keyboard.inline_keyboard[2][0].callback_data == "digest_dismiss"

def test_get_digest_topic_keyboard_over_limit():
    topics = ["topic1", "topic2", "topic3", "topic4", "topic5"]
    keyboard = get_digest_topic_keyboard(topics)
    assert len(keyboard.inline_keyboard) == 5 # max 4 topics + 1 dismiss

    # last topic should be topic4
    assert keyboard.inline_keyboard[3][0].text == "🧠 Build Guide: topic4"
    assert keyboard.inline_keyboard[3][0].callback_data == "build_guide:topic4"

def test_get_study_guide_keyboard():
    keyboard = get_study_guide_keyboard("guide_name")
    assert len(keyboard.inline_keyboard) == 2

    assert keyboard.inline_keyboard[0][0].text == "📝 Grade Practice Photo"
    assert keyboard.inline_keyboard[0][0].callback_data == "grade_guide:guide_name"
    assert keyboard.inline_keyboard[0][1].text == "📅 Schedule Study Time"
    assert keyboard.inline_keyboard[0][1].callback_data == "schedule_guide:guide_name"

    assert keyboard.inline_keyboard[1][0].text == "📖 Open in Obsidian"
    assert keyboard.inline_keyboard[1][0].callback_data == "obsidian_guide:guide_name"

def test_get_quick_actions_keyboard():
    keyboard = get_quick_actions_keyboard()
    assert len(keyboard.inline_keyboard) == 3

    assert keyboard.inline_keyboard[0][0].text == "📊 Digest"
    assert keyboard.inline_keyboard[0][0].callback_data == "cmd:summary"
    assert keyboard.inline_keyboard[0][1].text == "🩺 Health"
    assert keyboard.inline_keyboard[0][1].callback_data == "cmd:ping"

    assert keyboard.inline_keyboard[1][0].text == "💰 Stats"
    assert keyboard.inline_keyboard[1][0].callback_data == "cmd:stats"
    assert keyboard.inline_keyboard[1][1].text == "💾 Backup"
    assert keyboard.inline_keyboard[1][1].callback_data == "cmd:backup"

    assert keyboard.inline_keyboard[2][0].text == "🔗 Correlations"
    assert keyboard.inline_keyboard[2][0].callback_data == "cmd:correlations"

def test_get_photo_response_keyboard():
    keyboard = get_photo_response_keyboard()
    assert len(keyboard.inline_keyboard) == 2

    assert keyboard.inline_keyboard[0][0].text == "📝 Grade Practice Test"
    assert keyboard.inline_keyboard[0][0].callback_data == "photo:grade"
    assert keyboard.inline_keyboard[0][1].text == "📋 Save to Notes"
    assert keyboard.inline_keyboard[0][1].callback_data == "photo:save"

    assert keyboard.inline_keyboard[1][0].text == "❓ Ask Me About This"
    assert keyboard.inline_keyboard[1][0].callback_data == "photo:ask"

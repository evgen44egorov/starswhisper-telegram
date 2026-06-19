def normalize_question(value: str) -> str:
    question = " ".join(value.strip().split())
    if len(question) < 10:
        raise ValueError("Опиши вопрос чуть подробнее — минимум 10 символов.")
    if len(question) > 500:
        raise ValueError("Сократи вопрос до 500 символов.")
    return question


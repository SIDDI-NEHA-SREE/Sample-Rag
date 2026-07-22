def generate_answer_stream(question, contexts):

    prompt = build_prompt(question, contexts)

    response = client.models.generate_content_stream(
        model=CHAT_MODEL,
        contents=prompt
    )

    for chunk in response:
        yield chunk

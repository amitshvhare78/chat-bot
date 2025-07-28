import os

from groq import Groq

prompt=input("enter your prompt")

client = Groq(
    api_key=os.getenv("GROQ_API_KEY", "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"),
)

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": prompt,

        }
    ],
    model="llama-3.3-70b-versatile",
)

print(chat_completion.choices[0].message.content)
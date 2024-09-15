from os import system as shell
from os import name as os_name
import re

import ollama

from constants import *
from tree import search

wrap_chat_message = lambda role, content: {"role": role, "content": content}

global_chat_history = [wrap_chat_message("system", LLM_SYSTEM_PROMPT)]


def clear_shell():
    if os_name == "nt":
        shell("cls")
    else:
        shell("clear")

clear_shell()
while True:
    user_message = input("user > ")
    global_chat_history.append(wrap_chat_message("user", user_message))

    # Estimation of required no. of rollouts
    clear_shell()
    estimations = []
    for i, estimation_type in enumerate(THREE_POINT_ESTIMATE_TYPES):
        print(f"Getting max depth estimate {i+1}/{len(THREE_POINT_ESTIMATE_TYPES)} ({estimation_type.lower()} estimate)")

        tmp_chat_history = global_chat_history[:-1] + [
            wrap_chat_message(
                "user",
                MAX_ROLLOUT_ESTIMATION_PROMPT.replace('$QUERY', global_chat_history[-1]['content'].replace('$ESTIMATION_TYPE', estimation_type))
            )
        ]

        j = 0
        res = []
        while not res:
            j += 1
            print(f"Attempt no. {j}")
            evaluation_raw_txt = ollama.chat(
                model=OLLAMA_LLM,
                messages=tmp_chat_history,
                options={"num_ctx": CTX_WINDOW},
            )["message"]["content"]
            reg_str = r"<output>(\d+)</output>"
            res = re.findall(reg_str, evaluation_raw_txt)
            if not res:
                continue
            single_estimation = max(int(res[-1]), 1)
            estimations.append(single_estimation)

    max_search_depth = min((estimations[0] + 4*estimations[1] + estimations[2]) // 6, SEARCH_DEPTH_CAP)

    # Thinking
    thoughts = ""
    for step in search(global_chat_history, OLLAMA_LLM, max_search_depth):
        clear_shell()
        if step["finished"]:
            thoughts = step["thoughts"]
            match step["reason"]:
                case 1:
                    finished_reason = "definite search completion"
                case 2:
                    finished_reason = "diminishing returns"
                case 3:
                    finished_reason = "maximum search depth reached"
            print(
                f'Finished reasoning with a Q value of {step["q_value"]} because of {finished_reason}.'
            )
            print(f"Thoughts:\n\n{thoughts}\n\nResponse:")
        else:
            print(f'Current best node has a Q value of {step["q_value"]}')
            print(f'Thoughts:\n{step["thoughts"]}')

    # Response
    tmp_chat_history = global_chat_history[:-1] + [
        wrap_chat_message(
            "user",
            GENERATION_PROMPT.replace('$QUERY', global_chat_history[-1]['content']).replace('$THOUGHTS', thoughts)
        )
    ]
    response = ""
    for chunk in ollama.chat(
        model=OLLAMA_LLM,
        messages=tmp_chat_history,
        stream=True,
        options={"num_ctx": CTX_WINDOW},
    ):
        response += chunk["message"]["content"]
        print(chunk["message"]["content"], end="", flush=True)
    global_chat_history.append(
        wrap_chat_message("assistant", thoughts + "\n\n" + response)
    )

    clear_shell()
    for message in global_chat_history:
        if message["role"] == "system":
            continue
        print(f"{message['role']} > {message['content']}")
    print(
        f'Finished reasoning with a Q value of {step["q_value"]} because of {finished_reason}.'
    )

import re
from enum import Enum

from fuzzywuzzy import fuzz

from utils import html_to_discord

SIMILARITY_RATIO_THRESHOLD = 60
USING_EXPERIMENTAL_VALIDATOR = False

STOP_WORDS = ['idk', 'nope', 'nah', 'fuck', 'shit']


class Correctness(Enum):
    CORRECT = 0
    INCORRECT = 1
    PROMPT = 2

def parse_answerline(answerline):
    formatted_answer = answerline.lower()
    main_answer = html_to_discord(re.split(r'[\[<]', formatted_answer)[0])
    unformatted_main_answer = main_answer.replace('*', '').replace('_', '')
    correct_answers = re.findall(r'\*+.+?\*+', formatted_answer)
    correct_answers = [a.lstrip().rstrip().lstrip('*').rstrip('*').strip('_') for a in correct_answers]
    return formatted_answer, main_answer, unformatted_main_answer, correct_answers

def validate(given_answer, answerline):
    if USING_EXPERIMENTAL_VALIDATOR:
        return validate_experimental(given_answer, answerline)
    else:
        return validate_regex(given_answer, answerline)

def validate_regex(given_answer, answerline):
    formatted_answer, main_answer, unformatted_main_answer, correct_answers = parse_answerline(answerline)
    given_answer = given_answer.lower()

    if len(correct_answers) == 0:
        correct_answers = [main_answer]

    correctness = Correctness.PROMPT
    for ans in correct_answers:
        if fuzz.ratio(ans.lower(), given_answer) > SIMILARITY_RATIO_THRESHOLD:
            correctness = Correctness.CORRECT

    if given_answer in STOP_WORDS:
        correctness = Correctness.INCORRECT

    return correctness, formatted_answer, main_answer, unformatted_main_answer, correct_answers

def validate_experimental(given_answer, answerline):
    pass
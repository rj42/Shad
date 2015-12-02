import argparse
import pickle
import random
import string
import sys
from collections import defaultdict

# -------------------------------- Constants -------------------------------- #

DEFAULT_LM_ORDER = 3
DEFAULT_GENERATED_CORPUS_SIZE = 10 * 1000

PUNCTUATION = set(string.punctuation)
PUNCTUATION_END_SENTENCE = set(".?!")

# ------------------------------ Utilities ---------------------------------- #


def factory_defaultdict_int():
    return defaultdict(int)


def tokenize_sentence(sentence):
    """
    Simple sentence tokenizer.

    >>> "Hello, how are you?"
    ["Hello", ",", "how", "are", "you", "?"]

    :param sentence: input sentence
    :return: tokens
    """
    tokens = sentence.strip().split(" ")
    for token in tokens:
        if len(token) == 1:
            yield token
        elif len(token) >= 2:
            first_sym = token[0]
            if first_sym in PUNCTUATION:
                token = token[1:]
                yield first_sym
            last_sym = token[-1]
            if last_sym in PUNCTUATION:
                token = token[:-1]
                yield token
                yield last_sym
            else:
                yield token


def progress(count, total, suffix=''):
    # http://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', suffix))

# ------------------------------ LMBuilder----------------------------------- #


class LMBuilder():
    def __init__(self, order):
        assert order > 0, "Invalid: " + order
        self.order = order
        self.corpus_size = 0
        self.first_words_freq = None  # starting sentences words frequency
        self.ngram_freq = None  # ngram_freq[history][word] = Frequency(word|history)

    def build(self, input_corpus):
        assert self.ngram_freq is None, "Trying to build more than one model."
        self.ngram_freq = defaultdict(factory_defaultdict_int)
        with open(input_corpus, "r") as f:
            text = f.read().strip()
        sentences = text.split("\n")

        self.first_words_freq = defaultdict(int)
        self.ngram_freq = defaultdict(factory_defaultdict_int)

        # Get frequency.
        for num, sentence in enumerate(sentences):
            progress(num, len(sentences))
            tokens = [token for token in tokenize_sentence(sentence)]
            if len(tokens) == 0:
                continue
            self.first_words_freq[tokens[0]] += 1
            self.first_words_freq[""] += 1
            for order in range(1, self.order + 1):
                for from_, to in zip(range(len(tokens) - order + 1), range(order, len(tokens) + 1)):
                    prefix = tuple(tokens[from_:from_ + order - 1])
                    suffix = tuple(tokens[from_ + order - 1:to])
                    self.ngram_freq[prefix][suffix] += 1
                    self.ngram_freq[prefix][""] += 1

        print()  # for progressbar
        return

    def save(self, output):
        assert self.ngram_freq, "Trying to save not built model."
        with open(output, "wb") as f:
            pickle.dump(self.order, f)
            pickle.dump(self.first_words_freq, f)
            pickle.dump(self.ngram_freq, f)


# ---------------------------- Text generator ------------------------------- #
class TextGenerator():
    def __init__(self, input):
        with open(input, "rb") as f:
            self.order = pickle.load(f)
            self.first_words_freq = pickle.load(f)
            self.model = pickle.load(f)

    def choose_random_next_word(self, history):
        result = ""
        cumulative_freq = 0

        if len(history) == 0:
            threshold = random.randrange(0, self.first_words_freq[""])
            for word, freq in self.first_words_freq.items():
                if len(word) == 0:
                    continue
                cumulative_freq += freq
                if threshold <= cumulative_freq:
                    return word
        else:
            threshold = random.randrange(0, self.model[history][""])
            for suffix, freq in self.model[history].items():
                if len(suffix) == 0:
                    continue
                cumulative_freq += freq
                if threshold <= cumulative_freq:
                    return suffix[0]
        return result

    def generate_text(self, size):
        tokens = []
        current_ngram_size = 0
        text_size = 0
        last_sentence_ended = False
        while text_size < size or not last_sentence_ended:
            history = tuple(tokens[len(tokens) - current_ngram_size:len(tokens) + 1])
            next_word = self.choose_random_next_word(history)
            if len(next_word) != 0:
                tokens.append(next_word)
            if current_ngram_size + 1 < self.order:
                current_ngram_size += 1
            if next_word == "":
                current_ngram_size = current_ngram_size - 1 if current_ngram_size > 0 else 0
            if next_word in PUNCTUATION_END_SENTENCE:
                current_ngram_size = 0
                last_sentence_ended = text_size >= size
            text_size += 1
        return self.concatenate_tokens(tokens)

    def get_random_paragraph_size(self):
        return random.randrange(3, 10)  # heuristic

    def concatenate_tokens(self, tokens):
        text = ""
        sentence_num = 0
        token_in_paragraph_num = 0
        paragraph_size = self.get_random_paragraph_size()
        for token in tokens:
            if token_in_paragraph_num != 0 and token not in PUNCTUATION:
                text += " "
            if token in PUNCTUATION_END_SENTENCE:
                sentence_num += 1
            text += token
            token_in_paragraph_num += 1
            if sentence_num == paragraph_size:
                sentence_num = 0
                token_in_paragraph_num = 0
                paragraph_size = self.get_random_paragraph_size()
                text += "\n"
        return text


# --------------------------- Main routine ---------------------------------- #
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--mode", help="Mode to run: build or generate")
    parser.add_argument("--order", type=int,
                        help="Language model order.", default=DEFAULT_LM_ORDER)
    parser.add_argument("-i", "--input",
                        help="Path to input corpus for mode 'build' "
                             "or binarized model for mode 'generate'.")
    parser.add_argument("-o", "--output",
                        help="Path where binarized language model will be stored.")
    parser.add_argument("-s", "--size", type=int,
                        help="Generated corpus size.",
                        default=DEFAULT_GENERATED_CORPUS_SIZE)
    args = parser.parse_args()

    if args.mode == "build":
        builder = LMBuilder(args.order)
        builder.build(args.input)
        builder.save(args.output)
    elif args.mode == "generate":
        generator = TextGenerator(args.input)
        print(generator.generate_text(args.size))
    else:
        print("Unknown mode to run: " + args.mode)
        parser.print_help()


if __name__ == "__main__":
    main()

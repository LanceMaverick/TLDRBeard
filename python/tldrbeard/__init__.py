import re
import logging

from skybeard.beards import BeardChatHandler, BeardDBTable
from skybeard.decorators import onerror
from skybeard.utils import get_args
from skybeard.predicates import Filters

from sumy.parsers.html import HtmlParser
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer as Summarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words

from .config import LANGUAGE, SENTENCE_COUNT

logger = logging.getLogger(__name__)

class Tldrbeard(BeardChatHandler):

    __userhelp__ = """
    Creates a text summary of the last webpage posted in the chat with the /tldr command.
    Or of the webpage posted as an argument, e.g /tldr www.example.com"""

    __commands__ = [
        # command, callback coro, help text
        ("tldr", 'tldr', 'create tldr summary of webpage (last posted or as argument)'),
        (Filters.text_no_cmd, 'retain_last_url', 'log the last url sent in the chat'),
    ]

    # Link with a table in the skybeard db
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.webpage_table = BeardDBTable(self, 'tldrpage')

    async def tldr(self, msg):
        args = get_args(msg)
        url = None
        # Check if url is supplied as an argument
        if args:
            url =  self.extract_url_or_none(args[0])
        # otherwise look for the last one posted in the chat
        else:
            with self.webpage_table as table:
                for entry in table.all():
                    logging.info(entry)
                logging.info('Looking in webpage table for url to summarise')
                url = table.find_one(chat_id = msg['chat']['id'])['url']
                logging.info('Found url to summarise: ' + url)

        if not url:
            await self.sender.sendMessage('I cannot see any page to summarise')
            return

        summary = self.summarize(url, language = LANGUAGE, n_sents = SENTENCE_COUNT )
        if not summary:
            await self.sender.sendMessage(
                    'I cannot find any text to summarise in the url {}'.format(url),
                     disable_web_page_preview = True)

        # separate most important line from rest of text
        formatted_summary = '\n'.join(['\n\n'.join(summary[:2])]+summary[3:])
        await self.sender.sendMessage(formatted_summary, disable_web_page_preview = True)

    # Use Filter.text to check new messages for an URL. If found, it is extracted
    # and stored in the tldrpage table - only one entry per chat_id (last sent url only)
    async def retain_last_url(self, msg):
        text = msg['text']
        url = self.extract_url_or_none(text)
        if url:
            logging.info('Retaining url "{}" for summarisation'.format(url))
            chat_id=msg['chat']['id']
            with self.webpage_table as table:
                for entry in table.all():
                    logging.info(entry)

                logging.info('updating table...')
                entry = dict(chat_id=chat_id, url = url)
                dupe_check = table.find_one(chat_id=chat_id)
                if dupe_check:
                    table.update(entry, ['chat_id'])
                else:
                    table.insert(entry)

    # match properly formatted urls in text
    def extract_url_or_none(self, text):
        match = re.search("(?P<url>https?://[^\s]+)", text)
        if not match:
            return None
        logger.info('found tldr url match: {}'.format(match.groups()[0]))
        return match.groups()[0]

    def summarize(self, url, **kwargs):
        #set language and number of summary sentences
        language = kwargs.get('language', 'english')
        n_sents = kwargs.get('n_sents', 5)
        logger.info('Summarising url "{}" in {} in {} sentences'.format(
            url,
            language,
            n_sents))

        # build summarizer
        parser = HtmlParser.from_url(url, Tokenizer(language))
        stemmer = Stemmer(language)
        summarizer = Summarizer(stemmer)
        summarizer.stop_words = get_stop_words(language)

        #Return summary lines in order of importance
        #TODO: make generator
        sentences = []
        for sentence in summarizer(parser.document, n_sents):
            sentences.append(str(sentence))
        return sentences


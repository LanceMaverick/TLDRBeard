Creates a summary of web pages such as news articles.

The /tldr command will summarise the last webpage posted in the chat.
/tldr can also take an url as an argument, which it will attempt to summarise instead of the last article posted in the chat

The plugin will not save urls sent as an argument to /tldr as the last url posted in the chat. 

Language and nunber of summary sentences can be set in config.py

Requires sumy package for python, and after installing you may need to run:
python -c "import nltk; nltk.download('punkt')"

# brains

it thinks!

# setup

```brew install memcached```

```pip install -r requirements.txt```

# running

Server

```cd src && python app.py```

Celery task running

```cd src && celery -A workers worker -l INFO```

# tests

```cd src && python app.py tests```

# todo

 - [ ] test on heroku
 - [ ] setup one click deploy
 - [ ] add cli `get` command
 - [ ] save stdout/stderr from submissions... streamed and lost right now...

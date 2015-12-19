# brains

it thinks!

# setup

### local
```brew install memcached```

```pip install -r requirements.txt```

### heroku

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

then... on the app dashboard enable `web` for the site/queuing and `worker` to processes 
tasks.

You can then go to your heroku app -> settings -> "reveal config vars" and point your worker
to a different queue.

# running

django server

```cd src && python app.py```

celery task runner

```cd src && celery -A workers worker -l INFO```

# tests

```cd src && python app.py tests```

# todo

 - [x] test on heroku
 - [x] setup one click deploy
 - [ ] add cli `get` command
 - [ ] save stdout/stderr from submissions... streamed and lost right now...
 - [ ] time submissions
 - [ ] support multiple datasets
    - [ ] send cool stdout =============== <NAME> ===============

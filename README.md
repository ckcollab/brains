# brains

it thinks!

## using it

#### install the [cli](http://github.com/dev-coop/brains-cli)
```
# Install everything
$ pip install brains
$ mkdir experiment
$ cd experiment
```

#### make an example program
```
$ echo "print 'hello world'" >> run.py
```

#### configure brains
```
$ brains init
Give me your brains, I mean name: Eric Carmichael
Languages (python, ruby, etc.): python
How do you run your script? eg, `python run.py $INPUT` ($INPUT is replaced with dataset path)
: python run.py $INPUT

Automatically including the follow files in brain contents:
	run.py

done! brains.yaml created

$ cat brains.yaml
contents:
- run.py
languages: 'python'
name: 'Eric Carmichael'
run: 'python run.py $INPUT'
```

#### run the program
```
$ brains push
zipping...done
sending to server...done

Output:                                                                       

=============================== no dataset used ================================

hello world

```

#### run with datasets
your program can be ran multiple times at once vs many datasets
```
$ brains push --dataset test,test2
zipping...done
sending to server...done

Output:                                                                       

=================================== test =======================================

hello world

=================================== test2 ======================================

hello world

```

## setup server

#### local
```brew install memcached```

```pip install -r requirements.txt```

#### heroku

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

then... on the app dashboard enable `web` for the site/queuing and `worker` to processes 
tasks.

You can then go to your heroku app -> settings -> "reveal config vars" and point your worker
to a different queue.

#### running

django server

```cd src && python app.py```

celery task runner

```cd src && celery -A workers worker -l INFO```

#### tests

```cd src && python app.py tests```

#### todo

 - [x] test on heroku
 - [x] setup one click deploy
 - [ ] add cli `get` command
 - [ ] save stdout/stderr from submissions... streamed and lost right now...
 - [x] time submissions
 - [x] support multiple datasets
    - [x] send cool stdout =============== <NAME> ===============

Virtalenv – the worst thing ever happened to python.
====================================================

    Typo-typa, click-clack, `venv ve` etc
    `pip install` and `pip remove`
    You don't know completely friend
    What is a state of your virtualenv


Virtualenv is a pile of grabage. We can stop here, but you damn don't understand
what I'm talking about every damn time when I'm talking about it. Shit.
Anyway, we need to have a talk, fellow python programmer.


Falsehoods about python packages and virtualenv
-----------------------------------------------

1. If I write package to requirements.txt it will be in virtualenv
2. if I run `pip install -r requirements.txt` all packages with
right versions will be in virtualenv
3. I can manage all packages versions myself
4. Ok, at least if I will pin versions for packages like Django
I'm safe
3. If I use Pipenv then I'm safe and my virtualenv will regard
what pipenv use to keep packages
4. I will not forget to keep my virtualenv up to date
5. Some people can forget, but not me
6. Virtualenv can not be broken
7. Package maintainers can not broke my virtualenv
8. Package maintainers are sane people and do not do any meaningless shit
on package installation that can breake my virtualenv or
will require recreate virtualenv to install this damn piece of shit
because it broke itself


Why?
----

Virtualenv is dynamic. I mean like python, ruby, javascript. It is
dynamic and you don't know what state it is. Do you know about
shiny `pip freeze`? Do you belive that it is always correct and can actually
figure out what packages installed in your virtualenv? Yep? Sure?
One more falsehood.

The only way to have some confidence about virtualenv is recreate it from scratch,
install all packages in same order. Did you pinned versions, by the way?

But when to recreate it? Did you check that requirements.txt is changed on
`git checkout` or `git pull`? Oh, sorry, virtualenv are not to save your ass from
hours of debugging, pure little coder, common, world are not owe you anything, grow up.

But why it is this way? Because pile of grabage is dynamic and is not depend on your
warm, soft requirements.txt or what do you use for yourself. Even something
funny .toml are not any interest for virtualenv, because it is a pile of garbage and
piles of garbage are not have real interest for anything.


How virtualenv mess with python packaging
-----------------------------------------

Virtualenv is bad for python packaging. Because if it is a pile of
garbage, then it does not matter to keep yourself sane and don't try
to be stateless, to not interfere with explicitness of importing
machinery.

Package creators do insane things that are meaningless. Just open this link
and find about \*.pth files.
https://github.com/search?utf8=%E2%9C%93&q=extension%3Apth+import&type=Code
And you have noticed that setup.py is actual python script, yes?


Pipenv
------

It is not a Bundler. Man, if you use pile of garbage that virtualenv is,
you did not get what bundler is about. It is not about "I'v write packages
version", "I'v added shiny sha256's, but hell I know if they are actually
was correct when I pinned them".
It is about "I'v enforced damn packages versions, so you have not
a chance to use wrong version, 'hole in the head' bastard!".

What I dislike about pipenv, it is try to mask that virtualenv is shitty
pile of garbage with nice decorations around it.

Not on my watch, not on my watch.


How it must to be actually?
---------------------------

We can make it in different way, I will show you. Look carefully.

We want to have requests==2.18.4 for our code service. We write it to some
file, `requirements.txt` or `setup.py` or funny `.toml` thing.
Then we install this package somewhere in isolation. I mean not to pile of
garbage, listen here! In isolation, you know, not with other packages.

When we start our programm, we tell python where to find this `requests` thing when
it will issue `import` statement.

So what we have in this case? If funny requirements file changes, then we will
tell python interpreter that we have not installed version that we need, so
no luck, we are doomed. We install it then and start program again. Now it is ok,
we have right version of package. Really, without right package version you can not
start your damn dear switty program. You have to have right version beforehand
and this is good. This is how it supposed to be.

Be a good man, don't use pile of garbage anymore.
Use pundle instead. Guys, really. Stop this shit now.

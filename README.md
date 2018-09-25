# README
This project is a web crawler written in Python with the library asyncio. 

Starting from a url, it crawls all links belonging to that domain until a certain links depth is reached. It creates a graph where the nodes are links either crawled or referenced by a crawled page (in this case they can belong to an external domain). All the links (crawled and not) are filtered using a regex (it can be used to remove FTP links or external domains). The graph is in the format GEXF, which is commonly used by tools like [Gephi](https://gephi.org/). The level of parallelism and the maximum depth can be controlled by parameters. 

It use some features that only got introduced in Python 3.7:

- [Dataclasses](https://realpython.com/python-data-classes/)
- [Type Annotations](https://realpython.com/python37-new-features/#typing-enhancements)

## How to install
This project use `pipenv` to install and manage dependencies. Here it is the list of commands to create a local environment and install all the requirements.

~~~bash
mkdir .venv
pipenv --python 3.7.0
pipenv install
~~~

This will use all the dependencies already defined in Pipfile and Pipfile.lock

Once you have created the environment and installed the dependencies, if you want to run the program

~~~bash
pipenv shell
python crawler.py --start-url "https://monzo.com" --url-regex "(http://.*|https://.*)" --output monzo.gexf --parallelism 10 --max-depth 1
~~~
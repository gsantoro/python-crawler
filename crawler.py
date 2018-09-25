import asyncio
from aiohttp import ClientSession, ClientTimeout
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import argparse
import logging
import networkx as nx
from dataclasses import dataclass
import re

@dataclass(repr=True, eq=True, order=True, frozen=True)
class Link:
    depth: int = 0
    url: str = ""

    def __str__(self):
        return f"{self.url}"

logging.basicConfig(level=logging.INFO)

visited_urls = set()
urls_to_visit = set()

def has_valid_domain(url, allowed_domains):
    return get_domain(url) in allowed_domains

def get_domain(url):
    return urlparse(url).netloc

def is_relative_url(url):
    return get_domain(url) == ""

def is_url_to_visit(url):
    return url in urls_to_visit

def is_url_visited(url):
    return url in visited_urls

async def fetch_links(url, session):
    timeout = ClientTimeout(total=2)
    async with session.get(url, timeout=timeout) as response:
        html_page = await response.text()
        logging.info(f"Fetched {url}")

        next_links = []
        html_soup = BeautifulSoup(html_page, "html.parser")
        for link in html_soup.find_all("a"):
            next_link = link.get("href")

            if is_relative_url(next_link):
                next_link = urljoin(url, next_link)

            next_links.append(next_link)

        return next_links

def add_node(graph, link:Link):
    graph.add_node(link.url, depth=link.depth)

    logging.debug(f"Added to the graph: Node {link.url}")

def add_edge(graph, link:Link, next_link:Link):
    graph.add_edge(link.url, next_link.url)

    logging.debug(f"Added to the graph: Edge {link.url} -> {next_link.url}")


async def produce(queue, link:Link):
    urls_to_visit.add(link.url)
    await queue.put(link)

    logging.info("Added to the queue: {}".format(link.url))


async def consume(consumer_id, queue, allowed_domains, max_depth, url_regex, graph):
    async with ClientSession() as session:
        while True:
            link:Link = await queue.get()

            logging.info(f"Consumer {consumer_id}: start crawling {link.url}")

            add_node(graph, link)

            if link.depth < max_depth:
                next_links = await fetch_links(link.url, session)

                for next_link in next_links:
                    if not re.match(url_regex, next_link):
                        continue

                    next_link_obj = Link(link.depth + 1, next_link)

                    add_node(graph, next_link_obj)
                    add_edge(graph, link, next_link_obj)

                    if has_valid_domain(next_link, allowed_domains) \
                            and not is_url_visited(next_link) \
                            and not is_url_to_visit(next_link):
                        await produce(queue, next_link_obj)

            urls_to_visit.remove(link.url)
            visited_urls.add(link.url)
            queue.task_done()

            logging.info(f"Consumer {consumer_id}: end crawling {link.url}")


async def crawl(start_url, allowed_domains, parallelism, max_depth, url_regex, graph):
    queue = asyncio.Queue()

    consumers = [asyncio.create_task(consume(i, queue, allowed_domains, max_depth, url_regex, graph)) for i in range(parallelism)]

    await produce(queue, Link(depth=0, url=start_url))

    await queue.join()

    for consumer in consumers:
        consumer.cancel()


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-url", type=str, default="https://www.google.com",
                        help="start url to crawl")
    parser.add_argument("--url-regex", type=str, default="(http://.*|https://.*)",
                        help="regex to apply to all urls (both external and from the same domain)")
    parser.add_argument("--output", type=str, default="graph.gexf",
                        help="filename for the gexf file where to save the graph of the website")
    parser.add_argument("--parallelism", type=int, default=10,
                        help="number of consumers in parallel")
    parser.add_argument("--max-depth", type=int, default=2,
                        help="maximum depth for crawling")
    args = parser.parse_args()

    logging.info(f"Parameters: {args}")

    return args


def save_graph(graph, path):
    nx.write_gexf(graph, path)

    logging.info(f"Site map saved as a directed graph to: {path}")


def crawl_main(args, graph):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.ensure_future(crawl(args.start_url,
                                                        [get_domain(args.start_url)],
                                                        args.parallelism,
                                                        args.max_depth,
                                                        args.url_regex,
                                                        graph)))
    loop.close()


if __name__ == "__main__":
    arguments = get_args()

    directed_graph = nx.DiGraph()

    crawl_main(arguments, directed_graph)

    save_graph(directed_graph, arguments.output)

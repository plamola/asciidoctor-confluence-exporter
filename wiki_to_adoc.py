#!/usr/bin/env python3

# This script uses the Confluence API to convert pages in a Confluence wiki into
# files in the AsciiDoc format. The username and password required to connect to
# the API must be passed as environment variables: `CONFLUENCE_USERNAME` and
# `CONFLUENCE_PASSWORD`.

import requests
import argparse
import os
import logging
import sys
import pandoc
from pandoc.types import *


class Config:
    def __init__(self, confluence_user_name, confluence_password, base_url, output_folder, recursive, title_as_name):
        self.confluence_user_name = confluence_user_name
        self.confluence_password = confluence_password
        self.base_url = base_url
        self.output_folder = output_folder
        self.recursive = recursive
        self.title_as_name = title_as_name


# Used to build the URL to connect to, stripping extra slashes if needed
def slash_join(*args):
    return "/".join(arg.strip("/") for arg in args)

def create_folder(folder):
    # Verify that the specified output argument is a folder
    if os.path.exists(folder) and not os.path.isdir(folder):
        logging.error("Invalid output folder name '{}'. Exiting.".format(folder))
        exit(1)

    # If the folder does not exist, create it
    if not os.path.exists(folder):
        logging.info("Creating output folder '{}'".format(folder))
        os.makedirs(folder)


def process_page(service_config, page_id):
    create_folder(service_config.output_folder)
    try:
        url = "{}/{}?expand=body.storage".format(wiki_base_url, page_id)
        resp = requests.get(url=url, auth=(service_config.confluence_user_name, service_config.confluence_password))
        if resp.status_code != 200:
            logging.error("Status code {} for '{}'. Skipping page.".format(resp.status_code, url))
        else:
            logging.info("Status code {} for '{}'.".format(resp.status_code, url))
            data = resp.json()
            title = data["title"]
            html = data["body"]["storage"]["value"]
            # Convert from html to asciidoctor
            doc = pandoc.read(source=html.encode(), format="html")
            adoc = pandoc.write(doc=doc, format="asciidoctor")
            # Save to file
            filename = "{}/{}.adoc".format(service_config.output_folder,
                                           os.path.normpath(title) if service_config.title_as_name is True else page_id)
            logging.info("Creating file {}".format(filename))
            output_file = open(filename, "w")
            output_file.write("= {}\n\n".format(title))
            output_file.write(adoc)
            output_file.close()
            logging.info("Saved AsciiDoc file '{}'".format(filename))
            if service_config.recursive:
                # Find any children
                logging.info("Looking for child pages")
                children_url = "{}/{}/child/page".format(wiki_base_url, page_id)
                child_resp = requests.get(url=children_url, auth=(service_config.confluence_user_name, service_config.confluence_password))
                if child_resp.status_code != 200:
                    logging.error("Status code {} for '{}'. Continuing.".format(child_resp.status_code, children_url))
                else:
                    logging.info("Status code {} for '{}'.".format(child_resp.status_code, children_url))
                    child_data = child_resp.json()
                    child_page_ids = child_data["results"]
                    for child_page in child_page_ids:
                        if child_page["type"] == "page":
                            child_page_id = child_page["id"]
                            logging.info("child: {} - {}".format(child_page_id, child_page["title"]))
                            folder = "{}/{}".format(service_config.output_folder,
                                                    os.path.normpath(title) if service_config.title_as_name is True else page_id)
                            child_config = Config(service_config.confluence_user_name,
                                                  service_config.confluence_password,
                                                  service_config.base_url, folder,
                                                  service_config.recursive,
                                                  service_config.title_as_name)
                            process_page(child_config, child_page_id)
    except:
        e = sys.exc_info()[0]
        logging.error("Error: '{}'. Exiting.".format(e))
        exit(1)

# Parsing command arguments
parser = argparse.ArgumentParser(
    description="Reads a series of pages from a Confluence `--wiki` server as numeric IDs, and writes each one to an AsciiDoc file into the specified `--output` folder.")
parser.add_argument("-o", "--output", help="folder where to export files", required=True)
parser.add_argument("-w", "--wiki", help="base URL of the Confluence wiki", required=True)
parser.add_argument("-r", "--recursive", help="export all child pages", required=False, action="store_true")
parser.add_argument("-t", "--titles", help="use the title of the document in the file name, instead of the page id", required=False, action="store_true")
parser.add_argument("-v", "--verbose", help="show all logging messages during execution", action="store_true")
parser.add_argument("--version", action="version", version="%(prog)s 1.0")
parser.add_argument("pages", help="Confluence page IDs to export", metavar="N", nargs="+", type=int)
args = parser.parse_args()

# Setting logger parameters
level = logging.WARNING
if args.verbose:
    level = logging.INFO
logging.basicConfig(format='%(levelname)s: %(message)s', level=level)

logging.info("Starting program with parameters:")
logging.info("Wiki: '{}'".format(args.wiki))
logging.info("Recursive: '{}'".format(args.recursive))
logging.info("Use titles: '{}'".format(args.titles))
logging.info("Output directory: '{}'".format(args.output))
logging.info("Page IDs: '{}'".format(args.pages))

# Read username and password from the environment
CONFLUENCE_USERNAME = os.environ.get("CONFLUENCE_USERNAME")
CONFLUENCE_PASSWORD = os.environ.get("CONFLUENCE_PASSWORD")

if not CONFLUENCE_USERNAME or not CONFLUENCE_PASSWORD:
    logging.error("Environment variables CONFLUENCE_USERNAME and/or CONFLUENCE_PASSWORD are unset. Exiting.")
    exit(1)

logging.info("Environment variables set.")

wiki_base_url = slash_join(args.wiki, "rest", "api", "content")
logging.info("Base URL is '{}'.".format(wiki_base_url))

# Fetch each page and save as AsciiDoc
for page in args.pages:
    config = Config(CONFLUENCE_USERNAME,
                    CONFLUENCE_PASSWORD,
                    wiki_base_url,
                    args.output,
                    args.recursive,
                    args.titles)
    process_page(config, page)


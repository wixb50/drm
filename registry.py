#!/usr/bin/env python

import requests
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import json
import re
import argparse

## this is a registry manipulator, can do following:
##   - list all images (including layers)
##   - delete images
##       - all except last N images
##       - all images and/or tags
##
## run
##   registry.py -h
##   to get more help
##
## important: after removing the tags, run the garbage collector
## on your registry host:
## docker-compose -f [path_to_your_docker_compose_file] run \
##     registry bin/registry garbage-collect \
##     /etc/docker/registry/config.yml
##
## or if you are not using docker-compose:
## docker run registry:2 bin/registry garbage-collect \
##     /etc/docker/registry/config.yml
##
## for more detail on garbage collection read here:
## https://docs.docker.com/registry/garbage-collection/


# number of image versions to keep
CONST_KEEP_LAST_VERSIONS = 10

# this class is created for testing
class Requests:
    def request(self, method, url, **kwargs):
        return requests.request(method, url, **kwargs)

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''

    def __atoi(text):
        return int(text) if text.isdigit() else text

    return [ __atoi(c) for c in re.split('(\d+)', text) ]


# class to manipulate registry
class Registry:

    # this is required for proper digest processing
    HEADERS = {"Accept":
               "application/vnd.docker.distribution.manifest.v2+json"}

    def __init__(self):
        self.username = None
        self.password = None
        self.hostname = None
        self.no_validate_ssl = False
        self.http = None
        self.last_error = None

    def parse_login(self, login):
        if login != None:

            if not ':' in login:
                self.last_error = "Please provide -l in the form USER:PASSWORD"
                return (None, None)

            self.last_error = None
            (username, password) = login.split(':', 1)
            username = username.strip('"').strip("'")
            password = password.strip('"').strip("'")
            return (username, password)

        return (None, None)


    @staticmethod
    def create(host, login, force_non_ssl, no_validate_ssl):
        r = Registry()

        (r.username, r.password) = r.parse_login(login)
        if r.last_error != None:
            print(r.last_error)
            exit(1)

        r.hostname = '{0}://{1}'.format('http' if force_non_ssl else 'https', host)
        r.no_validate_ssl = no_validate_ssl
        r.http = Requests()
        return r


    def send(self, path, method="GET"):
        result = self.http.request(
            method, "{0}{1}".format(self.hostname, path),
            headers = self.HEADERS,
            auth=(None if self.username == ""
                  else (self.username, self.password)),
            verify = not self.no_validate_ssl)

        if str(result.status_code)[0] == '2':
            self.last_error = None
            return result

        self.last_error=result.status_code
        return None

    def list_images(self):
        result = self.send('/v2/_catalog')
        if result == None:
            return []

        return json.loads(result.text)['repositories']

    def list_tags(self, image_name):
        result = self.send("/v2/{0}/tags/list".format(image_name))
        if result == None:
            return []

        try:
            tags_list = json.loads(result.text)['tags']
        except ValueError:
            self.last_error = "list_tags: invalid json response"
            return []

        if tags_list != None:
            tags_list.sort(key=natural_keys)

        return tags_list

    def get_tag_digest(self, image_name, tag):
        image_headers = self.send("/v2/{0}/manifests/{1}".format(
            image_name, tag), method="HEAD")

        if image_headers == None:
            print("  tag digest not found: {0}".format(self.last_error))
            return None

        tag_digest = image_headers.headers['Docker-Content-Digest']

        return tag_digest

    def delete_tag(self, image_name, tag, dry_run):
        if dry_run:
            print('would delete tag {0}'.format(tag))
            return False

        tag_digest = self.get_tag_digest(image_name, tag)

        if tag_digest == None:
            return False

        delete_result = self.send("/v2/{0}/manifests/{1}".format(
            image_name, tag_digest), method="DELETE")

        if delete_result == None:
            print("failed, error: {0}".format(self.last_error))
            return False

        print("done")
        return True

    # this function is not used and thus not tested
    # def delete_tag_layer(self, image_name, layer_digest, dry_run):
    #     if dry_run:
    #         print('would delete layer {0}'.format(layer_digest))
    #         return False
    #
    #     print('deleting layer {0}'.format(layer_digest),)
    #
    #     delete_result = self.send('/v2/{0}/blobs/{1}'.format(
    #         image_name, layer_digest), method='DELETE')
    #
    #     if delete_result == None:
    #         print("failed, error: {0}".format(self.last_error))
    #         return False
    #
    #     print("done")
    #     return True


    def list_tag_layers(self, image_name, tag):
        layers_result = self.send("/v2/{0}/manifests/{1}".format(
            image_name, tag))

        if layers_result == None:
            print("error {0}".format(self.last_error))
            return []

        json_result = json.loads(layers_result.text)
        if json_result['schemaVersion'] == 1:
            layers = json_result['fsLayers']
        else:
            layers = json_result['layers']

        return layers

def parse_args(args = None):
    parser = argparse.ArgumentParser(
        description="List or delete images from Docker registry",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=("""
IMPORTANT: after removing the tags, run the garbage collector
           on your registry host:

   docker-compose -f [path_to_your_docker_compose_file] run \\
       registry bin/registry garbage-collect \\
       /etc/docker/registry/config.yml

or if you are not using docker-compose:

   docker run registry:2 bin/registry garbage-collect \\
       /etc/docker/registry/config.yml

for more detail on garbage collection read here:
   https://docs.docker.com/registry/garbage-collection/
                """))
    parser.add_argument(
        '-l','--login',
        help="Login and password to access to docker registry",
        required=False,
        metavar="USER:PASSWORD")

    parser.add_argument(
        '-r','--host',
        help="Hostname for registry server, e.g. example.com:5000",
        required=True,
        metavar="URL")

    parser.add_argument(
        '-f','--force-non-ssl',
        help="force allow use of non-ssl",
        action='store_const',
        default=False,
        const=True)

    parser.add_argument(
        '-rm','--delete',
        help='delete a specific reference of a repository',
        nargs='+',
        metavar="IMAGE:TAG")   

    parser.add_argument(
        '--dry-run',
        help=('If used in combination with --delete,'
              'then images will not be deleted'),
        action='store_const',
        default=False,
        const=True)

    parser.add_argument(
        '-ls','--image',
        help='Specify images and tags to list',
        nargs='*',
        metavar="[IMAGE:[TAG]]")

    parser.add_argument(
        '--no-validate-ssl',
        help="Disable ssl validation",        
        action='store_const',
        default=False,
        const=True)

    parser.add_argument(
        '--layers',
        help=('Show layers digests for all images and all tags'),
        action='store_const',
        default=False,
        const=True)

    option = parser.parse_args(args)

    actions = ['-ls/--image', '-rm/--delete']
    if not any(getattr(option, x.split('--')[1], None) != None for x in actions):
        parser.error('please input at least one action:{0}.'.format(actions))
    
    return option


def delete_tags(
    registry, image_name, dry_run, tags_to_delete):

    for tag in tags_to_delete:

        print("  deleting tag {0}".format(tag))

##        deleting layers is disabled because 
##        it also deletes shared layers
##        
##        for layer in registry.list_tag_layers(image_name, tag):
##            layer_digest = layer['digest']
##            registry.delete_tag_layer(image_name, layer_digest, dry_run)

        registry.delete_tag(image_name, tag, dry_run)

def get_tags_like(tag_like, tags_list):
    result = set()
    print("tag like: {0}".format(tag_like))
    for tag in tags_list:
        if re.search(tag_like, tag):
            print("Adding {0} to tags list".format(tag))
            result.add(tag)
    return result

def get_tags(all_tags_list, image_name, tags_like):
    # check if there are args for special tags
    result = set()
    if tags_like:
        result = get_tags_like(tags_like, all_tags_list)
    else:
        result.update(all_tags_list)

    # get tags from image name if any
    if ":" in image_name:
        (image_name, tag_name) = image_name.split(":")
        result = set([tag_name])

    return result

def main_loop(args):

    if args.no_validate_ssl:        
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    registry = Registry.create(args.host, args.login, args.force_non_ssl, args.no_validate_ssl)

    if args.image != None:
        image_list = args.image or registry.list_images()
    elif args.delete != None:
        image_list = args.delete
    else:
        image_list = []

    # loop through registry's images
    # or through the ones given in command line
    for image_name in image_list:
        print("---------------------------------")
        tags_like = None
        if ":" in image_name:
            (image_name, tags_like) = image_name.split(":")
        print("Image: {0}".format(image_name))

        all_tags_list = registry.list_tags(image_name)

        if not all_tags_list:
            print("  no tags!")
            continue

        tags_list = get_tags(all_tags_list, image_name, tags_like)

        # print(tags and optionally layers        
        for tag in tags_list:
            print("  tag: {0}".format(tag))
            if args.layers:
                for layer in registry.list_tag_layers(image_name, tag):
                    if 'size' in layer:
                        print("    layer: {0}, size: {1}".format(
                            layer['digest'], layer['size']))
                    else:
                        print("    layer: {0}".format(
                            layer['blobSum']))


        # delete tags if told so
        if args.delete:
            tags_list_to_delete = sorted(tags_list, key=natural_keys)

            delete_tags(
                registry, image_name, args.dry_run,
                tags_list_to_delete)

if __name__ == "__main__":
    args = parse_args()
    try:
        main_loop(args)
    except KeyboardInterrupt:
        print("Ctrl-C pressed, quitting")
        exit(1)

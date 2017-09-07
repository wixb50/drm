# drm
drm(docker registry management cli) is a script for easy manipulation of docker-registry from command line.


## Installation

Download registry.py and set it as executable
```
  sudo -i
  curl https://raw.githubusercontent.com/wixb50/drm/master/registry.py -s -o /usr/local/bin/drm && chmod 755 /usr/local/bin/drm
```

It uses requests python module, so you may need to install it as well:
```
  pip install requests
```

## Listing images

The below command will list all images and all tags in your registry:
```
  drm -l user:pass -r example.com:5000 -ls
```

List all images, tags and layers:
```
  drm -l user:pass -r example.com:5000 -ls --layers
```

List particular image(s) or image:tag (all tags of ubuntu and alpine in this example)
```
  drm -l user:pass -r example.com:5000 -ls ubuntu[:tag_like]
```
  
Same as above but with layers
```
  drm -l user:pass -r example.com:5000 -ls ubuntu[:tag_like] --layers
```
  
## Username and password
  
  It is optional, you can omit it in case if you use insecure registry without authentication (up to you, 
  but its really insecure; make sure you protect your entire registry from anyone)
  
  username and password pair can be provided in the following forms
```  
  -l username:password
  -l 'username':'password'
  -l "username":"password"
```
  Username cannot contain colon (':') (I don't think it will contain ever, but anyway I warned you).
  Password, in its turn, can contain as many colons as you wish.
    
      
## Deleting images 

Delete the tag from the image.
```
  drm -l user:pass -r example.com:5000 -rm image[:tag_like]
```

## force non ssl
If you are using docker registry with http only, you can force non ssl.
```
  drm -l user:pass -r example.com:5000 -f
```

## Disable ssl verification

If you are using docker registry with a self signed ssl certificate, you can disable ssl verification:
```
  drm -l user:pass -r example.com:5000 --no-validate-ssl 
```

## Help
Any help, just run.
```
  drm --help
```

  
## Important notes: 

### garbage-collection in docker-registry 
docker registry API does not actually delete tags or images, it marks them for later 
garbage collection. So, make sure you run something like below 
(or put them in your crontab):
```
  cd [path-where-your-docker-compose.yml]
  docker-compose stop registry
  docker-compose run \
       registry bin/registry garbage-collect \
       /etc/docker/registry/config.yml
  docker-compose up -d registry
```
or (if you are not using docker-compose):
```
  docker stop registry:2
  docker run registry:2 bin/registry garbage-collect \
       /etc/docker/registry/config.yml
  docker start registry:2
```

for more detail on garbage collection read here:
   https://docs.docker.com/registry/garbage-collection/

### enable image deletion in docker-registry
Make sure to enable it by either creating environment variable 
  `REGISTRY_STORAGE_DELETE_ENABLED: "true"`
or adding relevant configuration option to the docker-registry's config.yml.
For more on docker-registry configuration, read here:
  https://docs.docker.com/registry/configuration/

You may get `Functionality not supported` error when this option is not enabled.

# Contact

Please feel free to contact me at wixb50@gmail.com if you wish to add more functionality 
or want to contribute.

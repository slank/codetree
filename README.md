codetree
========

Codetree is a tool for assembling directories of code from disparate sources. You might, for example, want to keep your application code separate from your deployment code and local configuration, then bring them all together as part of your build process. Codetree helps you do that.

As a replacement for [config-manager](https://launchpad.net/config-manager), codetree is a bit more modern and, I hope, more extensible. Similar to config-manager, it was built for use at Canonical to pull together bzr-based repositories, but inspired by the need to grab individual files or archives via HTTP(S).

But enough about me...

Usage
-----

Codetree assumes that you'd like to assemble your code in the current working directory. It expects a configuration file whose syntax is detailed below. As `codetree -h` will tell you:

    usage: codetree [-h] cfgfile [cfgfile ...]
    
    positional arguments:
      cfgfile     Codetree configuration file
    
    optional arguments:
      -h, --help  show this help message and exit

Configuration Files
-------------------

Config-manager configuration files should be compatible with codetree. Codetree has a few more features, and therefore some additional config syntax.

Configuration files consist of directives, one per line, consisting of a local destination and a source. Blank lines and lines whose first character is "#" are ignored.

Here's an example config:

    app                     lp:myapp
    app/plugins/woohoo      lp:myapp-woohoo;revno=44
    app/images/logo.gif     http://content.internal/myimage.gif
    app/downloads           @
    app/content             /home/contentbot/appcontent

Taking that line-by-line:

* the app directory contains a copy of the latest version of myapp, a bzr repo hosted on launchpad.net
* the app/plugins/woohoo directory contains revision number 44 of lp:myapp-woohoo
* app/image/logo.gif is a single image file
* app/downloads is an empty directory
* app/content is a copy of the local directory /home/contentbot/appcontent

### Source arguments

Sources may accept various arguments. As in the lp:myapp-woohoo example above, you see that they come at the end of the source, separated by a semicolon. Arguments take the form key=value. In this case, the argument "revno" tells the Bzr handler to checkout revision 44 of lp:myapp-woohoo.

### Source URLs

There are currently three handlers, each registered for a number of URL schemes:

* Bzr: bzr, bzr+ssh, lp, bzr+http, bzr+https
* HTTP/S: http, https
* Local: (empty scheme)

If you're familiar with Bzr, you'll note that bzr+http and bzr+https are not valid schemes for Bzr URLs. No two handlers may handle the same scheme. In order to defnintively identify the handler you want for a source, the scheme you use may be slightly non-standard.

Other handlers are planned, such as an archive handler (variant of the http/s handler) and a git handler.

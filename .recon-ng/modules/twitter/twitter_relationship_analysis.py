# module required for framework integration
from recon.core.module import BaseModule
# module specific imports
import os
class Module(BaseModule):

    # modules are defined and configured by the "meta" class variable
    # "meta" is a dictionary that contains information about the module, ranging from basic information, to input that affects how the module functions
    # below is an example "meta" declaration that contains all of the possible definitions

    meta = {
        'name': 'Hostname Resolver',
        'author': 'Tim Tomes (@lanmaster53)',
        'version': '1.0',
        'description': 'Resolves IP addresses to hosts and updates the database with the results.',
        'dependencies': [],
        'files': [],
        'required_keys': [],
        'comments': (
            'Note: Nameserver must be in IP form.',
            '\te.g. 1.2.3.4',
        ),
        'query': 'SELECT DISTINCT host FROM hosts WHERE host IS NOT NULL',
        'options': (
            ('nameserver', '8.8.8.8', 'yes', 'ip address of a valid nameserver'),
        ),
    }

    # "name", "author", "version", and "description" are required entries
    # "dependencies" is required if the module requires the installation of a third party library (list of PyPI install names)
    # "files" is required if the module includes a reference to a data file in the "/data" folder of the marketplace repository
    # "required_keys" is required if the module leverages an API or builtin functionality that requires a key
    # "query" is optional and determines the "default" source of input
    # the "SOURCE" option is only available if "query" is defined
    # "options" expects a tuple of tuples containing 4 elements:
    # 1. the name of the option
    # 2. the default value of the option (strings, integers and boolean values are allowed)
    # 3. a boolean value (True or False) for whether or not the option is mandatory
    # 4. a description of the option
    # "comments" are completely optional

    # optional method
    def module_pre(self):
        # override this method to execute code prior to calling the "module_run" method
        # returned values are passed to the "module_run" method and must be captured in a parameter
        return value

    # mandatory method
    # the second parameter is required to capture the result of the "SOURCE" option, which means that it is only required if "query" is defined within "meta"
    # the third parameter is required if a value is returned from the "module_pre" method
    def module_run(self, hosts, value):
        # do something leveraging the api methods discussed below
        # local option values can be accessed via self.options['name'] or self.options.get('name')
        # key values can be accessed via self.keys['name'] or self.keys.get('name')
        # use the "self.workspace" class property to access the workspace location
        # threading can be used anywhere with the module through the usage of the "self.thread" api call
        # the "self.thread" api call requires a "module_thread" method which acts as the worker for each item in a queue
        # "self.thread" takes at least one argument
        # the first argument must be an iterable that contains all of the items to fill the queue
        # all other arguments get blindly passed to the "module_thread" method where they can be accessed at the thread level
        self.thread(hosts, url, headers)

    # optional method
    # the first received parameter is required to capture an item from the queue
    # all other parameters passed in to "self.thread" must be accounted for
    def module_thread(self, host, url, headers):
        # never catch KeyboardInterrupt exceptions in the "module_thread" method as threads don't see them
        # do something leveraging the api methods discussed below
        pass

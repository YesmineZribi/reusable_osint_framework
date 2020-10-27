# module required for framework integration
from recon.core.module import BaseModule
# mixins for desired functionality
# module specific imports
import os

class Module(BaseModule):

    # modules are defined and configured by the "meta" class variable
    # "meta" is a dictionary that contains information about the module, ranging from basic information, to input that affects how the module functions
    # below is an example "meta" declaration that contains all of the possible definitions

    meta = {
        'name': 'Database purger',
        'author': 'Yesmine Zribi (@YesmineZribi)',
        'version': '1.0',
        'description': 'Purges db tables provided',
        'dependencies': [],
        'files': [],
        'required_keys': [],
        'comments': (
            'Purges the database tables enabled',
        ),
        'options': (
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
        pass

    # mandatory method
    # the second parameter is required to capture the result of the "SOURCE" option, which means that it is only required if "query" is defined within "meta"
    # the third parameter is required if a value is returned from the "module_pre" method
    def module_run(self):
        self.output("Purging database...")
        self.output("Deleting all records from account")
        self.query('DELETE FROM users')
        self.output("Deleting all records from followers")
        self.query('DELETE FROM followers')
        self.output("Deleting all records from friends")
        self.query('DELETE FROM posts')
        self.output("Deleting all records from favorites")
        self.query('DELETE FROM favorites')
        self.output("Deleting all records from timeline")
        self.query('DELETE FROM mentions')
